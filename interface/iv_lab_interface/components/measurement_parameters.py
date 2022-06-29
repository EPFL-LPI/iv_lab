from PyQt5.QtGui import QDoubleValidator

from PyQt5.QtWidgets import (
    QStackedWidget,
    QLabel,
    QLineEdit,
    QHBoxLayout,
    QVBoxLayout,
    QPushButton,
    QWidget,
    QGroupBox,
    QCheckBox,
    QComboBox,
    QGridLayout
)

class MeasurementGroupBox(QGroupBox):
    def __init__(self):
        super().__init__("Measurement")

        self.init_ui()

    def init_ui(self):

        #measurement group box
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
        self.setLayout(measurementGroupBoxLayout)
        self.setEnabled(False)
        self.setMaximumWidth(300)


    def selectMeasurement(self,i):
        self.measurementStack.setCurrentIndex(i)
        self.StackGraphPanels.setCurrentIndex(i)

    def toggleIVLimitsMode(self):
        if self.CheckBoxAutomaticLimits.isChecked():
            self.fieldIVMinV.setEnabled(False)
            #self.fieldIVMaxV.setEnabled(False)
            self.fieldIVMaxV.setText(str(self.IVFwdLimitUser))
            self.labelIVMaxV.setText("Fwd Current Limit")
            self.labelIVMaxVUnits.setText("mA/cm^2")
        else:
            self.fieldIVMinV.setEnabled(True)
            #self.fieldIVMaxV.setEnabled(True)
            self.fieldIVMaxV.setText(str(self.IVMaxVUser))
            self.labelIVMaxV.setText("Maximum Voltage")
            self.labelIVMaxVUnits.setText("V")
    
    def IVMaxVTextChanged(self):
        if self.CheckBoxAutomaticLimits.isChecked():
            self.IVFwdLimitUser = float(self.fieldIVMaxV.text())
        else:
            self.IVMaxVUser = float(self.fieldIVMaxV.text())
    

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
        IV_params['Imax'] = Icompliance
        IV_params['Vmax'] = Vcompliance
        
        IV_params['active_area'] = cell_active_area
        cellName = self.fieldCellName.text()
        if cellName == "Enter Cell Name Here...":
            cellName = ""
        IV_params['cell_name'] = self.sanitizeCellName(cellName)
        
        #IV_params['Imax'] = 0.010
        #self.graphWidget.setLabel('left','Current (A)')
        #self.graphWidget.setLabel('bottom','Voltage (V)')
        self.runStarted()
        self.signal_runIV.emit(IV_params)

    def abortRun(self):
        self.showStatus("Aborting current run...")
        self.statusBar.show()
        self.signal_abortRun.emit()
        self.flag_abortRun = True


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
        params['Imax'] = abs(float(self.fieldCurrentLimit.text())/1000.)
        params['Vmax'] = Vcompliance
        params['active_area'] = float(self.fieldCellActiveArea.text())
        cellName = self.fieldCellName.text()
        if cellName == "Enter Cell Name Here...":
            cellName = ""
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
        params['Imax'] = Icompliance
        params['Vmax'] = abs(float(self.fieldVoltageLimit.text()))
        params['active_area'] = float(self.fieldCellActiveArea.text())
        cellName = self.fieldCellName.text()
        if cellName == "Enter Cell Name Here...":
            cellName = ""
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
        params['Imax'] = abs(float(self.fieldCurrentLimit.text())/1000.)
        params['Vmax'] = Vcompliance
        params['active_area'] = float(self.fieldCellActiveArea.text())
        cellName = self.fieldCellName.text()
        if cellName == "Enter Cell Name Here...":
            cellName = ""
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
        params['Imax'] = abs(float(self.fieldCurrentLimit.text())/1000.)
        params['Vmax'] = Vcompliance
        params['active_area'] = float(self.fieldCellActiveArea.text())
        cellName = self.fieldCellName.text()
        if cellName == "Enter Cell Name Here...":
            cellName = ""
        params['cell_name'] = self.sanitizeCellName(cellName)
        
        self.runStarted()
        self.ButtonSaveCalibration.setEnabled(True)
        self.signal_runCalibration.emit(params)

    def toggleMppStartMode(self):
        if self.CheckBoxAutomaticMpp.isChecked():
            self.fieldMaxPPStartV.setEnabled(False)
        else:
            self.fieldMaxPPStartV.setEnabled(True)
    
    def saveCalibration(self):
        calibration_params = {}
        calibration_params['reference_current'] = abs(float(self.fieldCalibrationReferenceCellCurrent.text())/1000.)
        self.signal_saveCalibration.emit(calibration_params)
    