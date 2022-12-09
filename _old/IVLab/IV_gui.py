import sys
from time import sleep
import os
import json
import unicodedata
import re

from PyQt5.QtCore import Qt
from PyQt5.QtCore import QObject, QThread, pyqtSignal, QRectF
from PyQt5.QtGui import QIntValidator, QDoubleValidator
from PyQt5.QtWidgets import (
    QApplication,
    QLabel,
    QMainWindow,
    QPushButton,
    QComboBox,
    QLineEdit,
    QTextEdit,
    QCheckBox,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QGroupBox,
    QFrame,
    QSplitter,
    QStackedWidget,
    QWidget,
    QFrame,
    QFileDialog,
    QMessageBox,
    QDialogButtonBox,
    QDialog,
    QStatusBar,
)
from pyqtgraph import PlotWidget, plot
import pyqtgraph as pg
import numpy as np

class LogOffDialog(QDialog):
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.win = parent
        
        self.setWindowTitle("Confirm Log Off")

        QBtn = QDialogButtonBox.Ok | QDialogButtonBox.Cancel

        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.OKButtonPressed)
        self.buttonBox.rejected.connect(self.reject)

        self.layout = QVBoxLayout()
        message = QLabel("Logbook Entry:")
        self.textEdit = QTextEdit()
        self.textEdit.setMaximumHeight(100)
        
        self.layout.addWidget(message)
        self.layout.addWidget(self.textEdit)
        self.layout.addWidget(self.buttonBox)
        self.setLayout(self.layout)
        
    def OKButtonPressed(self):
        self.win.signal_log_out.emit(self.textEdit.toPlainText())
        self.accept()

