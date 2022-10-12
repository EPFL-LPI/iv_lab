from typing import Union

from PyQt6.QtWidgets import (
    QVBoxLayout,
    QPushButton,
    QStackedWidget,
    QWidget
)

from iv_lab_controller import Runner
from iv_lab_controller.types import RunnerState
from iv_lab_controller.store import Store, Observer
from iv_lab_controller.base_classes import System

from . import common
from .types import (
    ExperimentAction,
    HardwareState,
    ApplicationState,
)

from .components import HardwareInitializationWidget
from .components.parameters import CompleteParametersWidget


class ExperimentFrame(QWidget):
    def __init__(self):
        super().__init__()

        self._runner = Runner()

        self.init_ui()
        self.register_connections()
        self.init_observers()

    @property
    def runner(self) -> Runner:
        """
        :returns: Runner.
        """
        return self._runner

    def init_ui(self):
        self.wgt_hardware = HardwareInitializationWidget()
        self.wgt_parameters = CompleteParametersWidget()

        # run / abort
        self.btn_run = QPushButton('Run')
        self.btn_run.setEnabled(False)
        self.btn_abort = QPushButton('Abort')
        self.btn_abort.setEnabled(False)
        self.stk_action = QStackedWidget()
        self.stk_action.insertWidget(ExperimentAction.Run.value, self.btn_run)
        self.stk_action.insertWidget(ExperimentAction.Abort.value, self.btn_abort)

        # reset button
        self.btn_reset_fields = QPushButton("Reset All Settings To Default", self)
        self.btn_reset_fields.setEnabled(False)

        # Set the measurement frame layout
        lo_main = QVBoxLayout()
        lo_main.addWidget(self.wgt_hardware)
        lo_main.addWidget(self.wgt_parameters)
        lo_main.addStretch()
        lo_main.addWidget(self.stk_action)
        lo_main.addWidget(self.btn_reset_fields)

        self.setLayout(lo_main)

    def init_observers(self):
        # runner
        def runner_state_ui(state: RunnerState):
            """
            Sets UI based on current runner state.
            """
            if state == RunnerState.Standby:
                self.enable_run_ui()

            elif state == RunnerState.Running:
                self.enable_abort_ui()

            elif state == RunnerState.Aborting:
                self.disable_ui()

            else:
                # @unreachable
                raise ValueError('Unknown runner state.')

        # experiment state
        def runner_state_changed(state: RunnerState, o_state: RunnerState):
            runner_state_ui(state)

        runner_state_observer = Observer(changed=runner_state_changed)
        Store.subscribe('runner_state', runner_state_observer)

        # hardware state
        def enable_hardware_ui(state: HardwareState):
            if state is HardwareState.Uninitialized:
                self.disable_ui()

            elif state is HardwareState.Initialized:
                self.enable_run_ui()
                self.btn_reset_fields.setEnabled(True)

            elif state is HardwareState.Error:
                # allow user to attempt reinitialization
                runner_state = Store.get('runner_state')
                runner_state_ui(runner_state)

            else:
                # @unreachable
                raise ValueError('Unknown hardware state')

        def hardware_state_changed(state: HardwareState, o_state: HardwareState):
            enable_hardware_ui(state)

        hardware_state_observer = Observer(changed=hardware_state_changed)
        Store.subscribe('hardware_state', hardware_state_observer)

        # application state
        def app_state_changed(state: ApplicationState, o_state: ApplicationState):
            if state is ApplicationState.Disabled:
                self.disable_ui()

            elif state is ApplicationState.Active:
                enable_hardware_ui(Store.get('hardware_state'))

            elif state is ApplicationState.Error:
                self.disable_ui()

            else:
                # @unreachable
                raise ValueError('Unknown application state')

        app_state_observer = Observer(changed=app_state_changed)
        Store.subscribe('application_state', app_state_observer)

        # system
        def system_changed(system: Union[System, None], o_sys: Union[System, None]):
            if system is None:
                self.btn_reset_fields.setEnabled(False)

            else:
                enable = Store.get('application_state') is not ApplicationState.Disabled
                self.btn_reset_fields.setEnabled(enable)

        system_observer = Observer(changed=system_changed)
        Store.subscribe('system', system_observer)

    def register_connections(self):
        self.btn_reset_fields.clicked.connect(self.reset_all_fields)

        self.btn_run.clicked.connect(self.trigger_run)
        self.btn_abort.clicked.connect(self.trigger_abort)

    def enable_run_ui(self):
        """
        Enable run UI, diable abort UI.
        """
        self.stk_action.setCurrentIndex(ExperimentAction.Run.value)
        self.btn_run.setEnabled(True)
        self.btn_abort.setEnabled(False)

    def enable_abort_ui(self):
        """
        Enable abort UI, diable run UI.
        """
        self.stk_action.setCurrentIndex(ExperimentAction.Abort.value)
        self.btn_run.setEnabled(False)
        self.btn_abort.setEnabled(True)

    def disable_ui(self):
        """
        Disable own UI elements. Show run UI.
        """
        self.stk_action.setCurrentIndex(ExperimentAction.Run.value)
        self.btn_run.setEnabled(False)
        self.btn_abort.setEnabled(False)
        self.btn_reset_fields.setEnabled(False)

    def reset_all_fields(self):
        Store.emit('reset_parameter_fields')

    def trigger_abort(self):
        """
        Trigger an abort.
        """
        self.btn_abort.setEnabled(False)
        self.runner.abort()

    def trigger_run(self):
        """
        Submits all experiments in the queue to be run.
        """
        self.btn_run.setEnabled(False)

        # check runner state
        try:
            runner_state = Store.get('runner_state')

        except KeyError:
            # runner not yet created
            pass

        else:
            if runner_state is RunnerState.Running:
                Store.set('status_msg', 'Already running')
                return

        # validate parameters
        exp, params = self.wgt_parameters.value
        try:
            params.validate()

        except ValueError as err:
            common.show_message_box(
                'Invalid parameters',
                f'{err}'
            )
            self.btn_run.setEnabled(True)
            return

        cell_name = Store.get('cell_name')
        if cell_name is None:
            common.show_message_box(
                'No cell name',
                'Please enter a name for your cell.'
            )
            self.btn_run.setEnabled(True)
            return

        # run
        self.runner.queue_experiment(exp, params)
        self._runner.run(cell_name)
