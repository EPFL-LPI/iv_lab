from PyQt6.QtWidgets import (
    QHBoxLayout,
    QVBoxLayout,
    QWidget,
)

from pymeasure.experiment import Results

from .base_classes import ToggleUiInterface
from .components.authentication import AuthenticationWidget
from .components.plot_header import PlotHeaderWidget
from .components.graph_panels import GraphPanels


class PlotFrame(QWidget, ToggleUiInterface):
    """
    Plot frame.
    """
    def __init__(self):
        super().__init__()

        self.init_ui()


    def init_ui(self):
        # subwidgets
        self.authentication = AuthenticationWidget()
        self.plot_header = PlotHeaderWidget()
        self.plots_panel = GraphPanels()

        # header
        lo_header = QHBoxLayout()
        lo_header.addWidget(self.plot_header)
        lo_header.addWidget(self.authentication)

        # layout
        lo_main = QVBoxLayout()
        lo_main.addLayout(lo_header)
        lo_main.addWidget(self.plots_panel, stretch=100)
        self.setLayout(lo_main)

    def enable_ui(self):
        """
        Enable UI elements.
        """
        self.plot_header.enable_ui()
    
    def disable_ui(self):
        """
        Disable UI elements.
        """
        self.plot_header.disable_ui()

    @property
    def cell_name(self) -> str:
        """
        :returns: Current cell name entered.
        """
        return self.plot_header.cell_name

    def add_result(self, result: Results):
        """
        Adds a result to the plots.
        """
        self.plots_panel.add_result(result)
