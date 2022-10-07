from typing import Union, List, Type

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QVBoxLayout,
    QPushButton,
    QWidget
)
from pymeasure.experiment import Procedure

from iv_lab_controller.base_classes import (
    Experiment,
    System,
    ExperimentParameters,
)

from . import common
from .base_classes import ToggleUiInterface
from .types import ExperimentQueue, ExperimentAction
from .components import (
    ExperimentParametersWidget,
    SystemParametersWidget,
)


class ExperimentFrame(QWidget, ToggleUiInterface):
    initialize_hardware = pyqtSignal()
    run_experiments = pyqtSignal(list)

    def __init__(self):
        super().__init__()
        
        self._experiment_queue: ExperimentQueue = []
        self._experiments: List[Experiment] = []
        self.init_ui()
        self.register_connections()

    @property
    def system(self) -> Union[System, None]:
        """
        :returns: The System.
        """
        return self._system

    @system.setter
    def system(self, system: Union[System, None]):
        """
        Set the system.
        Toggle UI based on system.
        """
        self._system = system
        self.toggle_measurement_ui()

    @property
    def hardware_is_initialized(self) -> bool:
        """
        :returns: Whether of not the system is initialized.
        """
        return self.system is not None
    
    @property
    def experiments(self) -> List[Experiment]:
        """
        :returns: Experiments.
        """
        return self._experiments

    @experiments.setter
    def experiments(self, experiments: List[Experiment]):
        """
        Sets available experiments, update UI to match.

        :param experiments: List of experiments.
        """
        self._experiments: List[Experiment] = experiments
        self.wgt_experiment_parameters.experiments = self.experiments

    @property
    def experiment_queue(self) -> ExperimentQueue:
        """
        :returns: Queue of experiments. 
        """
        return self._experiment_queue

    def init_ui(self):
        # init button
        self.btn_initialize = QPushButton("Initialize Hardware", self)
        self.btn_initialize.setMaximumWidth(300)
        self.btn_initialize.setEnabled(False)
        
        # parameter widgets
        self.wgt_experiment_parameters = ExperimentParametersWidget()
        self.wgt_system_parameters = SystemParametersWidget()

        # reset button
        self.btn_reset_fields = QPushButton("Reset All Settings To Default", self)
        self.btn_reset_fields.setEnabled(False)
        
        # Set the measurement frame layout
        lo_main = QVBoxLayout()
        lo_main.addWidget(self.btn_initialize)
        lo_main.addWidget(self.wgt_system_parameters)
        lo_main.addWidget(self.wgt_experiment_parameters)
        lo_main.addWidget(self.btn_reset_fields)
        
        self.setLayout(lo_main)  
    
    def register_connections(self):
        self.btn_initialize.clicked.connect(self.initialize_hardware.emit)
        self.btn_reset_fields.clicked.connect(self.reset_all_fields)

        self.wgt_experiment_parameters.queue_experiment.connect(self.queue_experiment)
        self.wgt_experiment_parameters.action.connect(self.handle_action)

    def reset_all_fields(self):
        self.wgt_system_parameters.reset_fields()
        self.wgt_experiment_parameters.reset_fields()

    def enable_ui(self):
        self.btn_initialize.setEnabled(True)

    def disable_ui(self):
        self.btn_initialize.setEnabled(False)

    def toggle_measurement_ui(self, enable: Union[bool, None] = None):
        """
        Toggles the measurement UI enabled or disabled.

        :param enable: If `None`, determines the enables state by the system
        state.
        If a bool, forces the enabled state to it.
        """
        if enable is None:
            # use default value, based on system
            enable = self.hardware_is_initialized
            
        self.wgt_system_parameters.toggle_ui(enable)
        self.wgt_experiment_parameters.setEnabled(enable)

    def handle_action(self, action: ExperimentAction):
        """
        """
        if action == ExperimentAction.Run:
            self.run_experiment_queue()

        if action == ExperimentAction.Abort:
            self.abort()

    def abort(self):
        common.StatusBar().showMessage("Aborting measurement...")

    def clear_experiment_queue(self):
        """
        Clears the experiment queue.
        """
        self._experiment_queue = []

    def queue_experiment(self, experiment: Type[Experiment], params: ExperimentParameters):
        """
        """
        self._experiment_queue.append((experiment, params))

    def run_experiment_queue(self):
        """
        Submits all experiments in the queue to be run.
        """
        self.run_experiments.emit(self.experiment_queue)
