from PyQt5.QtCore import (
    Qt,
)

from PyQt5.QtWidgets import (
    QVBoxLayout,
    QWidget,
)

from .components.plot_header import PlotHeaderWidget
from .components.graph_panels import GraphPanels


class PlotFrame(QWidget):

    def __init__(self):
        super().__init__()

        self.init_ui()


    def init_ui(self):
        self.plotHeader = PlotHeaderWidget()
        self.StackGraphPanels = GraphPanels()

        #plot frame and layout
        plotFrameLayout = QVBoxLayout()
        plotFrameLayout.addWidget(self.plotHeader)
        plotFrameLayout.addWidget(self.StackGraphPanels)
        self.setLayout(plotFrameLayout)
