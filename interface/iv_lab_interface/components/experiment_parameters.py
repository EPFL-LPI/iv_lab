from typing import List

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QStackedWidget,
    QPushButton,
    QVBoxLayout,
    QGroupBox,
    QComboBox,
)

from iv_lab_controller.base_classes import ExperimentParameters, Experiment

from ..types import ExperimentAction, ExperimentState


class ExperimentParametersWidget(QGroupBox):
    queue_experiment = pyqtSignal(type(Experiment), ExperimentParameters)
    action = pyqtSignal(ExperimentAction)

    def __init__(self):
        super().__init__("Measurement")
        
        self._state = ExperimentState.Standby

        self.init_ui()
        self.register_connections()

    @property
    def experiments(self) -> List[Experiment]:
        """
        :returns: List of experiments.
        """
        return self._experiments

    @experiments.setter
    def experiments(self, experiments: List[Experiment]):
        """
        Sets the widgets experiments and update the UI to match.
        """
        self._experiments: List[Experiment] = experiments

        # clear holders
        self.cb_measurement_select.clear()
        for i in range(self.stk_experiments.count()):
            wgt = self.stk_experiments.widget(i)
            self.stk_experiments.removeWidget(wgt)

        # load experiments
        for exp in self.experiments:
            self.cb_measurement_select.addItem(exp.name)

            e_ui = exp.ui()
            self.stk_experiments.addWidget(e_ui)
            e_ui.queue.connect(lambda: self.queue_experiment.emit(exp, e_ui.value))

    @property
    def active_experiment(self) -> Experiment:
        """
        :returns: Currently selected experiment.
        """
        selected = self.cb_measurement_select.currentIndex()
        return self.experiments[selected]

    @property
    def state(self) -> ExperimentState:
        """
        :returns: Current state of the experiment.
        """
        return self._state

    @state.setter
    def state(self, state: ExperimentState):
        """
        Sets the current experiment state.
        """
        self._state = state
        if self.state == ExperimentState.Standby:
            self.stk_action.setCurrentIndex(ExperimentAction.Run.value)
            self.btn_run.setEnabled(True)
        
        elif self.state == ExperimentState.Running:
            self.stk_action.setCurrentIndex(ExperimentAction.Abort.value)
            
        elif self.state == ExperimentState.Aborting:
            self.stk_action.setCurrentIndex(ExperimentAction.Run.value)
            self.btn_run.setEnabled(False)

        else:
            # @unreachable
            raise ValueError('Unknown experiment state.')

    @property
    def value(self) -> ExperimentParameters:
        """
        :returns: Parameter values of the active measurement.
        """
        active_wgt = self.stk_experiments.currentWidget()
        if active_wgt is None:
            # @unreachable
            raise RuntimeError("No measurement selected")

        return active_wgt.value

    def init_ui(self):
        self.cb_measurement_select = QComboBox()
        self.cb_measurement_select.setMaximumWidth(300)
        self.stk_experiments = QStackedWidget()

        self.btn_run = QPushButton('Run')
        self.btn_abort = QPushButton('Abort')
        self.stk_action = QStackedWidget()
        self.stk_action.insertWidget(ExperimentAction.Run.value, self.btn_run)
        self.stk_action.insertWidget(ExperimentAction.Abort.value, self.btn_abort)

        lo_main = QVBoxLayout()
        lo_main.addWidget(self.cb_measurement_select)
        lo_main.addWidget(self.stk_experiments)
        lo_main.addWidget(self.stk_action)

        self.setLayout(lo_main)
        self.setEnabled(False)
        self.setMaximumWidth(300)

    def register_connections(self):
        self.cb_measurement_select.currentIndexChanged.connect(self.select_experiment)
        self.btn_run.clicked.connect(self.trigger_run)
        self.btn_abort.clicked.connect(self.trigger_abort)

    def select_experiment(self, i: int):
        """
        Sets the measurement parameters to the correct type.
        Emits a `experiement_change` signal.

        :param i: Index of the measurement.
        """
        self.stk_experiments.setCurrentIndex(i)

    def trigger_run(self):
        """
        Trigger a run.
        """
        self.action.emit(ExperimentAction.Run)
        self.state = ExperimentState.Running

    def trigger_abort(self):
        """
        Trigger an abort.
        """
        self.action.emit(ExperimentAction.Abort)
        self.state = ExperimentState.Aborting
