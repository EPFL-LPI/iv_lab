from PyQt5.QtGui import QDoubleValidator

from PyQt5.QtWidgets import (
    QLabel,
    QLineEdit,
    QHBoxLayout,
    QWidget,
)


class CellSizeWidget(QWidget):

    def __init__(self):
        super().__init__()

        self.init_ui()

    def init_ui(self): 
        # cell active area
        cellSizeLayout = QHBoxLayout()
        self.labelCellActiveArea = QLabel("Cell Active Area")
        self.fieldCellActiveArea = QLineEdit("1.00")
        self.CellActiveAreaValidator = QDoubleValidator()
        self.fieldCellActiveArea.setValidator(self.CellActiveAreaValidator)
        self.fieldCellActiveArea.setMaximumWidth(75)
        self.labelCellActiveAreaUnits = QLabel("cm^2")
        cellSizeLayout.addWidget(self.labelCellActiveArea)
        cellSizeLayout.addWidget(self.fieldCellActiveArea)
        cellSizeLayout.addWidget(self.labelCellActiveAreaUnits)
        self.setLayout(cellSizeLayout)
        self.setEnabled(False)
    