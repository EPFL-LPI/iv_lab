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


class CalibrationParametersWidget(MeasurementParametersWidget):
    """
    Measurement parameters for calibration.
    """

    def __init__(self):
        super().__init__()

        self.setMaximumWidth(300)

    def init_params_ui(self, lo_main: QVBoxLayout):
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

        
        self.labelCalibrationReferenceCellCurrent = QLabel("Reference Diode Iref")
        self.fieldCalibrationReferenceCellCurrent = QLineEdit("1.00")
        self.CalibrationReferenceCellCurrentValidator = QDoubleValidator()
        self.fieldCalibrationReferenceCellCurrent.setValidator(self.CalibrationReferenceCellCurrentValidator)
        self.labelCalibrationReferenceCellCurrentUnits = QLabel("mA")

        lo_diode = QGridLayout()
        lo_diode.addWidget(self.labelCalibrationReferenceCellCurrent,0,0)
        lo_diode.addWidget(self.fieldCalibrationReferenceCellCurrent,0,1)
        lo_diode.addWidget(self.labelCalibrationReferenceCellCurrentUnits,0,2)
        
        self.ButtonSaveCalibration = QPushButton("Save Calibration", self)
        self.ButtonSaveCalibration.clicked.connect(self.saveCalibration)
        self.ButtonSaveCalibration.setEnabled(False)
        
        # Calibration panel layout
        lo_params = QGridLayout()
        lo_params.addWidget(self.labelCalibrationDiodeReferenceCurrent,0,0)
        lo_params.addWidget(self.fieldCalibrationDiodeReferenceCurrent,0,1)
        lo_params.addWidget(self.labelCalibrationDiodeReferenceCurrentUnits,0,2)

        lo_params.addWidget(self.labelCalibrationStabilizationTime,1,0)
        lo_params.addWidget(self.fieldCalibrationStabilizationTime,1,1)
        lo_params.addWidget(self.labelCalibrationStabilizationTimeUnits,1,2)

        lo_params.addWidget(self.labelCalibrationInterval,2,0)
        lo_params.addWidget(self.fieldCalibrationInterval,2,1)
        lo_params.addWidget(self.labelSeconds4,2,2)

        lo_params.addWidget(self.labelCalibrationDuration,3,0)
        lo_params.addWidget(self.fieldCalibrationDuration,3,1)
        lo_params.addWidget(self.labelSeconds5,3,2)
        
        lo_main.addLayout(lo_params)
        lo_main.addWidget(self.labelCalibrationReferenceCellCurrent)
        lo_main.addLayout(lo_diode)
        lo_main.addWidget(self.ButtonSaveCalibration)

    def saveCalibration(self):
        calibration_params = {}
        calibration_params['reference_current'] = abs(float(self.fieldCalibrationReferenceCellCurrent.text())/1000.)
        self.signal_saveCalibration.emit(calibration_params)
    