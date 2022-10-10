from PyQt6.QtWidgets import QVBoxLayout

from iv_lab_controller.base_classes import ValueWidget
from iv_lab_controller.parameters import SystemParameters

from . import (
    IlluminationParametersWidget,
    CellParametersWidget,
    ComplianceParametersWidget,
)


class SystemParametersWidget(ValueWidget):
    """
    Container widget for system parameters.
    """
    def __init__(self):
        super().__init__()

        self.init_ui()

    def init_ui(self):
        self.wgt_illumination_parameters = IlluminationParametersWidget()
        self.wgt_cell_parameters = CellParametersWidget()
        self.wgt_compliance_parameters = ComplianceParametersWidget()

        # layout
        lo_main = QVBoxLayout()
        lo_main.addWidget(self.wgt_illumination_parameters)
        lo_main.addWidget(self.wgt_cell_parameters)
        lo_main.addWidget(self.wgt_compliance_parameters)

        self.setLayout(lo_main)

    def enable_ui(self):
        self.wgt_illumination_parameters.enable_ui()
        self.wgt_cell_parameters.enable_ui()
        self.wgt_compliance_parameters.enable_ui()

    def disable_ui(self):
        self.wgt_illumination_parameters.disable_ui()
        self.wgt_cell_parameters.disable_ui()
        self.wgt_compliance_parameters.disable_ui()

    @property
    def value(self) -> SystemParameters:
        """
        :returns: System parameters.
        """
        params = SystemParameters()
        params.illumination_parameters = self.wgt_illumination_parameters.value
        params.cell_parameters = self.wgt_cell_parameters.value
        params.compliance_parameters = self.wgt_compliance_parameters.value

        return params
