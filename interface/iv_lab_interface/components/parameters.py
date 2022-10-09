from typing import Type, Tuple

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QVBoxLayout

from iv_lab_controller.base_classes import ValueWidget, Experiment
from iv_lab_controller.parameters import CompleteParameters

from ..base_classes import ToggleUiInterface
from . import (
    ExperimentParametersWidget,
    SystemParametersWidget,
)


class ParametersWidget(ValueWidget, ToggleUiInterface):
    """
    Container for system and experiment parameters.
    """
    # @note: Currently unused. Placeholder for queueing.
    queue_experiment = pyqtSignal()

    def __init__(self):
        super().__init__()

        self.init_ui()

    def init_ui(self):
        self.wgt_system_parameters = SystemParametersWidget()
        self.wgt_experiment_parameters = ExperimentParametersWidget()

        lo_main = QVBoxLayout()
        lo_main.addWidget(self.wgt_system_parameters)
        lo_main.addWidget(self.wgt_experiment_parameters)
        self.setLayout(lo_main)

    def enable_ui(self):
        self.wgt_system_parameters.enable_ui()
        self.wgt_experiment_parameters.enable_ui()

    def disable_ui(self):
        self.wgt_system_parameters.disable_ui()
        self.wgt_experiment_parameters.disable_ui()

    def reset_all_fields(self):
        self.wgt_system_parameters.reset_fields()
        self.wgt_experiment_parameters.reset_fields()

    @property
    def value(self) -> Tuple[Type[Experiment], CompleteParameters]:
        exp = self.wgt_experiment_parameters.active_experiment

        params = CompleteParameters()
        params.system_parameters = self.wgt_system_parameters.value
        params.experiment_parameters = self.wgt_experiment_parameters.value

        return (exp, params)
