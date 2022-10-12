from PyQt6.QtWidgets import (
    QHBoxLayout,
    QVBoxLayout,
    QWidget,
)

from .base_classes import ToggleUiInterface
from .components import (
    AuthenticationWidget,
    PlotHeaderWidget,
    ResultsWidget
)


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
        self.wgt_results = ResultsWidget()

        # header
        lo_header = QHBoxLayout()
        lo_header.addWidget(self.plot_header)
        lo_header.addWidget(self.authentication)

        # layout
        lo_main = QVBoxLayout()
        lo_main.addLayout(lo_header)
        lo_main.addWidget(self.wgt_results, stretch=100)
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
