from PyQt6.QtWidgets import (
    QLabel,
    QDoubleSpinBox,
    QHBoxLayout,
    QWidget
)

from iv_lab_controller.parameters import CellParameters

from ..base_classes import ToggleUiInterface


class CellParametersWidget(QWidget, ToggleUiInterface):

    def __init__(self):
        super().__init__()

        self.init_ui()

    def init_ui(self): 
        # cell active area
        lbl_cell_area = QLabel("Cell Active Area")
        lbl_cell_area_units = QLabel("cm<sup>2</sup>")
        self.sb_cell_area = QDoubleSpinBox()
        self.sb_cell_area.setDecimals(2)
        self.sb_cell_area.setSingleStep(0.01)
        self.sb_cell_area.setMinimum(0)
        self.sb_cell_area.setMaximumWidth(75)
        
        lo_main = QHBoxLayout()
        lo_main.addWidget(lbl_cell_area)
        lo_main.addWidget(self.sb_cell_area)
        lo_main.addWidget(lbl_cell_area_units)
        self.setLayout(lo_main)

        self.disable_ui()
        self.reset_fields()
    
    @property
    def value(self) -> CellParameters:
        """
        :returns: Cell parameters.
        """
        params = CellParameters()
        params.cell_area = self.sb_cell_area.value()

        return params

    def enable_ui(self):
        self.setEnabled(True)

    def disable_ui(self):
        self.setEnabled(False)

    def reset_fields(self):
        """
        Reset field values to default values.
        """
        self.sb_cell_area.setValue(1)
