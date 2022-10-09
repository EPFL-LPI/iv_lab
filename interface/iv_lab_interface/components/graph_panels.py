import os
from typing import List

from PyQt6.QtWidgets import QTabWidget
from pymeasure.experiment import Results
from pymeasure.display.widgets import PlotWidget

from iv_lab_controller.store import Store, Observer


class GraphPanels(QTabWidget):
    """
    Displays results.
    """
    def __init__(self):
        super().__init__()
        self._results: List[Results] = []
        self.init_observers()
        
    def init_observers(self):
        # results
        def results_changed(results: List[Results], o_results: List[Results]):
            for result in results:
                if result not in self._results:
                    self.add_result(result)

        results_observer = Observer(changed=results_changed)
        Store.subscribe('experiment_results', results_observer)

    @property
    def results(self) -> List[Results]:
        """
        :returns: Results.
        """
        return self._results

    def add_result(self, result: Results):
        """
        """
        self._results.append(result)
        res_name = os.path.basename(result.data_filename)
        res_name, _ = os.path.splitext(res_name)

        wgt_plot = PlotWidget(
            res_name,
            result.procedure.DATA_COLUMNS
        )
        curve = wgt_plot.new_curve(result)
        wgt_plot.load(curve)

        tab_i = self.addTab(wgt_plot, res_name)
        self.setCurrentIndex(tab_i)
