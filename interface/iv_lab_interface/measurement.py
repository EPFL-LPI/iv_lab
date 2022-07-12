from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import (
    QVBoxLayout,
    QPushButton,
    QWidget
)

from iv_lab_controller.user import User, Permissions

from .base_classes.UiToggle import UiToggleInterface
from .components.light_level import LightLevelGroupBox
from .components.measurement_parameters import MeasurementGroupBox
from .components.cell_size import CellSizeWidget
from .components.compliance import ComplianceGroupBox


class MeasurementFrame(QWidget, UiToggleInterface):
    initialize_hardware = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.init_ui()
        self.register_connections()

        self._hardware_initialized = False

    @property
    def hardware_is_initialized(self):
        return self._hardware_initialized
    
    def init_ui(self):
        # init button
        self.buttonInitialize = QPushButton("Initialize Hardware",self)
        self.buttonInitialize.setMaximumWidth(300)
        self.buttonInitialize.setEnabled(False)
        
        self.lightLevelGroupBox = LightLevelGroupBox()
        self.measurementGroupBox = MeasurementGroupBox()
        self.cellSizeWidget = CellSizeWidget()
        self.complianceGroupBox = ComplianceGroupBox()
        self.buttonResetToDefault = QPushButton("Reset All Settings To Default", self)
        self.buttonResetToDefault.setEnabled(False)
        
        # Set the measurement frame layout
        measurementLayout = QVBoxLayout()
        measurementLayout.addWidget(self.buttonInitialize)
        measurementLayout.addStretch(1)
        measurementLayout.addWidget(self.lightLevelGroupBox)
        measurementLayout.addStretch(1)
        measurementLayout.addWidget(self.measurementGroupBox)
        measurementLayout.addStretch(1)
        measurementLayout.addWidget(self.cellSizeWidget)
        measurementLayout.addStretch(1)
        measurementLayout.addWidget(self.complianceGroupBox)
        measurementLayout.addStretch(1)
        measurementLayout.addWidget(self.buttonResetToDefault)
        
        self.setLayout(measurementLayout)  
    
    def register_connections(self):
        self.buttonInitialize.clicked.connect(self.initialize_hardware.emit)
        self.buttonResetToDefault.clicked.connect(self.setAllFieldsToDefault)

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
        self.fieldVoltageLimit.setText('2.00')
        self.fieldCurrentLimit.setText('5.0')
        self.menuSelectLightLevel.setCurrentIndex(0)
        self.menuSelectMeasurement.setCurrentIndex(0)
        results = {}
        self.updateIVResults(results)
        #ugly hack to get around cursorPositionChanged event...
        #this event is not called when deleting a character, so write our default string
        #with a dot at the start, move the cursor to the start, and delete
        #otherwise if we put this string in directly the cursorPositionChanged callback
        #is activated and our default string is deleted.
        self.fieldCellName.setText(".Enter Cell Name Here...")
        self.fieldCellName.setCursorPosition(0)
        self.fieldCellName.del_()
        self.ButtonSaveCalibration.setEnabled(False)
        self.fieldCalibrationReferenceCellCurrent.setText('1.00')
        self.fieldCalibrationStabilizationTime.setText('5.0')
        self.fieldCalibrationInterval.setText('0.5')
        self.fieldCalibrationDuration.setText('60.0')

    def toggle_ui(self, enable: bool = True):
        """
        Enable or disable UI elements.

        :param enable: Whether to enable or disable elements.
            [Default: True]
        """
        if enable:
            self.enable_ui()

        else:
            self.disable_ui()

    def enable_ui(self):
        self.buttonInitialize.setEnabled(True)

    def disable_ui(self):
        self.buttonInitialize.setEnabled(False)