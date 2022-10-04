from PyQt6.QtWidgets import (
    QLabel,
    QVBoxLayout,
    QPushButton,
    QDoubleSpinBox,
    QGridLayout
)
from pymeasure.experiment.parameters import FloatParameter

from iv_lab_controller.measurements.calibration_parameters import CalibrationParameters

from .parameters_widget import MeasurementParametersWidget


class CalibrationParametersWidget(MeasurementParametersWidget):
    """
    Measurement parameters for calibration.
    """

    def __init__(self):
        super().__init__()

        self.setMaximumWidth(300)

    def init_params_ui(self, lo_main: QVBoxLayout):
        # reference current
        self.lbl_calibration_current = QLabel("Calibration Diode Iref")
        self.lbl_calibration_current_units = QLabel("mA")
        self.sb_calibration_current = QDoubleSpinBox()
        self.sb_calibration_current.setDecimals(2)
        self.sb_calibration_current.setSingleStep(0.01)
        self.sb_calibration_current.setMinimum(0)

        # stabilization time
        self.lbl_stabilization_time = QLabel("Stabilization Time")
        self.lbl_stabilization_time_units = QLabel("sec")
        self.sb_stabilization_time = QDoubleSpinBox()
        self.sb_stabilization_time.setDecimals(2)
        self.sb_stabilization_time.setSingleStep(0.01)
        self.sb_stabilization_time.setMinimum(0)

        # interval
        self.lbl_interval = QLabel("Meas Interval")
        self.lbl_interval_units = QLabel("sec")
        self.sb_interval = QDoubleSpinBox()
        self.sb_interval.setDecimals(2)
        self.sb_interval.setSingleStep(0.01)
        self.sb_interval.setMinimum(0)


        # duration
        self.lbl_duration = QLabel("Meas Duration")
        self.lbl_duration_units = QLabel("sec")
        self.sb_duration = QDoubleSpinBox()
        self.sb_duration.setDecimals(2)
        self.sb_duration.setSingleStep(0.01)
        self.sb_duration.setMinimum(0)

        # reference current
        self.lbl_ref_current = QLabel("Reference Diode Iref")
        self.lbl_ref_current_units = QLabel("mA")
        self.sb_ref_current = QDoubleSpinBox()
        self.sb_ref_current.setDecimals(2)
        self.sb_ref_current.setSingleStep(0.01)
        self.sb_ref_current.setMinimum(0)


        # layout
        lo_diode = QGridLayout()
        lo_diode.addWidget(self.lbl_ref_current, 0, 0)
        lo_diode.addWidget(self.sb_ref_current, 0, 1)
        lo_diode.addWidget(self.lbl_ref_current_units, 0, 2)
        
        self.btn_save = QPushButton("Save Calibration", self)
        self.btn_save.clicked.connect(self.saveCalibration)
        self.btn_save.setEnabled(False)
        
        # Calibration panel layout
        lo_params = QGridLayout()
        lo_params.addWidget(self.lbl_calibration_current, 0, 0)
        lo_params.addWidget(self.sb_calibration_current, 0, 1)
        lo_params.addWidget(self.lbl_calibration_current_units, 0, 2)

        lo_params.addWidget(self.lbl_stabilization_time, 1, 0)
        lo_params.addWidget(self.sb_stabilization_time, 1, 1)
        lo_params.addWidget(self.lbl_stabilization_time_units, 1, 2)

        lo_params.addWidget(self.lbl_interval, 2, 0)
        lo_params.addWidget(self.sb_interval, 2, 1)
        lo_params.addWidget(self.lbl_interval_units, 2, 2)

        lo_params.addWidget(self.lbl_duration, 3, 0)
        lo_params.addWidget(self.sb_duration, 3, 1)
        lo_params.addWidget(self.lbl_duration_units, 3, 2)
        
        lo_main.addLayout(lo_params)
        lo_main.addWidget(self.lbl_ref_current)
        lo_main.addLayout(lo_diode)
        lo_main.addWidget(self.btn_save)

        self.reset_fields()
    
    def reset_fields(self):
        """
        Reset field values to default.
        """
        self.sb_calibration_current.setValue(1)
        self.sb_stabilization_time.setValue(5)
        self.sb_interval.setValue(0.5)
        self.sb_ref_current.setValue(1)

    @property
    def value(self) -> CalibrationParameters:
        params = CalibrationParameters()
        params.reference_current = abs(self.sb_ref_current.value())* 1e-3

        return params


