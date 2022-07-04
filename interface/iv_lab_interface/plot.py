from PyQt5.QtCore import (
    Qt,
)

from PyQt5.QtWidgets import (
    QHBoxLayout,
    QVBoxLayout,
    QWidget,
)

from .components.authentication import AuthenticationWidget
from .components.plot_header import PlotHeaderWidget
from .components.graph_panels import GraphPanels


class PlotFrame(QWidget):

    def __init__(self):
        super().__init__()

        self.init_ui()


    def init_ui(self):
        self.authentication = AuthenticationWidget()
        self.plotHeader = PlotHeaderWidget()
        self.StackGraphPanels = GraphPanels()

        # header
        lo_header = QHBoxLayout()
        lo_header.addWidget(self.plotHeader)
        lo_header.addStretch(1)
        lo_header.addWidget(self.authentication)

        #plot frame and layout
        plotFrameLayout = QVBoxLayout()
        plotFrameLayout.addLayout(lo_header)
        plotFrameLayout.addWidget(self.StackGraphPanels)
        self.setLayout(plotFrameLayout)