class Window(QMainWindow):
    signal_initialize_hardware = pyqtSignal()
    signal_log_out = pyqtSignal(str)
    signal_log_in = pyqtSignal(str,str)
    signal_runIV = pyqtSignal(object)
    signal_runConstantV = pyqtSignal(object)
    signal_runConstantI = pyqtSignal(object)
    signal_runMaxPP = pyqtSignal(object)
    signal_runCalibration = pyqtSignal(object)
    signal_saveCalibration = pyqtSignal(object)
    signal_abortRun = pyqtSignal()
    signal_saveScanData = pyqtSignal(str, str)
    signal_toggleAutoSave = pyqtSignal(bool)
    progress = pyqtSignal(int)
    flag_abortRun = False

    def __init__(self, parent=None):
        super().__init__(parent)
        self.clicksCount = 0
        self.flag_abortRun = False
        self.setupUi()

    def setupUi(self):
        self.setWindowTitle("IVLab")
        self.resize(1200, 600)
        self.centralWidget = QWidget()
        self.setCentralWidget(self.centralWidget)
        
        #init button
        self.buttonInitialize = QPushButton("Initialize Hardware",self)
        self.buttonInitialize.clicked.connect(self.initializeHardware)
        self.buttonInitialize.setMaximumWidth(300)
        self.buttonInitialize.setEnabled(False)
        
        self.createLightLevelGroupBox()
        self.createMeasurementGroupBox()
        self.createCellSizeWidget()
        self.createComplianceGroupBox()
        self.ButtonResetToDefault = QPushButton("Reset All Settings To Default", self)
        self.ButtonResetToDefault.clicked.connect(self.setAllFieldsToDefault)
        self.ButtonResetToDefault.setEnabled(False)
        self.createPlotHeaderWidget()
        self.createGraphPanels()
        
        # Set the measurement frame layout
        self.measurementFrame = QWidget()
        
        measurementLayout = QVBoxLayout()
        measurementLayout.addWidget(self.buttonInitialize)
        measurementLayout.addStretch(1)
        measurementLayout.addWidget(self.lightLevelGroupBox)
        measurementLayout.addStretch(1)
        #measurementLayout.addWidget(self.labelMeasurementMenu)
        measurementLayout.addWidget(self.measurementGroupBox)
        #measurementLayout.addWidget(self.measurementStack)
        measurementLayout.addStretch(1)
        measurementLayout.addWidget(self.cellSizeWidget)
        measurementLayout.addStretch(1)
        measurementLayout.addWidget(self.ComplianceGroupBox)
        measurementLayout.addStretch(1)
        measurementLayout.addWidget(self.ButtonResetToDefault)
        
        #measurementLayout.addStretch(1)
        
        self.measurementFrame.setLayout(measurementLayout)  
        
        #plot frame and layout
        self.plotFrame = QWidget()
        plotFrameLayout = QVBoxLayout()
        plotFrameLayout.addWidget(self.plotHeader)
        plotFrameLayout.addWidget(self.StackGraphPanels)
        self.plotFrame.setLayout(plotFrameLayout)
        
        layout = QHBoxLayout()
        #plain layout works but does not scale as well as the splitter
        #layout.addWidget(self.measurementFrame)
        #layout.addWidget(self.plotFrame)
        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.addWidget(self.measurementFrame)
        self.splitter.addWidget(self.plotFrame)
        self.splitter.setStretchFactor(1,10)
        layout.addWidget(self.splitter)
        
        layout.setContentsMargins(10,10,10,10)
        
        self.centralWidget.setLayout(layout)
        
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("Please Log In")
        
        # make dictionary of all UI elements for later use
        self.UIFields = {'ManualLightLevel': self.fieldManualLightLevel,
                         'IVMinimumVoltage': self.fieldIVMinV,
                         'IVMaximumVoltage': self.fieldIVMaxV,
                         'IVVoltageStep': self.fieldIVVStep,
                         'IVSweepRate': self.fieldIVSweepRate,
                         'IVStabilizationTime': self.fieldIVStabilizationTime,
                         'ConstantVSetV': self.fieldConstantVSetV,
                         'ConstantVStabilizationTime': self.fieldConstantVStabilizationTime,
                         'ConstantVInterval': self.fieldConstantVInterval,
                         'ConstantVDuration': self.fieldConstantVDuration,
                         'ConstantISetI': self.fieldConstantISetI,
                         'ConstantIStabilizationTime': self.fieldConstantIStabilizationTime,
                         'ConstantIInterval': self.fieldConstantIInterval,
                         'ConstantIDuration': self.fieldConstantIDuration,
                         'MaxPPStartV': self.fieldMaxPPStartV,
                         'MaxPPStabilizationTime': self.fieldMaxPPStabilizationTime,
                         'MaxPPInterval': self.fieldMaxPPInterval,
                         'MaxPPDuration': self.fieldMaxPPDuration,
                         'CalibrationStabilizationTime': self.fieldCalibrationStabilizationTime,
                         'CalibrationInterval': self.fieldCalibrationInterval,
                         'CalibrationDuration': self.fieldCalibrationDuration,
                         'CalibrationReferenceCellCurrent': self.fieldCalibrationReferenceCellCurrent,
                         'VoltageLimit' : self.fieldVoltageLimit,
                         'CurrentLimit' : self.fieldCurrentLimit,
                         'CellActiveArea': self.fieldCellActiveArea}
        self.UIDropDowns = {'lightLevel': self.menuSelectLightLevel,
                            'measurementType': self.menuSelectMeasurement,
                            '2wire4wire': self.menu2wire4wire,
                            'sweepDirection': self.menuIVSweepDirection}
        #self.resize(1200, 600)
    
    def createLightLevelGroupBox(self): 
        #this group has two variants, in a stacked widget.
        self.panelLightLevelDropDown = QWidget()
        #self.panelLightLevelDropDown.setMaximumWidth(300)
        
        self.panelLightLevelManualField = QWidget()
        #self.panelLightLevelManualField.setMaximumWidth(300)
        
        #combobox to select the light level
        self.lightLevelGroupBox = QGroupBox("Light Level")
        lightLevelLayout = QVBoxLayout()
        #self.labelLightLevelMenu = QLabel("Select Light Level")
        self.menuSelectLightLevel = QComboBox()
        self.menuSelectLightLevel.setMaximumWidth(300)
        self.lightLevelStringList = ['100% Sun','Dark']
        self.lightLevelPercentList = [100,0]
        for light in self.lightLevelStringList:
            self.menuSelectLightLevel.addItem(light)
        #self.labelLightLevelMenu.setEnabled(False)
        #self.menuSelectLightLevel.setEnabled(False)
        
        lightLevelDropDownLayout = QHBoxLayout()
        lightLevelDropDownLayout.addWidget(self.menuSelectLightLevel)
        self.panelLightLevelDropDown.setLayout(lightLevelDropDownLayout)
        
        self.fieldManualLightLevel = QLineEdit("100.00")
        self.ManualLightLevelValidator = QDoubleValidator()
        self.fieldManualLightLevel.setValidator(self.ManualLightLevelValidator)
        self.labelManualLightLevel = QLabel("Manual Light Level: ")
        self.labelManualLightLevelUnits = QLabel("% sun")
        
        lightLevelManualFieldLayout = QHBoxLayout()
        lightLevelManualFieldLayout.addWidget(self.labelManualLightLevel)
        lightLevelManualFieldLayout.addWidget(self.fieldManualLightLevel)
        lightLevelManualFieldLayout.addWidget(self.labelManualLightLevelUnits)
        self.panelLightLevelManualField.setLayout(lightLevelManualFieldLayout)

        self.lightLevelStack = QStackedWidget()
        self.lightLevelStack.addWidget(self.panelLightLevelDropDown)
        self.lightLevelStack.addWidget(self.panelLightLevelManualField)
        self.lightLevelStack.setCurrentIndex(0)
        self.lightLevelModeManual = False
        
        self.labelMeasuredLightIntensity = QLabel("Measured Light Intensity: ---.--% sun")
        
        lightLevelLayout = QVBoxLayout()
        lightLevelLayout.addWidget(self.lightLevelStack)
        lightLevelLayout.addWidget(self.labelMeasuredLightIntensity)
        self.lightLevelGroupBox.setLayout(lightLevelLayout)
        self.lightLevelGroupBox.setMaximumWidth(300)
        self.lightLevelGroupBox.setEnabled(False)
    
    def setLightLevelModeManual(self):
        self.lightLevelStack.setCurrentIndex(1)
        self.lightLevelModeManual = True
        
    def setLightLevelModeMenu(self):
        self.lightLevelStack.setCurrentIndex(0)
        self.lightLevelModeManual = False
    
    def updateMeasuredLightIntensity(self,intensity):
        self.labelMeasuredLightIntensity.setText("Measured Light Intensity: " + "{:6.2f}".format(intensity) + "% sun")
    
    def setLightLevelList(self,lightLevelDict):
        self.menuSelectLightLevel.clear()
        for light in lightLevelDict:
            self.menuSelectLightLevel.addItem(light)
        self.lightLevelDictionary = lightLevelDict
    
    def createMeasurementGroupBox(self):
        #measurement group box
        self.measurementGroupBox = QGroupBox("Measurement")
        measurementGroupBoxLayout = QVBoxLayout()
        
        #combobox to select the measurement type
        #self.labelMeasurementMenu = QLabel("Select Measurement Type")
        self.menuSelectMeasurement = QComboBox()
        self.menuSelectMeasurement.setMaximumWidth(300)
        self.measurementList = ['J-V Scan','Constant Voltage, Measure J','Constant Current, Measure V','Maximum Power Point','Calibrate Reference Diode']
        for meas in self.measurementList:
            self.menuSelectMeasurement.addItem(meas)
        self.menuSelectMeasurement.currentIndexChanged.connect(self.selectMeasurement)
        #self.labelMeasurementMenu.setEnabled(False)
        #self.menuSelectMeasurement.setEnabled(False)
        
        #one panel per measurement type
        self.panelIVScan = QWidget()
        self.panelIVScan.setMaximumWidth(300)
        self.panelConstantV = QWidget()
        self.panelConstantV.setMaximumWidth(300)
        self.panelConstantI = QWidget()
        self.panelConstantI.setMaximumWidth(300)
        self.panelMaxPP = QWidget()
        self.panelMaxPP.setMaximumWidth(300)
        self.panelCalibration = QWidget()
        self.panelCalibration.setMaximumWidth(300)
        
        #IV Panel elements
        self.CheckBoxAutomaticLimits = QCheckBox("Use Automatic Limits (0 - Fwd Limit)")
        self.CheckBoxAutomaticLimits.stateChanged.connect(self.toggleIVLimitsMode)
        self.fieldIVMinV = QLineEdit("0.00")
        self.IVMinVValidator = QDoubleValidator()
        self.fieldIVMinV.setValidator(self.IVMinVValidator)
        self.labelIVMinV = QLabel("Minimum Voltage")
        self.IVMaxVUser = 1.2
        self.IVFwdLimitUser = 0.0
        self.fieldIVMaxV = QLineEdit(str(self.IVMaxVUser))
        self.fieldIVMaxV.textChanged.connect(self.IVMaxVTextChanged)
        self.IVMaxVValidator = QDoubleValidator()
        self.fieldIVMaxV.setValidator(self.IVMaxVValidator)
        self.labelIVMaxV = QLabel("Maximum Voltage")
        self.fieldIVVStep = QLineEdit("5.0")
        self.IVVStepValidator = QDoubleValidator()
        self.fieldIVVStep.setValidator(self.IVVStepValidator)
        self.labelIVVStep = QLabel("Voltage Step")
        self.fieldIVSweepRate = QLineEdit("20.0")
        self.IVSweepRateValidator = QDoubleValidator()
        self.fieldIVSweepRate.setValidator(self.IVSweepRateValidator)
        self.labelIVSweepRate = QLabel("Sweep Rate")
        self.fieldIVStabilizationTime = QLineEdit("5.0")
        self.IVStabilizationTimeValidator = QDoubleValidator()
        self.fieldIVStabilizationTime.setValidator(self.IVStabilizationTimeValidator)
        self.labelIVStabilizationTime = QLabel("Stabilization Time")
        self.labelIVStabilizationTimeUnits = QLabel("sec")
        self.labelIVSweepDirection = QLabel("Sweep Direction")
        self.menuIVSweepDirection = QComboBox()
        self.sweepDirectionList = ["Forward", "Reverse"]
        self.menuIVSweepDirection.addItem(self.sweepDirectionList[0])
        self.menuIVSweepDirection.addItem(self.sweepDirectionList[1])
        self.labelVolts = QLabel("V")
        self.labelIVMaxVUnits = QLabel("V")
        self.labelVolts2 = QLabel("mV")
        self.labelmVperSec = QLabel("mV/s")
        
        self.ButtonRunIV = QPushButton("Run J-V Scan", self)
        self.ButtonRunIV.clicked.connect(self.runIV)
        self.ButtonAbortIV = QPushButton("Abort J-V Scan", self)
        self.ButtonAbortIV.clicked.connect(self.abortRun)
        self.ButtonAbortIV.setEnabled(False)
        
        #JV panel layout
        IVScanFieldLayout = QGridLayout()
        IVScanFieldLayout.addWidget(self.labelIVMinV,0,0)
        IVScanFieldLayout.addWidget(self.fieldIVMinV,0,1)
        IVScanFieldLayout.addWidget(self.labelVolts,0,2)
        IVScanFieldLayout.addWidget(self.labelIVMaxV,1,0)
        IVScanFieldLayout.addWidget(self.fieldIVMaxV,1,1)
        IVScanFieldLayout.addWidget(self.labelIVMaxVUnits,1,2)
        IVScanFieldLayout.addWidget(self.labelIVVStep,2,0)
        IVScanFieldLayout.addWidget(self.fieldIVVStep,2,1)
        IVScanFieldLayout.addWidget(self.labelVolts2,2,2)
        IVScanFieldLayout.addWidget(self.labelIVSweepRate,3,0)
        IVScanFieldLayout.addWidget(self.fieldIVSweepRate,3,1)
        IVScanFieldLayout.addWidget(self.labelmVperSec,3,2)
        IVScanFieldLayout.addWidget(self.labelIVStabilizationTime,4,0)
        IVScanFieldLayout.addWidget(self.fieldIVStabilizationTime,4,1)
        IVScanFieldLayout.addWidget(self.labelIVStabilizationTimeUnits,4,2)
        IVScanFieldLayout.addWidget(self.labelIVSweepDirection,5,0)
        IVScanFieldLayout.addWidget(self.menuIVSweepDirection,5,1)
        
        IVScanLayout = QVBoxLayout()
        IVScanLayout.addWidget(self.CheckBoxAutomaticLimits)
        IVScanLayout.addLayout(IVScanFieldLayout)
        IVScanLayout.addWidget(self.ButtonRunIV)
        IVScanLayout.addWidget(self.ButtonAbortIV)
        self.panelIVScan.setLayout(IVScanLayout)
        
        #ConstantV Panel elements
        self.fieldConstantVSetV = QLineEdit("0.00")
        self.ConstantVSetVValidator = QDoubleValidator()
        self.fieldConstantVSetV.setValidator(self.ConstantVSetVValidator)
        self.labelConstantVSetV = QLabel("Set Voltage")
        self.fieldConstantVStabilizationTime = QLineEdit("5.0")
        self.ConstantVStabilizationTimeValidator = QDoubleValidator()
        self.fieldConstantVStabilizationTime.setValidator(self.ConstantVStabilizationTimeValidator)
        self.labelConstantVStabilizationTime = QLabel("Stabilization Time")
        self.labelConstantVStabilizationTimeUnits = QLabel("sec")
        self.fieldConstantVInterval = QLineEdit("0.50")
        self.ConstantVIntervalValidator = QDoubleValidator()
        self.fieldConstantVInterval.setValidator(self.ConstantVIntervalValidator)
        self.labelConstantVInterval = QLabel("Meas Interval")
        self.fieldConstantVDuration = QLineEdit("60.0")
        self.ConstantVDurationValidator = QDoubleValidator()
        self.fieldConstantVDuration.setValidator(self.ConstantVDurationValidator)
        self.labelConstantVDuration = QLabel("Meas Duration")
        self.labelVolts3 = QLabel("V")
        self.labelSeconds = QLabel("sec")
        self.labelSeconds1 = QLabel("sec")
        
        self.ButtonRunConstantV = QPushButton("Run Constant Voltage", self)
        self.ButtonRunConstantV.clicked.connect(self.runConstantV)
        self.ButtonAbortConstantV = QPushButton("Abort Measurement", self)
        self.ButtonAbortConstantV.clicked.connect(self.abortRun)
        self.ButtonAbortConstantV.setEnabled(False)
        
        #ConstantV panel layout
        ConstantVFieldLayout = QGridLayout()
        ConstantVFieldLayout.addWidget(self.labelConstantVSetV,0,0)
        ConstantVFieldLayout.addWidget(self.fieldConstantVSetV,0,1)
        ConstantVFieldLayout.addWidget(self.labelVolts3,0,2)
        ConstantVFieldLayout.addWidget(self.labelConstantVStabilizationTime,1,0)
        ConstantVFieldLayout.addWidget(self.fieldConstantVStabilizationTime,1,1)
        ConstantVFieldLayout.addWidget(self.labelConstantVStabilizationTimeUnits,1,2)
        ConstantVFieldLayout.addWidget(self.labelConstantVInterval,2,0)
        ConstantVFieldLayout.addWidget(self.fieldConstantVInterval,2,1)
        ConstantVFieldLayout.addWidget(self.labelSeconds,2,2)
        ConstantVFieldLayout.addWidget(self.labelConstantVDuration,3,0)
        ConstantVFieldLayout.addWidget(self.fieldConstantVDuration,3,1)
        ConstantVFieldLayout.addWidget(self.labelSeconds1,3,2)
        
        ConstantVLayout = QVBoxLayout()
        ConstantVLayout.addLayout(ConstantVFieldLayout)
        ConstantVLayout.addWidget(self.ButtonRunConstantV)
        ConstantVLayout.addWidget(self.ButtonAbortConstantV)
        self.panelConstantV.setLayout(ConstantVLayout)
        
        #ConstantI Panel elements
        self.fieldConstantISetI = QLineEdit("0.00")
        self.ConstantISetIValidator = QDoubleValidator()
        self.fieldConstantISetI.setValidator(self.ConstantISetIValidator)
        self.labelConstantISetI = QLabel("Set Current")
        self.fieldConstantIStabilizationTime = QLineEdit("5.0")
        self.ConstantIStabilizationTimeValidator = QDoubleValidator()
        self.fieldConstantIStabilizationTime.setValidator(self.ConstantIStabilizationTimeValidator)
        self.labelConstantIStabilizationTime = QLabel("Stabilization Time")
        self.labelConstantIStabilizationTimeUnits = QLabel("sec")
        self.fieldConstantIInterval = QLineEdit("0.50")
        self.ConstantIIntervalValidator = QDoubleValidator()
        self.fieldConstantIInterval.setValidator(self.ConstantIIntervalValidator)
        self.labelConstantIInterval = QLabel("Meas Interval")
        self.fieldConstantIDuration = QLineEdit("60.0")
        self.ConstantIDurationValidator = QDoubleValidator()
        self.fieldConstantIDuration.setValidator(self.ConstantIDurationValidator)
        self.labelConstantIDuration = QLabel("Meas Duration")
        self.labelMilliAmps = QLabel("mA")
        self.labelSeconds2 = QLabel("sec")
        self.labelSeconds3 = QLabel("sec")
        
        self.ButtonRunConstantI = QPushButton("Run Constant Current", self)
        self.ButtonRunConstantI.clicked.connect(self.runConstantI)
        self.ButtonAbortConstantI = QPushButton("Abort Measurement", self)
        self.ButtonAbortConstantI.clicked.connect(self.abortRun)
        self.ButtonAbortConstantI.setEnabled(False)
        
        #ConstantI panel layout
        ConstantIFieldLayout = QGridLayout()
        ConstantIFieldLayout.addWidget(self.labelConstantISetI,0,0)
        ConstantIFieldLayout.addWidget(self.fieldConstantISetI,0,1)
        ConstantIFieldLayout.addWidget(self.labelMilliAmps,0,2)
        ConstantIFieldLayout.addWidget(self.labelConstantIStabilizationTime,1,0)
        ConstantIFieldLayout.addWidget(self.fieldConstantIStabilizationTime,1,1)
        ConstantIFieldLayout.addWidget(self.labelConstantIStabilizationTimeUnits,1,2)
        ConstantIFieldLayout.addWidget(self.labelConstantIInterval,2,0)
        ConstantIFieldLayout.addWidget(self.fieldConstantIInterval,2,1)
        ConstantIFieldLayout.addWidget(self.labelSeconds2,2,2)
        ConstantIFieldLayout.addWidget(self.labelConstantIDuration,3,0)
        ConstantIFieldLayout.addWidget(self.fieldConstantIDuration,3,1)
        ConstantIFieldLayout.addWidget(self.labelSeconds3,3,2)
        
        ConstantILayout = QVBoxLayout()
        ConstantILayout.addLayout(ConstantIFieldLayout)
        ConstantILayout.addWidget(self.ButtonRunConstantI)
        ConstantILayout.addWidget(self.ButtonAbortConstantI)
        self.panelConstantI.setLayout(ConstantILayout)
        
        #MaxPP Panel elements
        self.CheckBoxAutomaticMpp = QCheckBox("Find Start Voltage Automatically")
        self.CheckBoxAutomaticMpp.stateChanged.connect(self.toggleMppStartMode)
        self.fieldMaxPPStartV = QLineEdit("1.00")
        self.MaxPPStartVValidator = QDoubleValidator()
        self.fieldMaxPPStartV.setValidator(self.MaxPPStartVValidator)
        self.labelMaxPPStartV = QLabel("Start Voltage")
        self.fieldMaxPPStabilizationTime = QLineEdit("5.0")
        self.MaxPPStabilizationTimeValidator = QDoubleValidator()
        self.fieldMaxPPStabilizationTime.setValidator(self.MaxPPStabilizationTimeValidator)
        self.labelMaxPPStabilizationTime = QLabel("Stabilization Time")
        self.labelMaxPPStabilizationTimeUnits = QLabel("sec")
        self.fieldMaxPPInterval = QLineEdit("0.50")
        self.MaxPPIntervalValidator = QDoubleValidator()
        self.fieldMaxPPInterval.setValidator(self.MaxPPIntervalValidator)
        self.labelMaxPPInterval = QLabel("Meas Interval")
        self.fieldMaxPPDuration = QLineEdit("60.0")
        self.MaxPPDurationValidator = QDoubleValidator()
        self.fieldMaxPPDuration.setValidator(self.MaxPPDurationValidator)
        self.labelMaxPPDuration = QLabel("Meas Duration")
        self.labelVolts4 = QLabel("V")
        self.labelSeconds4 = QLabel("sec")
        self.labelSeconds5 = QLabel("sec")
        
        self.ButtonRunMaxPP = QPushButton("Run Max Power Point", self)
        self.ButtonRunMaxPP.clicked.connect(self.runMaxPP)
        self.ButtonAbortMaxPP = QPushButton("Abort Measurement", self)
        self.ButtonAbortMaxPP.clicked.connect(self.abortRun)
        self.ButtonAbortMaxPP.setEnabled(False)
        
        #MaxPP panel layout
        MaxPPFieldLayout = QGridLayout()
        MaxPPFieldLayout.addWidget(self.labelMaxPPStartV,0,0)
        MaxPPFieldLayout.addWidget(self.fieldMaxPPStartV,0,1)
        MaxPPFieldLayout.addWidget(self.labelVolts4,0,2)
        MaxPPFieldLayout.addWidget(self.labelMaxPPStabilizationTime,1,0)
        MaxPPFieldLayout.addWidget(self.fieldMaxPPStabilizationTime,1,1)
        MaxPPFieldLayout.addWidget(self.labelMaxPPStabilizationTimeUnits,1,2)
        MaxPPFieldLayout.addWidget(self.labelMaxPPInterval,2,0)
        MaxPPFieldLayout.addWidget(self.fieldMaxPPInterval,2,1)
        MaxPPFieldLayout.addWidget(self.labelSeconds4,2,2)
        MaxPPFieldLayout.addWidget(self.labelMaxPPDuration,3,0)
        MaxPPFieldLayout.addWidget(self.fieldMaxPPDuration,3,1)
        MaxPPFieldLayout.addWidget(self.labelSeconds5,3,2)
        
        MaxPPLayout = QVBoxLayout()
        MaxPPLayout.addWidget(self.CheckBoxAutomaticMpp)
        MaxPPLayout.addLayout(MaxPPFieldLayout)
        MaxPPLayout.addWidget(self.ButtonRunMaxPP)
        MaxPPLayout.addWidget(self.ButtonAbortMaxPP)
        self.panelMaxPP.setLayout(MaxPPLayout)
        
        #Calibration Panel elements
        self.labelCalibrationDiodeReferenceCurrent = QLabel("Calibration Diode Iref")
        self.fieldCalibrationDiodeReferenceCurrent = QLineEdit("1.00")
        self.CalibrationDiodeReferenceCurrentValidator = QDoubleValidator()
        self.fieldCalibrationDiodeReferenceCurrent.setValidator(self.CalibrationDiodeReferenceCurrentValidator)
        self.labelCalibrationDiodeReferenceCurrentUnits = QLabel("mA")
        self.fieldCalibrationStabilizationTime = QLineEdit("5.0")
        self.CalibrationStabilizationTimeValidator = QDoubleValidator()
        self.fieldCalibrationStabilizationTime.setValidator(self.CalibrationStabilizationTimeValidator)
        self.labelCalibrationStabilizationTime = QLabel("Stabilization Time")
        self.labelCalibrationStabilizationTimeUnits = QLabel("sec")
        self.fieldCalibrationInterval = QLineEdit("0.50")
        self.CalibrationIntervalValidator = QDoubleValidator()
        self.fieldCalibrationInterval.setValidator(self.CalibrationIntervalValidator)
        self.labelCalibrationInterval = QLabel("Meas Interval")
        self.fieldCalibrationDuration = QLineEdit("60.0")
        self.CalibrationDurationValidator = QDoubleValidator()
        self.fieldCalibrationDuration.setValidator(self.CalibrationDurationValidator)
        self.labelCalibrationDuration = QLabel("Meas Duration")
        self.labelSeconds4 = QLabel("sec")
        self.labelSeconds5 = QLabel("sec")
        
        self.ButtonRunCalibration = QPushButton("Run Calibration", self)
        self.ButtonRunCalibration.clicked.connect(self.runCalibration)
        self.ButtonAbortCalibration = QPushButton("Abort Measurement", self)
        self.ButtonAbortCalibration.clicked.connect(self.abortRun)
        self.ButtonAbortCalibration.setEnabled(False)
        
        self.labelCalibrationReferenceCellCurrent = QLabel("Reference Diode Iref")
        self.fieldCalibrationReferenceCellCurrent = QLineEdit("1.00")
        self.CalibrationReferenceCellCurrentValidator = QDoubleValidator()
        self.fieldCalibrationReferenceCellCurrent.setValidator(self.CalibrationReferenceCellCurrentValidator)
        self.labelCalibrationReferenceCellCurrentUnits = QLabel("mA")
        CalibrationDiodeCurrentLayout = QGridLayout()
        CalibrationDiodeCurrentLayout.addWidget(self.labelCalibrationReferenceCellCurrent,0,0)
        CalibrationDiodeCurrentLayout.addWidget(self.fieldCalibrationReferenceCellCurrent,0,1)
        CalibrationDiodeCurrentLayout.addWidget(self.labelCalibrationReferenceCellCurrentUnits,0,2)
        
        self.ButtonSaveCalibration = QPushButton("Save Calibration", self)
        self.ButtonSaveCalibration.clicked.connect(self.saveCalibration)
        self.ButtonSaveCalibration.setEnabled(False)
        
        #Calibration panel layout
        CalibrationFieldLayout = QGridLayout()
        CalibrationFieldLayout.addWidget(self.labelCalibrationDiodeReferenceCurrent,0,0)
        CalibrationFieldLayout.addWidget(self.fieldCalibrationDiodeReferenceCurrent,0,1)
        CalibrationFieldLayout.addWidget(self.labelCalibrationDiodeReferenceCurrentUnits,0,2)
        CalibrationFieldLayout.addWidget(self.labelCalibrationStabilizationTime,1,0)
        CalibrationFieldLayout.addWidget(self.fieldCalibrationStabilizationTime,1,1)
        CalibrationFieldLayout.addWidget(self.labelCalibrationStabilizationTimeUnits,1,2)
        CalibrationFieldLayout.addWidget(self.labelCalibrationInterval,2,0)
        CalibrationFieldLayout.addWidget(self.fieldCalibrationInterval,2,1)
        CalibrationFieldLayout.addWidget(self.labelSeconds4,2,2)
        CalibrationFieldLayout.addWidget(self.labelCalibrationDuration,3,0)
        CalibrationFieldLayout.addWidget(self.fieldCalibrationDuration,3,1)
        CalibrationFieldLayout.addWidget(self.labelSeconds5,3,2)
        
        CalibrationLayout = QVBoxLayout()
        CalibrationLayout.addLayout(CalibrationFieldLayout)
        CalibrationLayout.addWidget(self.ButtonRunCalibration)
        CalibrationLayout.addWidget(self.ButtonAbortCalibration)
        CalibrationLayout.addWidget(self.labelCalibrationReferenceCellCurrent)
        CalibrationLayout.addLayout(CalibrationDiodeCurrentLayout)
        CalibrationLayout.addWidget(self.ButtonSaveCalibration)
        self.panelCalibration.setLayout(CalibrationLayout)
        
        
        self.measurementStack = QStackedWidget()
        self.measurementStack.addWidget(self.panelIVScan)
        self.measurementStack.addWidget(self.panelConstantV)
        self.measurementStack.addWidget(self.panelConstantI)
        self.measurementStack.addWidget(self.panelMaxPP)
        self.measurementStack.addWidget(self.panelCalibration)
        #self.measurementStack.setEnabled(False)
        
        measurementGroupBoxLayout.addWidget(self.menuSelectMeasurement)
        measurementGroupBoxLayout.addWidget(self.measurementStack)
        self.measurementGroupBox.setLayout(measurementGroupBoxLayout)
        self.measurementGroupBox.setEnabled(False)
        self.measurementGroupBox.setMaximumWidth(300)
    
    def createComplianceGroupBox(self):
        #Compliance Voltage and current
        self.ComplianceGroupBox = QGroupBox("SMU Configuration")
        ComplianceLayout = QGridLayout()
        
        self.label2wire4wire = QLabel("Measurement mode")
        self.menu2wire4wire = QComboBox()
        self.menu2wire4wire.setMaximumWidth(300)
        self.menu2wire4wire.addItem("2 wire")
        self.menu2wire4wire.addItem("4 wire")
        
        self.labelVoltageLimit = QLabel("Voltage Limit")
        self.fieldVoltageLimit = QLineEdit("2.00")
        self.voltageLimitValidator = QDoubleValidator()
        self.fieldVoltageLimit.setValidator(self.voltageLimitValidator)
        self.fieldVoltageLimit.setMaximumWidth(75)
        self.labelVoltageLimitUnits = QLabel("V")
        self.labelCurrentLimit = QLabel("Current Limit")
        self.fieldCurrentLimit = QLineEdit("5.00")
        self.currentLimitValidator = QDoubleValidator()
        self.fieldCurrentLimit.setValidator(self.currentLimitValidator)
        self.fieldCurrentLimit.setMaximumWidth(75)
        self.labelCurrentLimitUnits = QLabel("mA")
        
        ComplianceLayout.addWidget(self.label2wire4wire,0,0)
        ComplianceLayout.addWidget(self.menu2wire4wire,0,1)
        ComplianceLayout.addWidget(self.labelVoltageLimit,1,0)
        ComplianceLayout.addWidget(self.fieldVoltageLimit,1,1)
        ComplianceLayout.addWidget(self.labelVoltageLimitUnits,1,2)
        ComplianceLayout.addWidget(self.labelCurrentLimit,2,0)
        ComplianceLayout.addWidget(self.fieldCurrentLimit,2,1)
        ComplianceLayout.addWidget(self.labelCurrentLimitUnits,2,2)
        
        self.ComplianceGroupBox.setLayout(ComplianceLayout)
        self.ComplianceGroupBox.setMaximumWidth(300)
        self.ComplianceGroupBox.setEnabled(False)
    
    def createCellSizeWidget(self):   
        # cell active area
        self.cellSizeWidget = QWidget()
        cellSizeLayout = QHBoxLayout()
        self.labelCellActiveArea = QLabel("Cell Active Area")
        self.fieldCellActiveArea = QLineEdit("1.00")
        self.CellActiveAreaValidator = QDoubleValidator()
        self.fieldCellActiveArea.setValidator(self.CellActiveAreaValidator)
        self.fieldCellActiveArea.setMaximumWidth(75)
        self.labelCellActiveAreaUnits = QLabel("cm<sup>2<\sup>")
        cellSizeLayout.addWidget(self.labelCellActiveArea)
        cellSizeLayout.addWidget(self.fieldCellActiveArea)
        cellSizeLayout.addWidget(self.labelCellActiveAreaUnits)
        self.cellSizeWidget.setLayout(cellSizeLayout)
        self.cellSizeWidget.setEnabled(False)
    
    #argument 'e' is of type QMouseEvent.
    def clearCellName(self, e):
        cellName = self.fieldCellName.text()
        if cellName == "Enter Cell Name Here...":
            self.fieldCellName.setText("")
    
    def clearUserName(self, e):
        userName = self.fieldUserName.text()
        if userName == "Username":
            self.fieldUserName.setText("")
    
    def clearSciper(self, e):
        sciper = self.fieldUserSciper.text()
        if sciper == "Sciper":
            self.fieldUserSciper.setText("")
        
    def createPlotHeaderWidget(self):   
        #buttons and fields above the plot
        self.fieldCellName = QLineEdit("")
        self.fieldCellName.setPlaceholderText("Enter Cell Name Here...")
        self.fieldCellName.setMinimumWidth(500)
        self.fieldCellName.setEnabled(False)
        #self.fieldCellName.mousePressEvent = self.clearCellName
        #self.fieldCellName.cursorPositionChanged.connect(self.clearCellName)
        
        self.checkBoxAutoSave = QCheckBox("Auto-save")
        self.checkBoxAutoSave.setEnabled(False)
        self.checkBoxAutoSave.stateChanged.connect(self.toggleAutoSaveMode)
        
        self.buttonSaveData = QPushButton("Save Data",self)
        self.buttonSaveData.clicked.connect(self.saveScanData)
        self.buttonSaveData.setEnabled(False)
        self.buttonSaveData.setEnabled(False)
        
        self.panelLogIn = QWidget()
        panelLogInLayout = QHBoxLayout()
        self.fieldUserName = QLineEdit("")
        self.fieldUserName.setPlaceholderText("Username")
        self.fieldUserName.setMinimumWidth(100)
        #self.fieldUserName.cursorPositionChanged.connect(self.clearUserName)
        self.fieldUserSciper = QLineEdit("")
        self.fieldUserSciper.setPlaceholderText("Sciper")
        self.fieldUserSciper.returnPressed.connect(self.logIn)
        self.fieldUserSciper.setMinimumWidth(100)
        #self.fieldUserSciper.cursorPositionChanged.connect(self.clearSciper)
        self.buttonLogIn = QPushButton("Log In",self)
        self.buttonLogIn.clicked.connect(self.logIn)
        
        panelLogInLayout.addWidget(self.fieldUserName)
        panelLogInLayout.addWidget(self.fieldUserSciper)
        panelLogInLayout.addWidget(self.buttonLogIn)
        self.panelLogIn.setLayout(panelLogInLayout)
        #self.panelLogIn.setMaximumHeight(35)
        
        self.panelLogOut = QWidget()
        panelLogOutLayout = QHBoxLayout()
        self.labelLoggedInAs = QLabel("Logged in as: ")
        self.labelUserName = QLabel("jean toutlemonde")
        self.buttonLogOut = QPushButton("Log Out",self)
        self.buttonLogOut.clicked.connect(self.logOut)
        
        panelLogOutLayout.addWidget(self.labelLoggedInAs)
        panelLogOutLayout.addWidget(self.labelUserName)
        panelLogOutLayout.addWidget(self.buttonLogOut)
        self.panelLogOut.setLayout(panelLogOutLayout)
        #self.panelLogOut.setMaximumHeight(35)
        
        self.StackLogInOut = QStackedWidget()
        self.StackLogInOut.addWidget(self.panelLogIn)
        self.StackLogInOut.addWidget(self.panelLogOut)
        #self.StackLogInOut.setMaximumHeight(40)
        self.StackLogInOut.setCurrentIndex(0) # 0 = login, 1 = logout
        
        # Set the plot header layout
        self.plotHeader = QWidget()
        headerLayout = QHBoxLayout()
        headerLayout.addWidget(self.fieldCellName)
        headerLayout.addWidget(self.checkBoxAutoSave)
        headerLayout.addWidget(self.buttonSaveData)
        headerLayout.addStretch(1)
        headerLayout.addWidget(self.StackLogInOut)
        self.plotHeader.setLayout(headerLayout)
    
    def createGraphPanels(self):
        # Graph Widgets
        self.StackGraphPanels = QStackedWidget()
        self.panelGraphIV = QWidget()
        self.panelGraphConstantV = QWidget()
        self.panelGraphConstantI = QWidget()
        self.panelGraphMPP = QWidget()
        self.panelGraphMPPIV = QWidget()
        self.panelGraphCalibration = QWidget()
        
        #IV plot widget and panel
        self.graphWidgetIV = pg.PlotWidget()
        #self.graphWidget.setMaximumWidth(2000) # does not appear to do anything
        #self.graphWidget.setMinimumSize(800,600)  # does not appear to do anything
        self.graphWidgetIV.setBackground('w')
        self.graphWidgetIV.showGrid(x = True, y = True, alpha = 0.3)
        self.graphWidgetIV.setLabel('left','Current (mA/cm<sup>2<\sup>)')
        self.graphWidgetIV.setLabel('bottom','Voltage (V)')
        self.curve_IV_valid = False
        #self.curve = self.graphWidget.plot([1,2,3],[1,2,3],pen=pg.mkPen('r', width=2))
        #self.graphWidget.setFrameStyle(QFrame.Panel | QFrame.Raised)
        #pg.setConfigOption('foreground','r')
        
        #fields to give values computed from IV scan
        self.IVResultsWidget = QWidget()
        IVResultsLayout = QGridLayout()
        
        self.labelJsc = QLabel("Jsc:")
        self.fieldJsc = QLabel("-----")
        self.labelJscUnits = QLabel("mA/cm<sup>2<\sup>")
        
        self.labelVoc = QLabel("Voc:")
        self.fieldVoc = QLabel("-----")
        self.labelVocUnits = QLabel("V")
        
        self.labelFillFactor = QLabel("Fill Factor:")
        self.fieldFillFactor = QLabel("-----")
        self.labelFillFactorUnits = QLabel("")
        
        self.labelPce = QLabel("PCE:")
        self.fieldPce = QLabel("-----")
        self.labelPceUnits = QLabel("%")
        
        self.labelJmpp = QLabel("Jmpp:")
        self.fieldJmpp = QLabel("-----")
        self.labelJmppUnits = QLabel("mA/cm<sup>2<\sup>")
        
        self.labelVmpp = QLabel("Vmpp:")
        self.fieldVmpp = QLabel("-----")
        self.labelVmppUnits = QLabel("V")
        
        self.labelPmpp = QLabel("Pmpp:")
        self.fieldPmpp = QLabel("-----")
        self.labelPmppUnits = QLabel("mW/cm<sup>2<\sup>")
        
        self.labelLightInt = QLabel("Light Intensity:")
        self.fieldLightInt = QLabel("-----")
        self.labelLightIntUnits = QLabel("% sun")
        
        IVResultsLayoutVoc = QHBoxLayout()
        IVResultsLayoutVoc.addWidget(self.labelVoc)
        IVResultsLayoutVoc.addWidget(self.fieldVoc)
        IVResultsLayoutVoc.addWidget(self.labelVocUnits)
        #IVResultsLayoutLine1.addStretch(1)
        IVResultsLayoutVmpp = QHBoxLayout()
        IVResultsLayoutVmpp.addWidget(self.labelVmpp)
        IVResultsLayoutVmpp.addWidget(self.fieldVmpp)
        IVResultsLayoutVmpp.addWidget(self.labelVmppUnits)
        #IVResultsLayoutLine1.addStretch(1)
        IVResultsLayoutPmpp = QHBoxLayout()
        IVResultsLayoutPmpp.addWidget(self.labelPmpp)
        IVResultsLayoutPmpp.addWidget(self.fieldPmpp)
        IVResultsLayoutPmpp.addWidget(self.labelPmppUnits)
        #IVResultsLayoutLine1.addStretch(1)
        IVResultsLayoutJsc = QHBoxLayout()
        IVResultsLayoutJsc.addWidget(self.labelJsc)
        IVResultsLayoutJsc.addWidget(self.fieldJsc)
        IVResultsLayoutJsc.addWidget(self.labelJscUnits)
        #IVResultsLayoutLine2.addStretch(1)
        IVResultsLayoutPce = QHBoxLayout()
        IVResultsLayoutPce.addWidget(self.labelPce)
        IVResultsLayoutPce.addWidget(self.fieldPce)
        IVResultsLayoutPce.addWidget(self.labelPceUnits)
        #IVResultsLayoutLine2.addStretch(1)
        IVResultsLayoutJmpp = QHBoxLayout()
        IVResultsLayoutJmpp.addWidget(self.labelJmpp)
        IVResultsLayoutJmpp.addWidget(self.fieldJmpp)
        IVResultsLayoutJmpp.addWidget(self.labelJmppUnits)
        #IVResultsLayoutLine2.addStretch(1)
        IVResultsLayoutFF = QHBoxLayout()
        IVResultsLayoutFF.addWidget(self.labelFillFactor)
        IVResultsLayoutFF.addWidget(self.fieldFillFactor)
        IVResultsLayoutFF.addWidget(self.labelFillFactorUnits)
        #IVResultsLayoutLine2.addStretch(1)
        IVResultsLayoutLightInt = QHBoxLayout()
        IVResultsLayoutLightInt.addWidget(self.labelLightInt)
        IVResultsLayoutLightInt.addWidget(self.fieldLightInt)
        IVResultsLayoutLightInt.addWidget(self.labelLightIntUnits)
        
        IVResultsLayout.addLayout(IVResultsLayoutJsc,0,0)
        IVResultsLayout.addLayout(IVResultsLayoutVoc,1,0)
        IVResultsLayout.addLayout(IVResultsLayoutFF,2,0)
        IVResultsLayout.addLayout(IVResultsLayoutPce,3,0)
        IVResultsLayout.addLayout(IVResultsLayoutJmpp,0,2)
        IVResultsLayout.addLayout(IVResultsLayoutVmpp,1,2)
        IVResultsLayout.addLayout(IVResultsLayoutPmpp,2,2)
        IVResultsLayout.addLayout(IVResultsLayoutLightInt,3,2)
        IVResultsLayout.setColumnStretch(1,1)
        IVResultsLayout.setColumnStretch(3,1)
        #IVResultsLayout.setColumnStretch(5,1)
        
        self.IVResultsWidget.setLayout(IVResultsLayout)
        self.IVResultsWidget.setEnabled(False)

        panelGraphIVLayout = QVBoxLayout()
        panelGraphIVLayout.addWidget(self.graphWidgetIV)
        panelGraphIVLayout.addWidget(self.IVResultsWidget)
        self.panelGraphIV.setLayout(panelGraphIVLayout)
        
        self.StackGraphPanels.addWidget(self.panelGraphIV)
        
        #Constant V plot widget and panel
        self.graphWidgetConstantV = pg.PlotWidget()
        self.graphWidgetConstantV.setBackground('w')
        self.graphWidgetConstantV.showGrid(x = True, y = True, alpha = 0.3)
        self.graphWidgetConstantV.setLabel('left','Current (mA/cm<sup>2<\sup>)')
        self.graphWidgetConstantV.setLabel('bottom','Time (sec)')
        self.curve_ConstantV_valid = False
        
        panelGraphConstantVLayout = QVBoxLayout()
        panelGraphConstantVLayout.addWidget(self.graphWidgetConstantV)
        self.panelGraphConstantV.setLayout(panelGraphConstantVLayout)
        
        self.StackGraphPanels.addWidget(self.panelGraphConstantV)
        
        #Constant I plot widget and panel
        self.graphWidgetConstantI = pg.PlotWidget()
        self.graphWidgetConstantI.setBackground('w')
        self.graphWidgetConstantI.showGrid(x = True, y = True, alpha = 0.3)
        self.graphWidgetConstantI.setLabel('left','Voltage (V)')
        self.graphWidgetConstantI.setLabel('bottom','Time (sec)')
        self.curve_ConstantI_valid = False
        
        panelGraphConstantILayout = QVBoxLayout()
        panelGraphConstantILayout.addWidget(self.graphWidgetConstantI)
        self.panelGraphConstantI.setLayout(panelGraphConstantILayout)
        
        self.StackGraphPanels.addWidget(self.panelGraphConstantI)
        
        #MPP plot widgets and panel
        self.graphWidgetMPP = pg.PlotWidget()
        self.graphWidgetMPP.setBackground('w')
        self.graphWidgetMPP.showGrid(x = True, y = True, alpha = 0.3)
        self.graphWidgetMPP.setLabel('left','Power (mW/cm<sup>2<\sup>)')
        self.graphWidgetMPP.setLabel('bottom','Time (sec)')
        self.curve_MPP_valid = False
        
        self.graphWidgetMPPIV = pg.PlotWidget()
        self.graphWidgetMPPIV.setBackground('w')
        #get the plotItem from the plotWidget
        self.plotItemMPPIV = self.graphWidgetMPPIV.plotItem
        self.plotItemMPPIV.setLabel('left','MPP Voltage (V)',color='#ff0000')
        self.plotItemMPPIV.showGrid(x = True, y = True, alpha = 0.3)
        self.plotItemMPPIV.setLabel('bottom','Time (sec)')
        self.plotItemMPPIV.setLabel('right','MPP Current (mA/cm<sup>2<\sup>)', color='#0000ff')
        self.curveMPPV = self.plotItemMPPIV.plot(x=[], y=[], pen=pg.mkPen('r', width=2))
   
        #create new viewbox to contain second plot, link it to the plot item, and add a curve to it
        self.viewBoxMPPI = pg.ViewBox()
        self.plotItemMPPIV.scene().addItem(self.viewBoxMPPI)
        self.plotItemMPPIV.getAxis('right').linkToView(self.viewBoxMPPI)
        self.viewBoxMPPI.setXLink(self.plotItemMPPIV)
        self.curveMPPI = pg.PlotCurveItem(pen=pg.mkPen('b', width=2))
        self.viewBoxMPPI.addItem(self.curveMPPI)
        #viewbox for 2nd curve needs to be told to track the size of the main plot on each change
        self.plotItemMPPIV.vb.sigResized.connect(self.updateViewsMPPIV)
        
        panelGraphMPPLayout = QVBoxLayout()
        panelGraphMPPLayout.addWidget(self.graphWidgetMPP)
        panelGraphMPPLayout.addWidget(self.graphWidgetMPPIV)
        self.panelGraphMPP.setLayout(panelGraphMPPLayout)
        
        self.StackGraphPanels.addWidget(self.panelGraphMPP)
        
        #Calibration plot widgets and panel
        """self.graphWidgetCalibration = pg.PlotWidget()
        self.graphWidgetCalibration.setBackground('w')
        self.graphWidgetCalibration.showGrid(x = True, y = True, alpha = 0.3)
        self.graphWidgetCalibration.setLabel('left','Power (mW/cm^2)')
        self.graphWidgetCalibration.setLabel('bottom','Time (sec)')
        self.curve_Calibration_valid = False
        """
        self.graphWidgetCalibration = pg.PlotWidget()
        self.graphWidgetCalibration.setBackground('w')
        #get the plotItem from the plotWidget
        self.plotItemCalibration = self.graphWidgetCalibration.plotItem
        self.plotItemCalibration.setLabel('left','Calibration Diode Current (mA)',color='#ff0000')
        self.plotItemCalibration.showGrid(x = True, y = True, alpha = 0.3)
        self.plotItemCalibration.setLabel('bottom','Time (sec)')
        self.plotItemCalibration.setLabel('right','Reference Diode Current (mA)', color='#0000ff')
        self.curveCalibrationMeas = self.plotItemCalibration.plot(x=[], y=[], pen=pg.mkPen('r', width=2))
   
        #create new viewbox to contain second plot, link it to the plot item, and add a curve to it
        self.viewBoxCalibrationRef = pg.ViewBox()
        self.plotItemCalibration.scene().addItem(self.viewBoxCalibrationRef)
        self.plotItemCalibration.getAxis('right').linkToView(self.viewBoxCalibrationRef)
        self.viewBoxCalibrationRef.setXLink(self.plotItemCalibration)
        self.curveCalibrationRef = pg.PlotCurveItem(pen=pg.mkPen('b', width=2))
        self.viewBoxCalibrationRef.addItem(self.curveCalibrationRef)
        #viewbox for 2nd curve needs to be told to track the size of the main plot on each change
        self.plotItemCalibration.vb.sigResized.connect(self.updateViewsCalibration)
        
        panelGraphCalibrationLayout = QVBoxLayout()
        panelGraphCalibrationLayout.addWidget(self.graphWidgetCalibration)
        self.panelGraphCalibration.setLayout(panelGraphCalibrationLayout)
        
        self.StackGraphPanels.addWidget(self.panelGraphCalibration)
    
    def selectMeasurement(self,i):
        self.measurementStack.setCurrentIndex(i)
        self.StackGraphPanels.setCurrentIndex(i)
    
    def logOut(self):
        dlg = LogOffDialog(self)
        if not dlg.exec():
            return
        
        #self.signal_log_out.emit() - this signal is now emitted by the LogOffDialog
        self.setHardwareActive(False)
        self.buttonInitialize.setEnabled(False)
        self.fieldCellName.setEnabled(False)
        self.checkBoxAutoSave.setEnabled(False)
        self.buttonSaveData.setEnabled(False)
        self.cellSizeWidget.setEnabled(False)
        self.ButtonResetToDefault.setEnabled(False)
        self.IVResultsWidget.setEnabled(False)
        self.clearPlotIV()
        self.clearPlotConstantV()
        self.clearPlotConstantI()
        self.clearPlotMPP()
        self.clearPlotMPPIV()
        self.clearPlotCalibration()
        self.curve_valid = False
        self.StackLogInOut.setCurrentIndex(0)
        # should call set all fields to default from the application logic after receiving logout signal
        # cannot call this here as we need to be sure the application is done saving the config file
        # before clearing the current values from all the fields.
        #self.setAllFieldsToDefault()
    
    # this function sends login details down to the application logic
    # application logic should call logInValid() if the username/pwd combo is good.
    def logIn(self):
        username = self.fieldUserName.text()
        userSciper = self.fieldUserSciper.text()
        logInValid = False
        self.signal_log_in.emit(username,userSciper)        
      
    def logInValid(self,username):
        self.buttonInitialize.setEnabled(True)
        self.fieldCellName.setEnabled(True)
        self.checkBoxAutoSave.setEnabled(True)
        self.cellSizeWidget.setEnabled(True)
        self.ButtonResetToDefault.setEnabled(True)
        self.IVResultsWidget.setEnabled(True)
        self.labelUserName.setText(username)
        self.StackLogInOut.setCurrentIndex(1)
        #ugly hack to get around cursorPositionChanged event...
        #this event is not called when deleting a character, so write our default string
        #with a dot at the start, move the cursor to the start, and delete
        #otherwise if we put this string in directly the cursorPositionChanged callback
        #is activated and our default string is deleted.
        self.fieldUserName.setText("")
        self.fieldUserName.setCursorPosition(0)
        self.fieldUserName.del_()
        self.fieldUserSciper.setText("")
        self.fieldUserSciper.setCursorPosition(0)
        self.fieldUserSciper.del_()
    
    # tell the application logic to initialize the hardware.
    # application logic should call setHardwareActive() if this is successful.
    def initializeHardware(self):
        self.signal_initialize_hardware.emit()
        #self.setHardwareActive(True) 
    
    def setHardwareActive(self,active):
        #self.labelLightLevelMenu.setEnabled(active)
        self.lightLevelGroupBox.setEnabled(active)
        #self.menuSelectLightLevel.setEnabled(active)
        #self.labelMeasurementMenu.setEnabled(active)
        self.measurementGroupBox.setEnabled(active)
        #self.menuSelectMeasurement.setEnabled(active)
        #self.Stack.setEnabled(active)
        self.ComplianceGroupBox.setEnabled(active)
    
    def launchDataFilePathDialog(self):
        fname, _ = QFileDialog.getOpenFileName(self, 'Open file', 'c:\\',"text files (*.txt)")
        if fname != "":
            pass
            #print(fname)
            #self.fieldDataFilePath.setText(fname)
    
    def IVMaxVTextChanged(self):
        if self.CheckBoxAutomaticLimits.isChecked():
            self.IVFwdLimitUser = float(self.fieldIVMaxV.text())
        else:
            self.IVMaxVUser = float(self.fieldIVMaxV.text())
    
    def toggleIVLimitsMode(self):
        if self.CheckBoxAutomaticLimits.isChecked():
            self.fieldIVMinV.setEnabled(False)
            #self.fieldIVMaxV.setEnabled(False)
            self.fieldIVMaxV.setText(str(self.IVFwdLimitUser))
            self.labelIVMaxV.setText("Fwd Current Limit")
            self.labelIVMaxVUnits.setText("mA/cm<sup>2<\sup>")
        else:
            self.fieldIVMinV.setEnabled(True)
            #self.fieldIVMaxV.setEnabled(True)
            self.fieldIVMaxV.setText(str(self.IVMaxVUser))
            self.labelIVMaxV.setText("Maximum Voltage")
            self.labelIVMaxVUnits.setText("V")
    
    def toggleMppStartMode(self):
        if self.CheckBoxAutomaticMpp.isChecked():
            self.fieldMaxPPStartV.setEnabled(False)
        else:
            self.fieldMaxPPStartV.setEnabled(True)
    
    def runIV(self):
        
        sweepDir = self.sweepDirectionList[self.menuIVSweepDirection.currentIndex()]
        dV = float(self.fieldIVVStep.text())/1000. # field value is mV
        Vcompliance = abs(float(self.fieldVoltageLimit.text()))
        Icompliance = abs(float(self.fieldCurrentLimit.text())/1000.)
        cell_active_area = float(self.fieldCellActiveArea.text())
        
        if self.CheckBoxAutomaticLimits.isChecked():
            limitsMode = 'Automatic'
            FwdCurrentLimit = float(self.fieldIVMaxV.text()) * cell_active_area / 1000.
            if sweepDir == 'Forward':
                startV = 0.0
                stopV = 'Voc'
                dV = abs(dV)
            else:    
                startV = 'Voc'
                stopV = 0.0
                dV = -1 * abs(dV)
        else:
            limitsMode = 'Manual'
            FwdCurrentLimit = Icompliance
            
            minV = float(self.fieldIVMinV.text())
            maxV = float(self.fieldIVMaxV.text())
            
            if abs(maxV) > Vcompliance:
                self.showErrorMessage("ERROR: Maximum voltage outside of compliance range")
                return
            if abs(minV) > Vcompliance:
                self.showErrorMessage("ERROR: Minimum voltage outside of compliance range")
                return
            if minV >= maxV:
                self.showErrorMessage("ERROR: Maximum voltage must be greater\nthan Minimum for J-V scan")
                return
                        
            if sweepDir == 'Forward':
                startV = minV
                stopV = maxV
                dV = abs(dV)
            else:    
                startV = maxV
                stopV = minV
                dV = -1 * abs(dV)
        
        self.showStatus("launching IV Scan")
        self.statusBar.show()
        IV_params = {}
        #IV_param = dict(light_int = 100, start_V = 'Voc', stop_V = 0, dV = 0.01, sweep_rate = 0.010, Imax = 0.010)
        if self.lightLevelModeManual :
            IV_params['light_int'] = float(self.fieldManualLightLevel.text())
        else:
            lightKey = self.menuSelectLightLevel.currentText()            
            IV_params['light_int'] = self.lightLevelDictionary[lightKey]
            
        IV_params['limits_mode'] = limitsMode
        IV_params['Fwd_current_limit'] = FwdCurrentLimit
        IV_params['start_V'] = startV
        IV_params['stop_V'] = stopV
        IV_params['dV'] = dV
        IV_params['sweep_rate'] = abs(float(self.fieldIVSweepRate.text())/1000.)
        IV_params['Dwell'] = abs(float(self.fieldIVStabilizationTime.text()))
        IV_params['Nwire'] = str(self.menu2wire4wire.currentText())
        IV_params['Imax'] = Icompliance
        IV_params['Vmax'] = Vcompliance
        
        IV_params['active_area'] = cell_active_area
        cellName = self.fieldCellName.text()
        #if cellName == "Enter Cell Name Here...":
        #    cellName = ""
        IV_params['cell_name'] = self.sanitizeCellName(cellName)
        
        #IV_params['Imax'] = 0.010
        #self.graphWidget.setLabel('left','Current (A)')
        #self.graphWidget.setLabel('bottom','Voltage (V)')
        self.runStarted()
        self.signal_runIV.emit(IV_params)
        
    def runConstantV(self):
        Vcompliance = abs(float(self.fieldVoltageLimit.text()))
        setV = float(self.fieldConstantVSetV.text())
        if abs(setV) > Vcompliance:
            self.showErrorMessage("ERROR: Requested voltage outside of compliance range")
            return
        
        self.showStatus("launching Constant Voltage Measurement")
        self.statusBar.show()
        params = {}
        #param: light_int, set_voltage, duration, interval
        
        if self.lightLevelModeManual :
            params['light_int'] = float(self.fieldManualLightLevel.text())
        else:
            lightKey = self.menuSelectLightLevel.currentText()            
            params['light_int'] = self.lightLevelDictionary[lightKey]
            
        params['set_voltage'] = float(self.fieldConstantVSetV.text())
        params['Dwell'] = float(self.fieldConstantVStabilizationTime.text())
        params['interval'] = float(self.fieldConstantVInterval.text())
        params['duration'] = float(self.fieldConstantVDuration.text())
        params['Nwire'] = str(self.menu2wire4wire.currentText())
        params['Imax'] = abs(float(self.fieldCurrentLimit.text())/1000.)
        params['Vmax'] = Vcompliance
        params['active_area'] = float(self.fieldCellActiveArea.text())
        cellName = self.fieldCellName.text()
        #if cellName == "Enter Cell Name Here...":
        #    cellName = ""
        params['cell_name'] = self.sanitizeCellName(cellName)
        
        self.runStarted()
        self.signal_runConstantV.emit(params)
    
    def runConstantI(self):
        Icompliance = abs(float(self.fieldCurrentLimit.text())/1000.)
        setI = float(self.fieldConstantISetI.text())
        if abs(setI) > Icompliance:
            self.showErrorMessage("ERROR: Requested current outside of compliance range")
            return
    
        self.showStatus("launching Constant Current Measurement")
        self.statusBar.show()
        params = {}
        #param: light_int, set_current, duration, interval
        
        if self.lightLevelModeManual :
            params['light_int'] = float(self.fieldManualLightLevel.text())
        else:
            lightKey = self.menuSelectLightLevel.currentText()            
            params['light_int'] = self.lightLevelDictionary[lightKey]
            
        params['set_current'] = float(self.fieldConstantISetI.text())/1000.
        params['Dwell'] = float(self.fieldConstantIStabilizationTime.text())
        params['interval'] = float(self.fieldConstantIInterval.text())
        params['duration'] = float(self.fieldConstantIDuration.text())
        params['Nwire'] = str(self.menu2wire4wire.currentText())
        params['Imax'] = Icompliance
        params['Vmax'] = abs(float(self.fieldVoltageLimit.text()))
        params['active_area'] = float(self.fieldCellActiveArea.text())
        cellName = self.fieldCellName.text()
        #if cellName == "Enter Cell Name Here...":
        #    cellName = ""
        params['cell_name'] = self.sanitizeCellName(cellName)
        
        self.runStarted()
        self.signal_runConstantI.emit(params)
    
    def runMaxPP(self):
        Vcompliance = abs(float(self.fieldVoltageLimit.text()))
        startV = float(self.fieldMaxPPStartV.text())
        if abs(startV) > Vcompliance:
            self.showErrorMessage("ERROR: MPP start voltage outside of compliance range")
            return
        
        self.showStatus("launching Maximum Power Point Measurement")
        self.statusBar.show()
        params = {}
        #param: light_int, start_voltage, duration, interval
        
        if self.lightLevelModeManual :
            params['light_int'] = float(self.fieldManualLightLevel.text())
        else:
            lightKey = self.menuSelectLightLevel.currentText()            
            params['light_int'] = self.lightLevelDictionary[lightKey]
            
        if self.CheckBoxAutomaticMpp.isChecked():
            params['start_voltage'] = 'auto'
        else:
            params['start_voltage'] = float(self.fieldMaxPPStartV.text())
        params['Dwell'] = float(self.fieldMaxPPStabilizationTime.text())
        params['interval'] = float(self.fieldMaxPPInterval.text())
        params['duration'] = float(self.fieldMaxPPDuration.text())
        params['Nwire'] = str(self.menu2wire4wire.currentText())
        params['Imax'] = abs(float(self.fieldCurrentLimit.text())/1000.)
        params['Vmax'] = Vcompliance
        params['active_area'] = float(self.fieldCellActiveArea.text())
        cellName = self.fieldCellName.text()
        #if cellName == "Enter Cell Name Here...":
        #    cellName = ""
        params['cell_name'] = self.sanitizeCellName(cellName)
        
        self.runStarted()
        self.signal_runMaxPP.emit(params)
    
    def runCalibration(self):
        Vcompliance = abs(float(self.fieldVoltageLimit.text()))
        setV = float(self.fieldConstantVSetV.text())
        if abs(setV) > Vcompliance:
            self.showErrorMessage("ERROR: Requested voltage outside of compliance range")
            return
        
        self.showStatus("launching Photodiode Calibration")
        self.statusBar.show()
        params = {}
        #param: light_int, set_voltage, duration, interval
        
        if self.lightLevelModeManual :
            params['light_int'] = float(self.fieldManualLightLevel.text())
        else:
            lightKey = self.menuSelectLightLevel.currentText()            
            params['light_int'] = self.lightLevelDictionary[lightKey]
            
        params['set_voltage'] = 0.0
        params['Dwell'] = float(self.fieldCalibrationStabilizationTime.text())
        params['interval'] = float(self.fieldCalibrationInterval.text())
        params['duration'] = float(self.fieldCalibrationDuration.text())
        params['reference_current'] = abs(float(self.fieldCalibrationDiodeReferenceCurrent.text())/1000.)
        params['Nwire'] = str(self.menu2wire4wire.currentText())
        params['Imax'] = abs(float(self.fieldCurrentLimit.text())/1000.)
        params['Vmax'] = Vcompliance
        params['active_area'] = float(self.fieldCellActiveArea.text())
        cellName = self.fieldCellName.text()
        #if cellName == "Enter Cell Name Here...":
        #    cellName = ""
        params['cell_name'] = self.sanitizeCellName(cellName)
        
        self.runStarted()
        self.ButtonSaveCalibration.setEnabled(True)
        self.signal_runCalibration.emit(params)
    
    def abortRun(self):
        self.showStatus("Aborting current run...")
        self.statusBar.show()
        self.signal_abortRun.emit()
        self.flag_abortRun = True
    
    def runStarted(self):
        self.menuSelectMeasurement.setEnabled(False)
        self.ButtonRunIV.setEnabled(False)
        self.ButtonAbortIV.setEnabled(True)
        self.ButtonRunConstantV.setEnabled(False)
        self.ButtonAbortConstantV.setEnabled(True)
        self.ButtonRunConstantI.setEnabled(False)
        self.ButtonAbortConstantI.setEnabled(True)
        self.ButtonRunMaxPP.setEnabled(False)
        self.ButtonAbortMaxPP.setEnabled(True)
        self.buttonSaveData.setEnabled(False)
        self.ButtonRunCalibration.setEnabled(False)
        self.ButtonAbortCalibration.setEnabled(True)
    
    def runFinished(self):
        self.menuSelectMeasurement.setEnabled(True)
        self.ButtonRunIV.setEnabled(True)
        self.ButtonAbortIV.setEnabled(False)
        self.ButtonRunConstantV.setEnabled(True)
        self.ButtonAbortConstantV.setEnabled(False)
        self.ButtonRunConstantI.setEnabled(True)
        self.ButtonAbortConstantI.setEnabled(False)
        self.ButtonRunMaxPP.setEnabled(True)
        self.ButtonAbortMaxPP.setEnabled(False)
        self.ButtonRunCalibration.setEnabled(True)
        self.ButtonAbortCalibration.setEnabled(False)
        self.buttonSaveData.setEnabled(True)
        self.flag_abortRun = False
        #self.showStatus("Run finished")
        #self.statusBar.show()
    
    def toggleAutoSaveMode(self):
        if self.checkBoxAutoSave.isChecked():
            self.signal_toggleAutoSave.emit(True)
        else:
            self.signal_toggleAutoSave.emit(False)
    
    def saveScanData(self):
        scanType = str(self.menuSelectMeasurement.currentText())
        cellName = self.fieldCellName.text()
        #if cellName == "Enter Cell Name Here...":
        #    cellName = ""
        self.signal_saveScanData.emit(scanType, cellName)
    
    def setCalibrationReferenceCurrent(self,current):
        self.fieldCalibrationReferenceCellCurrent.setText("{:5.3f}".format(current))
    
    def saveCalibration(self):
        calibration_params = {}
        calibration_params['reference_current'] = abs(float(self.fieldCalibrationReferenceCellCurrent.text())/1000.)
        self.signal_saveCalibration.emit(calibration_params)
    
    def disableCalibration(self):
        if self.menuSelectMeasurement.count() >= 5:
            self.menuSelectMeasurement.removeItem(4)
    
    def enableCalibration(self):
        if self.menuSelectMeasurement.count() < 5:
            self.menuSelectMeasurement.addItem('Calibrate Reference Diode')
    
    def updatePlotIV(self,dataX, dataY):
        if not self.curve_IV_valid:
            self.curve_IV = self.graphWidgetIV.plot(dataX,dataY,pen=pg.mkPen('r', width=2))
            self.curve_IV_valid = True
        else:
            self.curve_IV.setData(dataX,dataY) #,pen=pg.mkPen('r', width=2))
    
    def updateIVResults(self,IV_Results):
        if 'Jsc' in IV_Results:
            self.fieldJsc.setText("{:.3f}".format(IV_Results['Jsc']))
        else:
            self.fieldJsc.setText("-----")
        if 'Voc' in IV_Results:
            self.fieldVoc.setText("{:.4f}".format(IV_Results['Voc']))
        else:
            self.fieldVoc.setText("-----")
        if 'FF' in IV_Results:
            self.fieldFillFactor.setText("{:.4f}".format(IV_Results['FF']))
        else:
            self.fieldFillFactor.setText("-----")
        if 'PCE' in IV_Results:
            self.fieldPce.setText("{:.3f}".format(IV_Results['PCE']))
        else:
            self.fieldPce.setText("-----")
        if 'Jmpp' in IV_Results:
            self.fieldJmpp.setText("{:.3f}".format(IV_Results['Jmpp']))
        else:
            self.fieldJmpp.setText("-----")
        if 'Vmpp' in IV_Results:
            self.fieldVmpp.setText("{:.4f}".format(IV_Results['Vmpp']))
        else:
            self.fieldVmpp.setText("-----")
        if 'Pmpp' in IV_Results:
            self.fieldPmpp.setText("{:.3f}".format(IV_Results['Pmpp']))
        else:
            self.fieldPmpp.setText("-----") 
        if 'light_int_meas' in IV_Results:
            self.fieldLightInt.setText(f"{IV_Results['light_int_meas']:.1f}")
        else:
            self.fieldLightInt.setText("-----") 
        
    
    def updatePlotConstantV(self,dataX, dataY):
        if not self.curve_ConstantV_valid:
            self.curve_ConstantV = self.graphWidgetConstantV.plot(dataX,dataY,pen=pg.mkPen('r', width=2))
            self.curve_ConstantV_valid = True
        else:
            self.curve_ConstantV.setData(dataX,dataY) #,pen=pg.mkPen('r', width=2))
    
    def updatePlotConstantI(self,dataX, dataY):
        if not self.curve_ConstantI_valid:
            self.curve_ConstantI = self.graphWidgetConstantI.plot(dataX,dataY,pen=pg.mkPen('r', width=2))
            self.curve_ConstantI_valid = True
        else:
            self.curve_ConstantI.setData(dataX,dataY) #,pen=pg.mkPen('r', width=2))
    
    def updatePlotMPP(self,dataX, dataY):
        if not self.curve_MPP_valid:
            self.curve_MPP = self.graphWidgetMPP.plot(dataX,dataY,pen=pg.mkPen('r', width=2))
            self.curve_MPP_valid = True
        else:
            self.curve_MPP.setData(dataX,dataY) #,pen=pg.mkPen('r', width=2))
    
    def updatePlotMPPIV(self,dataX, dataV, dataI):
        self.curveMPPV.setData(dataX,dataV) #,pen=pg.mkPen('r', width=2))
        self.curveMPPI.setData(dataX,dataI) #,pen=pg.mkPen('b', width=2))
        self.viewBoxMPPI.setGeometry(self.plotItemMPPIV.vb.sceneBoundingRect())
    
    def updatePlotCalibration(self, dataXMeas, dataMeas, dataXRef, dataRef):
        self.curveCalibrationMeas.setData(dataXMeas,dataMeas) #,pen=pg.mkPen('r', width=2))
        self.curveCalibrationRef.setData(dataXRef,dataRef) #,pen=pg.mkPen('b', width=2))
        self.viewBoxCalibrationRef.setGeometry(self.plotItemCalibration.vb.sceneBoundingRect())
    
    def updateViewsMPPIV(self):
        self.viewBoxMPPI.setGeometry(self.plotItemMPPIV.vb.sceneBoundingRect())
    
    def updateViewsCalibration(self):
        self.viewBoxCalibrationRef.setGeometry(self.plotItemCalibration.vb.sceneBoundingRect())
    
    def clearPlotIV(self):
        self.graphWidgetIV.clear()
        self.curve_IV_valid = False
    
    def clearPlotConstantV(self):
        self.graphWidgetConstantV.clear()
        self.curve_ConstantV_valid = False
    
    def clearPlotConstantI(self):
        self.graphWidgetConstantI.clear()
        self.curve_ConstantI_valid = False
    
    def clearPlotMPP(self):
        self.graphWidgetMPP.clear()
        self.curve_MPP_valid = False
    
    def clearPlotMPPIV(self):
        self.curveMPPV.setData(x=[], y=[])
        self.curveMPPI.setData(x=[], y=[])
    
    def clearPlotCalibration(self):
        self.curveCalibrationMeas.setData(x=[], y=[])
        self.curveCalibrationRef.setData(x=[], y=[])
        
    def loadSettingsFile(self, settingsFilePath ='NULL'):
        # grab settings file name from field.
        if settingsFilePath == 'NULL' :
            settingsFilePath = self.FieldSettingsFile.text()
        if(os.path.exists(settingsFilePath)):
            try:
                with open(settingsFilePath) as json_file:
                    settings = json.load(json_file)
                    # loop over all text edit fields and load the settings
                    for name in self.UIFields :
                        if (name in settings): self.UIFields[name].setText((settings[name]))
                    # loop over all drop-down menus (QComboBox) and load the value selected
                    # look up the index by name.  If it is not found, load index zero
                    # note that the callback functions are automatically called when the values are set
                    for name in self.UIDropDowns:
                        if (name in settings):
                            DropDownIndex = self.UIDropDowns[name].findText(settings[name])
                            if DropDownIndex < 0: DropDownIndex = 0
                            self.UIDropDowns[name].setCurrentIndex(DropDownIndex)
                    if('IVMaxVUser' in settings):
                        self.IVMaxVUser = settings['IVMaxVUser']
                    if('IVFwdLimitUser' in settings):
                        self.IVFwdLimitUser = settings['IVFwdLimitUser']
                    if ('CheckBoxAutomaticLimits' in settings):
                        self.CheckBoxAutomaticLimits.setChecked(settings['CheckBoxAutomaticLimits'])
                        self.toggleIVLimitsMode()
                    if ('CheckBoxAutoSave' in settings):
                        self.checkBoxAutoSave.setChecked(settings['CheckBoxAutoSave'])
                        self.toggleAutoSaveMode()
                    if ('CheckBoxAutomaticMpp' in settings):
                        self.CheckBoxAutomaticMpp.setChecked(settings['CheckBoxAutomaticMpp'])
                        self.toggleMppStartMode()
                    
            except:
                self.showErrorMessage("Error: Config file not properly formatted.\nLoading default parameters.")
                self.setAllFieldsToDefault()
        else:
            #self.showErrorMessage("Error: Config File does not exist")
            # no settings file - set default parameters
            self.setAllFieldsToDefault()
            
    def setAllFieldsToDefault(self):
        self.CheckBoxAutomaticLimits.setChecked(False)
        self.toggleIVLimitsMode()
        self.checkBoxAutoSave.setChecked(False)
        self.toggleAutoSaveMode()
        self.CheckBoxAutomaticMpp.setChecked(False)
        self.toggleMppStartMode()
        self.fieldIVMinV.setText('0.00')
        self.IVMaxVUser = 1.2
        self.IVFwdLimitUser = 0.0
        self.fieldIVMaxV.setText(str(self.IVMaxVUser))
        self.fieldIVVStep.setText('5.0')
        self.fieldIVSweepRate.setText('20.0')
        self.fieldIVStabilizationTime.setText('5.0')
        self.menuIVSweepDirection.setCurrentIndex(1)
        self.fieldConstantVSetV.setText('0.00')
        self.fieldConstantVStabilizationTime.setText('5.0')
        self.fieldConstantVInterval.setText('0.50')
        self.fieldConstantVDuration.setText('60.0')
        self.fieldConstantISetI.setText('0.00')
        self.fieldConstantIStabilizationTime.setText('5.0')
        self.fieldConstantIInterval.setText('0.50')
        self.fieldConstantIDuration.setText('60.0')
        self.fieldMaxPPStartV.setText('1.00')
        self.fieldMaxPPStabilizationTime.setText('5.0')
        self.fieldMaxPPInterval.setText('0.50')
        self.fieldMaxPPDuration.setText('60.0')
        self.fieldCellActiveArea.setText('0.16')
        self.menu2wire4wire.setCurrentIndex(0)
        self.fieldVoltageLimit.setText('2.00')
        self.fieldCurrentLimit.setText('5.0')
        self.menuSelectLightLevel.setCurrentIndex(0)
        self.menuSelectMeasurement.setCurrentIndex(0)
        results = {}
        self.updateIVResults(results)
        self.fieldCellName.setText("")
        #ugly hack to get around cursorPositionChanged event...
        #this event is not called when deleting a character, so write our default string
        #with a dot at the start, move the cursor to the start, and delete
        #otherwise if we put this string in directly the cursorPositionChanged callback
        #is activated and our default string is deleted.
        #self.fieldCellName.setText(".Enter Cell Name Here...")
        #self.fieldCellName.setCursorPosition(0)
        #self.fieldCellName.del_()
        self.ButtonSaveCalibration.setEnabled(False)
        self.fieldCalibrationReferenceCellCurrent.setText('1.00')
        self.fieldCalibrationStabilizationTime.setText('5.0')
        self.fieldCalibrationInterval.setText('0.5')
        self.fieldCalibrationDuration.setText('60.0')
            
    def saveSettingsFile(self, settingsFilePath ='NULL'):
        # create dict that contains all settings
        settings = {}
        for name in self.UIFields:
            settings[name] = self.UIFields[name].text()
        for name in self.UIDropDowns:
            settings[name] = self.UIDropDowns[name].currentText()
        settings["CheckBoxAutomaticLimits"] = self.CheckBoxAutomaticLimits.isChecked()
        settings["CheckBoxAutoSave"] = self.checkBoxAutoSave.isChecked()
        settings["CheckBoxAutomaticMpp"] = self.CheckBoxAutomaticMpp.isChecked()
        settings["IVMaxVUser"] = self.IVMaxVUser
        settings["IVFwdLimitUser"] = self.IVFwdLimitUser
        
        try:
            basePath, filename = os.path.split(settingsFilePath)
            if (not os.path.exists(basePath)):
                os.makedirs(basePath)
            with open(settingsFilePath, 'w') as outfile:
                json.dump(settings, outfile)
        except Exception as err:
            print(err)
            self.showErrorMessage("ERROR: Could not create settings file " + settingsFilePath)
    
    def sanitizeCellName(self, value, allow_unicode=False):
        """
        Taken from https://github.com/django/django/blob/master/django/utils/text.py
        Convert to ASCII if 'allow_unicode' is False. Convert spaces or repeated
        dashes to single dashes. Remove characters that aren't alphanumerics,
        underscores, or hyphens. Convert to lowercase. Also strip leading and
        trailing whitespace, dashes, and underscores.
        """
        value = str(value)
        if allow_unicode:
            value = unicodedata.normalize('NFKC', value)
        else:
            value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
        value = re.sub(r'[^\w\s-]', '', value.lower())
        sanitized_name = re.sub(r'[-\s]+', '-', value).strip('-_')
        if len(sanitized_name) > 64:
            sanitized_name = sanitized_name[0:63]
        return sanitized_name
    
    def showErrorMessage(self,message):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Critical)
        msg.setText(message)
        msg.setInformativeText('')
        msg.setWindowTitle("Error")
        msg.exec_()
    
    def showStatus(self,message):
        self.statusBar.showMessage(message)
    
if __name__ == "__main__":

    class myApp:

        flag_abortRun = False

        def runIVLocal(self):
            print("running local IV Scan\n")
            #win.clearPlot()
            self.dataX = []
            self.dataY = []
            for x in np.linspace(0,100,1000 + 1):
                
                self.dataX.append(x)
                self.dataY.append(x*x)
                
                win.updatePlot(self.dataX,self.dataY)
                print("X: " + str(x))
                QApplication.processEvents()
                
                if self.flag_abortRun: 
                    break
            
            win.runFinished()
            self.flag_abortRun = False
            #self.graphWidget.setXRange(0,10)
            
        def abortRunLocal(self):
            print("executing abortRunLocal")
            self.flag_abortRun = True

    app = QApplication(sys.argv)
    myap = myApp()
    win = Window()
    win.signal_runIV.connect(myap.runIVLocal)
    win.signal_abortRun.connect(myap.abortRunLocal)
    win.show()
    sys.exit(app.exec())