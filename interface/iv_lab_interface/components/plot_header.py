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
        
        self.panelLogIn = QWidget()
        panelLogInLayout = QHBoxLayout()
        self.fieldUserName = QLineEdit("Username")
        self.fieldUserName.setMinimumWidth(100)
        self.fieldUserName.cursorPositionChanged.connect(self.clearUserName)
        self.fieldUserSciper = QLineEdit("Sciper")
        self.fieldUserSciper.returnPressed.connect(self.logIn)
        self.fieldUserSciper.setMinimumWidth(100)
        self.fieldUserSciper.cursorPositionChanged.connect(self.clearSciper)
        self.buttonLogIn = QPushButton("Log In",self)
        self.buttonLogIn.clicked.connect(self.logIn)
        
        panelLogInLayout.addWidget(self.fieldUserName)
        panelLogInLayout.addWidget(self.fieldUserSciper)
        panelLogInLayout.addWidget(self.buttonLogIn)
        self.panelLogIn.setLayout(panelLogInLayout)
        #self.panelLogIn.setMaximumHeight(35)
        
        self.panelLogOut = QWidget()
        panelLogOutLayout = QHBoxLayout()
        self.labelLoggedInAs = QLabel("Logged in as: ")
        self.labelUserName = QLabel("jean toutlemonde")
        self.buttonLogOut = QPushButton("Log Out",self)
        self.buttonLogOut.clicked.connect(self.logOut)
        
        panelLogOutLayout.addWidget(self.labelLoggedInAs)
        panelLogOutLayout.addWidget(self.labelUserName)
        panelLogOutLayout.addWidget(self.buttonLogOut)
        self.panelLogOut.setLayout(panelLogOutLayout)
        #self.panelLogOut.setMaximumHeight(35)
        
        self.StackLogInOut = QStackedWidget()
        self.StackLogInOut.addWidget(self.panelLogIn)
        self.StackLogInOut.addWidget(self.panelLogOut)
        #self.StackLogInOut.setMaximumHeight(40)
        self.StackLogInOut.setCurrentIndex(0) # 0 = login, 1 = logout
        
        # Set the plot header layout
        headerLayout = QHBoxLayout()
        headerLayout.addWidget(self.fieldCellName)
        headerLayout.addWidget(self.checkBoxAutoSave)
        headerLayout.addWidget(self.buttonSaveData)
        headerLayout.addStretch(1)
        headerLayout.addWidget(self.StackLogInOut)
        self.setLayout(headerLayout)
    


    #argument 'e' is of type QMouseEvent.
    def clearCellName(self, e):
        cellName = self.fieldCellName.text()
        if cellName == "Enter Cell Name Here...":
            self.fieldCellName.setText("")
    
    def clearUserName(self, e):
        userName = self.fieldUserName.text()
        if userName == "Username":
            self.fieldUserName.setText("")
    
    def clearSciper(self, e):
        sciper = self.fieldUserSciper.text()
        if sciper == "Sciper":
            self.fieldUserSciper.setText("")

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

    def logOut(self):
        self.signal_log_out.emit()
        self.setHardwareActive(False)
        self.buttonInitialize.setEnabled(False)
        self.fieldCellName.setEnabled(False)
        self.checkBoxAutoSave.setEnabled(False)
        self.buttonSaveData.setEnabled(False)
        self.cellSizeWidget.setEnabled(False)
        self.ButtonResetToDefault.setEnabled(False)
        self.IVResultsWidget.setEnabled(False)
        self.clearPlotIV()
        self.clearPlotConstantV()
        self.clearPlotConstantI()
        self.clearPlotMPP()
        self.clearPlotMPPIV()
        self.clearPlotCalibration()
        self.curve_valid = False
        self.StackLogInOut.setCurrentIndex(0)
        # should call set all fields to default from the application logic after receiving logout signal
        # cannot call this here as we need to be sure the application is done saving the config file
        # before clearing the current values from all the fields.
        #self.setAllFieldsToDefault()
    
    # this function sends login details down to the application logic
    # application logic should call logInValid() if the username/pwd combo is good.
    def logIn(self):
        username = self.fieldUserName.text()
        userSciper = self.fieldUserSciper.text()
        logInValid = False
        self.signal_log_in.emit(username,userSciper)  