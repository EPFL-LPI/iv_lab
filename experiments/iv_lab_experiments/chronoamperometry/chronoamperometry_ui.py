from PyQt6.QtWidgets import (
    QLabel,
    QDoubleSpinBox,
    QVBoxLayout,
    QGridLayout
)

from iv_lab_cvontroller.base_classes.parameters_widget import MeasurementParametersWidget

from .chronoamperometry_parameters import ChronoamperometryParameters


class ChronoamperometryParametersWidget(MeasurementParametersWidget):
    """
    Measurement parameters for a chronoamperometry experiment.
    """

    def __init__(self):
        super().__init__()

        self.setMaximumWidth(300)

    def init_params_ui(self, lo_main: QVBoxLayout):
        self.user_voltage_limit = 1.2

        # set voltage
        self.lbl_set_voltage = QLabel("Set Voltage")
        self.lbl_set_voltage_units = QLabel("V")
        self.sb_set_voltage = QDoubleSpinBox()
        self.sb_set_voltage.setDecimals(2)
        self.sb_set_voltage.setSingleStep(0.1)
        self.sb_set_voltage.setMinimum(-self.user_voltage_limit)
        self.sb_set_voltage.setMaximum(self.user_voltage_limit)

        # settling time
        self.lbl_settling_time = QLabel("Stabilization Time")
        self.lbl_settling_time_units = QLabel("sec")
        self.sb_settling_time = QDoubleSpinBox()
        self.sb_settling_time.setDecimals(1)
        self.sb_settling_time.setSingleStep(0.1)
        self.sb_settling_time.setMinimum(0)

        # measurement interval
        self.lbl_interval = QLabel("Meas Interval")
        self.lbl_interval_untis = QLabel("sec")
        self.sb_interval = QDoubleSpinBox()
        self.sb_interval.setDecimals(1)
        self.sb_interval.setSingleStep(0.1)
        self.sb_interval.setMinimum(0)

        # duration
        self.lbl_duration = QLabel("Meas Duration")
        self.lbl_duration_units = QLabel("sec")
        self.sb_duration = QDoubleSpinBox()
        self.sb_duration.setDecimals(1)
        self.sb_duration.setSingleStep(0.1)
        self.sb_duration.setMinimum(0)
        
        # layout
        lo_params = QGridLayout()
        lo_params.addWidget(self.lbl_set_voltage, 0, 0)
        lo_params.addWidget(self.sb_set_voltage, 0, 1)
        lo_params.addWidget(self.lbl_set_voltage_units, 0, 2)

        lo_params.addWidget(self.lbl_settling_time, 1, 0)
        lo_params.addWidget(self.sb_settling_time, 1, 1)
        lo_params.addWidget(self.lbl_settling_time_units, 1, 2)

        lo_params.addWidget(self.lbl_interval, 2, 0)
        lo_params.addWidget(self.sb_interval, 2, 1)
        lo_params.addWidget(self.lbl_interval_untis, 2, 2)

        lo_params.addWidget(self.lbl_duration, 3, 0)
        lo_params.addWidget(self.sb_duration, 3, 1)
        lo_params.addWidget(self.lbl_duration_units, 3, 2)
        
        lo_main.addLayout(lo_params)

        self.reset_fields()

    @property
    def value(self) -> ChronoamperometryParameters:
        """
        :returns: Value of the measurement parameters.
        """
        params = ChronoamperometryParameters()
        params.set_voltage = self.sb_set_voltage.value()
        params.settling_time = self.sb_settling_time.value()
        params.interval = self.sb_interval.value()
        params.duration = self.sb_duraiton.value()

        return params

    def reset_fields(self):
        """
        Reset field values to default.
        """
        self.sb_set_voltage.setValue(0)
        self.sb_settling_time.setValue(5)
        self.sb_interval.setValue(0.1)
        self.sb_duration.setValue(10)
