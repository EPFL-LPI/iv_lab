from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QDoubleValidator

from PyQt6.QtWidgets import (
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


class ChronopotentiometryParametersWidget(MeasurementParametersWidget):
    """
    Measurement parameters for a chronopotentiometry measurement.
    """

    def __init__(self):
        super().__init__()

        self.setMaximumWidth(300)

    def init_params_ui(self, lo_main: QVBoxLayout):
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
        
        # ConstantI panel layout
        lo_params = QGridLayout()
        lo_params.addWidget(self.labelConstantISetI,0,0)
        lo_params.addWidget(self.fieldConstantISetI,0,1)
        lo_params.addWidget(self.labelMilliAmps,0,2)

        lo_params.addWidget(self.labelConstantIStabilizationTime,1,0)
        lo_params.addWidget(self.fieldConstantIStabilizationTime,1,1)
        lo_params.addWidget(self.labelConstantIStabilizationTimeUnits,1,2)

        lo_params.addWidget(self.labelConstantIInterval,2,0)
        lo_params.addWidget(self.fieldConstantIInterval,2,1)
        lo_params.addWidget(self.labelSeconds2,2,2)

        lo_params.addWidget(self.labelConstantIDuration,3,0)
        lo_params.addWidget(self.fieldConstantIDuration,3,1)
        lo_params.addWidget(self.labelSeconds3,3,2)
        
        lo_main.addLayout(lo_params)
