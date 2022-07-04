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
    signal_saveScanData = pyqtSignal(str, str)
    signal_toggleAutoSave = pyqtSignal(bool)

    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        #buttons and fields above the plot
        self.fieldCellName = QLineEdit("Enter Cell Name Here...")
        self.fieldCellName.setMinimumWidth(500)
        self.fieldCellName.setEnabled(False)
        #self.fieldCellName.mousePressEvent = self.clearCellName
        self.fieldCellName.cursorPositionChanged.connect(self.clearCellName)
        
        self.checkBoxAutoSave = QCheckBox("Auto-save")
        self.checkBoxAutoSave.setEnabled(False)
        self.checkBoxAutoSave.stateChanged.connect(self.toggleAutoSaveMode)
        
        self.buttonSaveData = QPushButton("Save Data",self)
        self.buttonSaveData.clicked.connect(self.saveScanData)
        self.buttonSaveData.setEnabled(False)
        
        # Set the plot header layout
        headerLayout = QHBoxLayout()
        headerLayout.addWidget(self.fieldCellName)
        headerLayout.addWidget(self.checkBoxAutoSave)
        headerLayout.addWidget(self.buttonSaveData)
        self.setLayout(headerLayout)
    
    #argument 'e' is of type QMouseEvent.
    def clearCellName(self, e):
        cellName = self.fieldCellName.text()
        if cellName == "Enter Cell Name Here...":
            self.fieldCellName.setText("")

    def toggleAutoSaveMode(self):
        if self.checkBoxAutoSave.isChecked():
            self.signal_toggleAutoSave.emit(True)
        else:
            self.signal_toggleAutoSave.emit(False)

    def saveScanData(self):
        scanType = str(self.menuSelectMeasurement.currentText())
        cellName = self.fieldCellName.text()
        if cellName == "Enter Cell Name Here...":
            cellName = ""
        self.signal_saveScanData.emit(scanType, cellName)