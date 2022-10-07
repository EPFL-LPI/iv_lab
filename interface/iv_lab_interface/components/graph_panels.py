from typing import List

from PyQt6.QtWidgets import QTabWidget
from pymeasure.experiment import Results
from pymeasure.display.widgets import PlotWidget


class GraphPanels(QTabWidget):
    """
    Displays results.
    """
    def __init__(self):
        super().__init__()
        self._results: List[Results] = []
        
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
        wgt_plot = PlotWidget('test', ('x', 'y'))
        wgt_plot.new_curve(result)
        self.addTab(wgt_plot, str(len(self.results)))
