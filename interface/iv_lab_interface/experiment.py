from PyQt6.QtWidgets import (
    QVBoxLayout,
    QPushButton,
    QStackedWidget,
    QWidget
)

from iv_lab_controller import Runner
from iv_lab_controller.types import RunnerState
from iv_lab_controller.store import Store, Observer

from . import common
from .types import (
    ExperimentAction,
    HardwareState,
)

from .components import (
    ParametersWidget,
    HardwareInitialization,
)

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
        self.wgt_hardware = HardwareInitialization()
        self.wgt_parameters = ParametersWidget()

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
        lo_main.addWidget(self.stk_action)
        lo_main.addWidget(self.btn_reset_fields)
        
        self.setLayout(lo_main)  
    
    def init_observers(self):
        # experiment state
        def runner_state_changed(state: RunnerState, o_state: RunnerState):
            """
            Sets the current experiment state.
            """
            if state == RunnerState.Standby:
                self.stk_action.setCurrentIndex(ExperimentAction.Run.value)
                self.btn_run.setEnabled(True)
                self.btn_abort.setEnabled(False)
            
            elif state == RunnerState.Running:
                self.stk_action.setCurrentIndex(ExperimentAction.Abort.value)
                self.btn_run.setEnabled(False)
                self.btn_abort.setEnabled(True)
                
            elif state == RunnerState.Aborting:
                self.stk_action.setCurrentIndex(ExperimentAction.Run.value)
                self.btn_run.setEnabled(False)
                self.btn_abort.setEnabled(False)

            else:
                # @unreachable
                raise ValueError('Unknown experiment state.')

        runner_state_observer = Observer(changed=runner_state_changed)
        Store.subscribe('runner_state', runner_state_observer)

        # hardware state
        def hardware_state_changed(state: HardwareState, o_state: HardwareState):
            if state is HardwareState.Uninitialized:
                self.wgt_parameters.disable_ui()
                self.btn_run.setEnabled(False)
                self.btn_abort.setEnabled(False)

            elif state is HardwareState.Initialized:
                self.wgt_parameters.enable_ui()
                self.btn_run.setEnabled(True)
                self.btn_abort.setEnabled(True)

            elif state is HardwareState.Error:
                # allow user to attempt reinitialization
                self.enable_ui()

            else:
                raise ValueError('Unknown hardware state')

        hardware_state_observer = Observer(changed=hardware_state_changed)
        Store.subscribe('hardware_state', hardware_state_observer)

    def register_connections(self):
        self.btn_reset_fields.clicked.connect(self.reset_all_fields)

        self.btn_run.clicked.connect(self.trigger_run)
        self.btn_abort.clicked.connect(self.trigger_abort)

    def reset_all_fields(self):
        self.wgt_parameters.reset_fields()

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
