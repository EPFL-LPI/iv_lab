from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import (
    QLabel,
    QPushButton,
    QComboBox,
    QLineEdit,
    QCheckBox,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QGroupBox,
    QStackedWidget,
    QFrame,
    QWidget,
)
        
class PlotHeaderWidget(QWidget):
    signal_save_data = pyqtSignal(str)
    signal_toggle_auto_save = pyqtSignal(bool)

    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        self.in_cell_name = QLineEdit()
        self.in_cell_name.setPlaceholderText('Enter Cell Name Here...')
        self.in_cell_name.setMinimumWidth(500)
        self.in_cell_name.setEnabled(False)
        
        self.cb_auto_save = QCheckBox("Autosave")
        self.cb_auto_save.setEnabled(False)
        self.cb_auto_save.stateChanged.connect(self.toggle_auto_save)
        
        self.btn_save = QPushButton("Save Data",self)
        self.btn_save.clicked.connect(self.save_data)
        self.btn_save.setEnabled(False)
        
        # Set the plot header layout
        lo_main = QHBoxLayout()
        lo_main.addWidget(self.in_cell_name)
        lo_main.addWidget(self.cb_auto_save)
        lo_main.addWidget(self.btn_save)
        self.setLayout(lo_main)
    
    @property
    def cell_name(self) -> str:
        """
        :returns: Entered cell name.
        """
        return self.in_cell_name.text()

    def toggle_auto_save(self):
        if self.cb_auto_save.isChecked():
            self.signal_toggle_auto_save.emit(True)

        else:
            self.signal_toggle_auto_save.emit(False)

    def save_data(self):
        cell_name = self.in_cell_name.text()
        
        self.signal_save_data.emit(cell_name)