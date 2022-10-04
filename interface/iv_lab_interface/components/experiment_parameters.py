from typing import List

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QStackedWidget,
    QVBoxLayout,
    QGroupBox,
    QComboBox,
)

from iv_lab_controller.base_classes.measurement_parameters import MeasurementParameters
from iv_lab_controller.base_classes.experiment import Experiment


class ExperimentParametersWidget(QGroupBox):
    run_experiment = pyqtSignal()
    abort = pyqtSignal()

    def __init__(self):
        super().__init__("Measurement")
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
            e_ui.run.connect(self.run_experiment.emit)

    @property
    def active_experiment(self) -> Experiment:
        """
        :returns: Currently selected experiment.
        """
        selected = self.cb_measurement_select.currentIndex()
        return self.experiments[selected]

    @property
    def value(self) -> MeasurementParameters:
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

    def select_experiment(self, i: int):
        """
        Sets the measurement parameters to the correct type.
        Emits a `experiement_change` signal.

        :param i: Index of the measurement.
        """
        self.stk_experiments.setCurrentIndex(i)

    def _abort(self):
        """
        Signal to abort measurement.
        """
        self.abort.emit()
