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


class ChronoamperometryParametersWidget(MeasurementParametersWidget):
    """
    Measurement parameters for a chronoamperometry experiment.
    """

    def __init__(self):
        super().__init__()

        self.setMaximumWidth(300)

    def init_params_ui(self, lo_main: QVBoxLayout):
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
        
        # ConstantV panel layout
        lo_params = QGridLayout()
        lo_params.addWidget(self.labelConstantVSetV,0,0)
        lo_params.addWidget(self.fieldConstantVSetV,0,1)
        lo_params.addWidget(self.labelVolts3,0,2)

        lo_params.addWidget(self.labelConstantVStabilizationTime,1,0)
        lo_params.addWidget(self.fieldConstantVStabilizationTime,1,1)
        lo_params.addWidget(self.labelConstantVStabilizationTimeUnits,1,2)

        lo_params.addWidget(self.labelConstantVInterval,2,0)
        lo_params.addWidget(self.fieldConstantVInterval,2,1)
        lo_params.addWidget(self.labelSeconds,2,2)

        lo_params.addWidget(self.labelConstantVDuration,3,0)
        lo_params.addWidget(self.fieldConstantVDuration,3,1)
        lo_params.addWidget(self.labelSeconds1,3,2)
        
        lo_main.addLayout(lo_params)