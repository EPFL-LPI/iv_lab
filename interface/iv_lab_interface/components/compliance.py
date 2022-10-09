from PyQt6.QtWidgets import (
    QLabel,
    QDoubleSpinBox,
    QGridLayout,
    QGroupBox
)

from iv_lab_controller.parameters import ComplianceParameters

from ..base_classes import ToggleUiInterface


class ComplianceWidget(QGroupBox, ToggleUiInterface):
    def __init__(self):
        super().__init__("Compliance")

        self.init_ui()

    def init_ui(self):
        lbl_voltage_limit = QLabel("Voltage Limit")
        lbl_voltage_limit_units = QLabel("V")
        self.sb_voltage_limit = QDoubleSpinBox()
        self.sb_voltage_limit.setDecimals(2)
        self.sb_voltage_limit.setSingleStep(0.1)
        self.sb_voltage_limit.setMinimum(0)
        self.sb_voltage_limit.setMaximumWidth(75)

        lbl_current_limit = QLabel("Current Limit")
        lbl_current_limit_units = QLabel("mA")
        self.sb_current_limit = QDoubleSpinBox()
        self.sb_current_limit.setDecimals(2)
        self.sb_current_limit.setSingleStep(5)
        self.sb_current_limit.setMinimum(0)
        self.sb_current_limit.setMaximumWidth(75)
        
        lo_main = QGridLayout()
        lo_main.addWidget(lbl_voltage_limit, 0, 0)
        lo_main.addWidget(self.sb_voltage_limit, 0, 1)
        lo_main.addWidget(lbl_voltage_limit_units, 0, 2)

        lo_main.addWidget(lbl_current_limit, 1, 0)
        lo_main.addWidget(self.sb_current_limit, 1, 1)
        lo_main.addWidget(lbl_current_limit_units, 1, 2)
        
        self.setLayout(lo_main)
        self.setMaximumWidth(300)

        self.disable_ui()
        self.reset_fields()

    @property
    def value(self) -> ComplianceParameters:
        """
        :returns: Compliance parameters.
        """
        params = ComplianceParameters()
        params.voltage_limit = self.sb_voltage_limit.value()
        params.current_limit = self.sb_current_limit.value() / 1000

        return params

    def enable_ui(self):
        self.setEnabled(True)

    def disable_ui(self):
        self.setEnabled(False)

    def reset_fields(self):
        """
        Reset field value to a default value.
        """
        self.sb_voltage_limit.setValue(2)
        self.sb_current_limit.setValue(5)
