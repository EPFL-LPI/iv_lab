from PyQt6.QtCore import pyqtSignal, QRegularExpression
from PyQt6.QtGui import QRegularExpressionValidator
from PyQt6.QtWidgets import (
    QPushButton,
    QLineEdit,
    QCheckBox,
    QHBoxLayout,
    QWidget,
)

from ..base_classes import ToggleUiInterface

        
class PlotHeaderWidget(QWidget, ToggleUiInterface):
    signal_save_data = pyqtSignal(str)
    signal_toggle_auto_save = pyqtSignal(bool)

    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        # cell name
        cn_regex = QRegularExpression(r"[a-zA-Z\d\s\-_]{1,255}")
        cn_validator = QRegularExpressionValidator(cn_regex)
        self.in_cell_name = QLineEdit()
        self.in_cell_name.setValidator(cn_validator)
        self.in_cell_name.setPlaceholderText('Enter Cell Name Here...')
        self.in_cell_name.setMinimumWidth(500)
        self.in_cell_name.setEnabled(False)
        
        # save mode
        self.cb_auto_save = QCheckBox("Autosave")
        self.cb_auto_save.setEnabled(False)
        self.cb_auto_save.stateChanged.connect(self.toggle_auto_save)
        
        # save
        self.btn_save = QPushButton("Save Data",self)
        self.btn_save.clicked.connect(self.save_data)
        self.btn_save.setEnabled(False)
        
        # layout
        lo_main = QHBoxLayout()
        lo_main.addWidget(self.in_cell_name)
        lo_main.addWidget(self.cb_auto_save)
        lo_main.addWidget(self.btn_save)
        self.setLayout(lo_main)

        self.reset_fields()
    
    @property
    def cell_name(self) -> str:
        """
        :returns: Entered cell name.
        """
        return self.in_cell_name.text()

    def enable_ui(self):
        """
        Enable the UI elements.
        """
        self.in_cell_name.setEnabled(True)

    def disable_ui(self):
        """
        Disable the UI elements.
        """
        self.in_cell_name.setEnabled(False)

    def toggle_auto_save(self):
        if self.cb_auto_save.isChecked():
            self.signal_toggle_auto_save.emit(True)

        else:
            self.signal_toggle_auto_save.emit(False)

    def save_data(self):
        cell_name = self.in_cell_name.text()
        self.signal_save_data.emit(cell_name)

    def reset_fields(self):
        """
        Reset field values to default.
        """
        self.in_cell_name.clear()
        self.cb_auto_save.setChecked(False)
