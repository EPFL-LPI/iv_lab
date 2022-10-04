from typing import Union, List

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QVBoxLayout,
    QPushButton,
    QWidget
)
from pymeasure.experiment.procedure import Procedure

from iv_lab_controller.base_classes.system import System
from iv_lab_controller.base_classes.experiment import Experiment

from . import common
from .base_classes.UiToggle import UiToggleInterface
from .components.illumination import IlluminationWidget
from .components.experiment_parameters import ExperimentParametersWidget
from .components.cell_parameters import CellParametersWidget
from .components.compliance import ComplianceWidget


class MeasurementFrame(QWidget, UiToggleInterface):
    initialize_hardware = pyqtSignal()
    run_procedure = pyqtSignal(Procedure)

    def __init__(self):
        super().__init__()
        
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

    def init_ui(self):
        # init button
        self.btn_initialize = QPushButton("Initialize Hardware", self)
        self.btn_initialize.setMaximumWidth(300)
        self.btn_initialize.setEnabled(False)
        
        # parameter widgets
        self.wgt_illumination_parameters = IlluminationWidget()
        self.wgt_experiment_parameters = ExperimentParametersWidget()
        self.wgt_cell_parameters = CellParametersWidget()
        self.wgt_compliance_parameters = ComplianceWidget()

        # reset button
        self.btn_reset_fields = QPushButton("Reset All Settings To Default", self)
        self.btn_reset_fields.setEnabled(False)
        
        # Set the measurement frame layout
        lo_main = QVBoxLayout()
        lo_main.addWidget(self.btn_initialize)
        lo_main.addStretch(1)
        lo_main.addWidget(self.wgt_illumination_parameters)
        lo_main.addStretch(1)
        lo_main.addWidget(self.wgt_experiment_parameters)
        lo_main.addStretch(1)
        lo_main.addWidget(self.wgt_cell_parameters)
        lo_main.addStretch(1)
        lo_main.addWidget(self.wgt_compliance_parameters)
        lo_main.addStretch(1)
        lo_main.addWidget(self.btn_reset_fields)
        
        self.setLayout(lo_main)  
    
    def register_connections(self):
        self.btn_initialize.clicked.connect(self.initialize_hardware.emit)
        self.btn_reset_fields.clicked.connect(self.reset_all_fields)

        self.wgt_experiment_parameters.run_experiment.connect(self._run_experiment)
        self.wgt_experiment_parameters.abort.connect(self.abort)

    def reset_all_fields(self):
        self.wgt_illumination_parameters.reset_fields()
        self.wgt_experiment_parameters.reset_fields()
        self.wgt_cell_parameters.reset_fields()
        self.wgt_compliance_parameters.reset_fields()

    def toggle_ui(self, enable: bool = True):
        """
        Enable or disable UI elements.

        :param enable: Whether to enable or disable elements.
            [Default: True]
        """
        if enable:
            self.enable_ui()

        else:
            self.disable_ui()

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
            
        self.wgt_illumination_parameters.setEnabled(enable)
        self.wgt_experiment_parameters.setEnabled(enable)
        self.wgt_compliance_parameters.setEnabled(enable)

    # @todo: Delegate to runner
    def abort(self):
        common.StatusBar().showMessage("Aborting measurement...")

    def _run_experiment(self):
        """
        Runs a given measurement type.

        :param measurement: Type of measurement to run.
        """
        if self.system is None:
            raise RuntimeError("System not set")

        exp = self.wgt_experiment_parameters.active_experiment
        params = self.wgt_experiment_parameters.value
        proc = exp.create_procedure(params.to_dict())
        self.run_procedure.emit(proc)
