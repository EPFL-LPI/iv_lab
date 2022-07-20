from PyQt5.QtCore import pyqtSignal
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

from .parameters_widget import MeasurementParametersWidget


class MPPParametersWidget(MeasurementParametersWidget):
    """
    Measurement parameters for an MPP experiment.
    """

    def __init__(self):
        super().__init__()

        self.setMaximumWidth(300)

    def init_params_ui(self, lo_main: QVBoxLayout):
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
        
        # MaxPP panel layout
        lo_params = QGridLayout()
        lo_params.addWidget(self.labelMaxPPStartV,0,0)
        lo_params.addWidget(self.fieldMaxPPStartV,0,1)
        lo_params.addWidget(self.labelVolts4,0,2)
        lo_params.addWidget(self.labelMaxPPStabilizationTime,1,0)
        lo_params.addWidget(self.fieldMaxPPStabilizationTime,1,1)
        lo_params.addWidget(self.labelMaxPPStabilizationTimeUnits,1,2)
        lo_params.addWidget(self.labelMaxPPInterval,2,0)
        lo_params.addWidget(self.fieldMaxPPInterval,2,1)
        lo_params.addWidget(self.labelSeconds4,2,2)
        lo_params.addWidget(self.labelMaxPPDuration,3,0)
        lo_params.addWidget(self.fieldMaxPPDuration,3,1)
        lo_params.addWidget(self.labelSeconds5,3,2)
        
        lo_main.addWidget(self.CheckBoxAutomaticMpp)
        lo_main.addLayout(lo_params)

    def toggleMppStartMode(self):
        if self.CheckBoxAutomaticMpp.isChecked():
            self.fieldMaxPPStartV.setEnabled(False)
        else:
            self.fieldMaxPPStartV.setEnabled(True)