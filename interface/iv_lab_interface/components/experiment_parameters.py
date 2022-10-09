from typing import List

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QStackedWidget,
    QVBoxLayout,
    QGroupBox,
    QComboBox,
)

from iv_lab_controller import Store
from iv_lab_controller.store import Observer
from iv_lab_controller.base_classes import (
    ExperimentParametersInterface,
    Experiment,
    System,
)

from ..base_classes import ToggleUiInterface
from ..types import ApplicationState, HardwareState


class ExperimentParametersWidget(QGroupBox, ToggleUiInterface):
    queue_experiment = pyqtSignal(type(Experiment), ExperimentParametersInterface)

    def __init__(self):
        super().__init__("Measurement")

        self._experiments: List[Experiment] = []
        
        self.init_ui()
        self.register_connections()
        self.init_observers()

    def init_observers(self):
        # system
        def system_changed(system: System, o_sys: System):
            """
            Updates the UI to match the system's experiments.
            """
            self._experiments: List[Experiment] = []

            # collect experiments
            if system is not None:
                user = Store.get('user')
                for perm in user.permissions:
                    self._experiments += system.experiments_for_permission(perm)

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

        sys_observer = Observer(changed=system_changed)
        Store.subscribe('system', sys_observer)

        # hardware
        def hardware_state_changed(state: HardwareState, o_state: HardwareState):
            if state == HardwareState.Uninitialized:
                self.disable_ui()

        hardware_state_observer = Observer(changed=hardware_state_changed)
        Store.subscribe('hardware_state', hardware_state_observer)

        # application state
        def app_state_changed(state: ApplicationState, o_state: ApplicationState):
            if state is ApplicationState.Disabled:
                self.disable_ui()

        app_state_observer = Observer(changed=app_state_changed)
        Store.subscribe('application_state', app_state_observer)
                
    @property
    def experiments(self) -> List[Experiment]:
        """
        :returns: List of avaialble experiments.
        """
        return self._experiments

    @property
    def active_experiment(self) -> Experiment:
        """
        :returns: Currently selected experiment.
        """
        selected = self.cb_measurement_select.currentIndex()
        return self.experiments[selected]

    @property
    def value(self) -> ExperimentParametersInterface:
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

        lo_main = QVBoxLayout()
        lo_main.addWidget(self.cb_measurement_select)
        lo_main.addWidget(self.stk_experiments)

        self.setLayout(lo_main)
        self.setEnabled(False)
        self.setMaximumWidth(300)

    def register_connections(self):
        self.cb_measurement_select.currentIndexChanged.connect(self.select_experiment)

    def enable_ui(self):
        self.setEnabled(True)

    def disable_ui(self):
        self.setEnabled(False)

    def select_experiment(self, i: int):
        """
        Sets the measurement parameters to the correct type.
        Emits a `experiement_change` signal.

        :param i: Index of the measurement.
        """
        self.stk_experiments.setCurrentIndex(i)
