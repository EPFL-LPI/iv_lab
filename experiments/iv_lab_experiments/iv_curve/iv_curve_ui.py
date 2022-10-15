from PyQt6.QtWidgets import (
    QLabel,
    QDoubleSpinBox,
    QVBoxLayout,
    QCheckBox,
    QComboBox,
    QGridLayout
)

from .iv_curve_parameters import IVCurveParameters

from iv_lab_controller.base_classes import ExperimentParametersWidget
from iv_lab_controller.parameters.types import SweepDirection


class IVCurveParametersWidget(ExperimentParametersWidget):
    """
    Measurement parameters for an IV curve.
    """
    user_current_limit = 0
    user_voltage_limit = 1.2

    def __init__(self):
        super().__init__()

        self.setMaximumWidth(300)

    def init_params_ui(self, lo_main: QVBoxLayout):
        """
        Initialize parameters UI.
        """
        self.sb_auto_limits = QCheckBox("Use Automatic Limits (0 - Fwd Limit)")
        self.sb_auto_limits.stateChanged.connect(self.toggle_limit_mode)

        lbl_min_voltage = QLabel("Minimum Voltage")
        self.sb_min_voltage = QDoubleSpinBox()
        self.sb_min_voltage.setDecimals(2)
        self.sb_min_voltage.setSingleStep(0.01)
        self.sb_min_voltage.setMinimum(0)
        self.sb_min_voltage.setMinimum(-self.user_voltage_limit)
        self.sb_min_voltage.setMaximum(self.user_voltage_limit)

        self.lbl_max_voltage = QLabel("Maximum Voltage")
        self.lbl_max_voltage_units = QLabel("V")
        self.sb_max_voltage = QDoubleSpinBox()
        self.sb_min_voltage.setDecimals(2)
        self.sb_min_voltage.setSingleStep(0.01)
        self.sb_max_voltage.setMinimum(0)
        self.sb_max_voltage.setMaximum(self.user_voltage_limit)
        self.sb_max_voltage.valueChanged.connect(self.max_voltage_changed)

        lbl_voltage_step = QLabel("Voltage Step")
        self.sb_voltage_step = QDoubleSpinBox()
        self.sb_voltage_step.setDecimals(2)
        self.sb_voltage_step.setSingleStep(1)
        self.sb_voltage_step.setMinimum(0)
        self.sb_voltage_step.setMaximum(self.user_voltage_limit* 1000)

        lbl_sweep_rate = QLabel("Sweep Rate")
        self.sb_sweep_rate = QDoubleSpinBox()
        self.sb_sweep_rate.setDecimals(2)
        self.sb_sweep_rate.setSingleStep(1)
        self.sb_sweep_rate.setMinimum(0)

        lbl_stabilization_time = QLabel("Stabilization Time")
        self.sb_settling_time = QDoubleSpinBox()
        self.sb_settling_time.setDecimals(2)
        self.sb_settling_time.setSingleStep(5)
        self.sb_settling_time.setMinimum(0)

        lbl_sweep_direction = QLabel("Sweep Direction")
        self.cb_sweep_direction = QComboBox()
        for direction in ["Forward", "Reverse"]:
            self.cb_sweep_direction.addItem(direction)

        # JV panel layout
        lo_params = QGridLayout()
        lo_params.addWidget(lbl_min_voltage, 0, 0)
        lo_params.addWidget(self.sb_min_voltage, 0, 1)
        lo_params.addWidget(QLabel("V"), 0, 2)

        lo_params.addWidget(self.lbl_max_voltage, 1, 0)
        lo_params.addWidget(self.sb_max_voltage, 1, 1)
        lo_params.addWidget(self.lbl_max_voltage_units, 1, 2)

        lo_params.addWidget(lbl_voltage_step, 2, 0)
        lo_params.addWidget(self.sb_voltage_step, 2, 1)
        lo_params.addWidget(QLabel("mV"), 2, 2)

        lo_params.addWidget(lbl_sweep_rate, 3, 0)
        lo_params.addWidget(self.sb_sweep_rate, 3, 1)
        lo_params.addWidget(QLabel("mV/s"), 3, 2)

        lo_params.addWidget(lbl_stabilization_time, 4, 0)
        lo_params.addWidget(self.sb_settling_time, 4, 1)
        lo_params.addWidget(QLabel("sec"), 4, 2)

        lo_params.addWidget(lbl_sweep_direction, 5, 0)
        lo_params.addWidget(self.cb_sweep_direction, 5, 1)
        
        lo_main.addWidget(self.sb_auto_limits)
        lo_main.addLayout(lo_params)

        self.reset_fields()

    def toggle_limit_mode(self, enabled: bool):
        """

        """
        self.sb_min_voltage.setEnabled(not enabled)
        
        if enabled:
            # self.fieldIVMaxV.setEnabled(False)
            self.lbl_max_voltage.setText("Current Limit")
            self.lbl_max_voltage_units.setText("mA/cm^2")
            self.sb_max_voltage.setValue(self.user_current_limit)

        else:
            # self.fieldIVMaxV.setEnabled(True)
            self.lbl_max_voltage.setText("Maximum Voltage")
            self.lbl_max_voltage_units.setText("V")
            self.sb_max_voltage.setValue(self.user_voltage_limit)

    def max_voltage_changed(self, voltage: float):
        """

        """
        if self.sb_auto_limits.isChecked():
            self.user_current_limit = self.sb_max_voltage.value()

        else:
            self.user_voltage_limit = self.sb_max_voltage.value()

    @property
    def value(self) -> IVCurveParameters:
        """
        :returns: Values of the measurement parameters.
        """
        params = IVCurveParameters()

        # sweep direction
        sweep_dir = (
            SweepDirection.Forward
            if self.cb_sweep_direction.currentText() == 'Forward' else
            SweepDirection.Reverse
        )

        # auto limits
        auto_lims = self.sb_auto_limits.isChecked()
        params.automatic_limits = auto_lims

        if auto_lims:
            # @todo
            raise NotImplementedError('Automatic limits not yet implmented')

        else:
            if sweep_dir is SweepDirection.Forward:
                params.start_voltage = self.sb_min_voltage.value()
                params.stop_voltage = self.sb_max_voltage.value()

            else:
                params.start_voltage = self.sb_max_voltage.value()
                params.stop_voltage = self.sb_min_voltage.value()

        params.voltage_step = self.sb_voltage_step.value() * 1000
        params.sweep_rate = self.sb_sweep_rate.value() * 1000
        params.settling_time = self.sb_settling_time.value()

        return params

    def reset_fields(self):
        """
        Reset field values to default.
        """
        self.sb_auto_limits.setChecked(False)
        self.sb_min_voltage.setValue(0)
        self.sb_max_voltage.setValue(self.user_voltage_limit)
        self.sb_voltage_step.setValue(5)
        self.sb_sweep_rate.setValue(20)
        self.sb_settling_time.setValue(5)
        self.cb_sweep_direction.setCurrentIndex(0)
