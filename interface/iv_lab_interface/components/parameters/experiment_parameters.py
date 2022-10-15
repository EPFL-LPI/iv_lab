import logging
from typing import List, Union

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

from .parameters_widget_base import ParametersWidgetBase


logger = logging.getLogger('iv_lab')


class ExperimentParametersWidget(QGroupBox, ParametersWidgetBase):
    queue_experiment = pyqtSignal(type(Experiment), ExperimentParametersInterface)

    def __init__(self):
        super().__init__("Measurement")

        self._experiments: List[Experiment] = []

        self.init_ui()
        self.register_connections()
        self.init_observers()

    def init_observers(self):
        super().init_observers()

        # system
        def system_changed(system: System, o_sys: System):
            """
            Updates the UI to match the system's experiments.
            """
            self._experiments = []
            # collect experiments
            if system is not None:
                user = Store.get('user')
                for perm in user.permissions:
                    self._experiments += system.experiments_for_permission(perm)

            # clear holders
            self.cb_measurement_select.clear()
            while True:
                wgt = self.stk_experiments.widget(0)
                if wgt is None:
                    break

                self.stk_experiments.removeWidget(wgt)

            # load experiments
            for exp in self.experiments:
                self.cb_measurement_select.addItem(exp.name)

                e_ui = exp.ui()
                self.stk_experiments.addWidget(e_ui)

                # @note: Queueing functionality not implemented but
                #   placeholders left in for future use.
                e_ui.queue.connect(lambda: self.queue_experiment.emit(exp, e_ui.value))

        sys_observer = Observer(changed=system_changed)
        Store.subscribe('system', sys_observer)

    @property
    def experiments(self) -> List[Experiment]:
        """
        :returns: List of avaialble experiments.
        """
        return self._experiments

    @property
    def active_experiment(self) -> Union[Experiment, None]:
        """
        :returns: Currently selected experiment.
        """
        selected = self.cb_measurement_select.currentIndex()
        if selected < 0:
            return None

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

    def reset_fields(self):
        """
        Reset fields on all experiments, if possible.
        """
        for i in range(self.stk_experiments.count()):
            wgt = self.stk_experiments.widget(i)
            wgt.reset_fields()
