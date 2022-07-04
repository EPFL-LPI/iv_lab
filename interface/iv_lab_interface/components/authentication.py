from json import JSONDecodeError

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import (
    QLabel,
    QPushButton,
    QLineEdit,
    QVBoxLayout,
    QHBoxLayout,
    QStackedWidget,
    QMessageBox,
    QWidget,
)

import iv_lab_controller.authentication as auth_ctrl
from iv_lab_controller.user import User

from .. import common


class AuthenticationWidget(QStackedWidget):
    """
    Handles logging users in and out.
    """
    user_logged_out = pyqtSignal()
    user_authenticated = pyqtSignal(User)

    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        self.panelLogIn = QWidget()
        panelLogInLayout = QHBoxLayout()
        
        self.fieldUserName = QLineEdit()
        self.fieldUserName.setPlaceholderText("Username")
        self.fieldUserName.setMinimumWidth(100)

        self.fieldPassword = QLineEdit()
        self.fieldPassword.setPlaceholderText("Sciper")
        self.fieldPassword.returnPressed.connect(self.logIn)
        self.fieldPassword.setMinimumWidth(100)

        self.buttonLogIn = QPushButton("Log In", self)
        self.buttonLogIn.clicked.connect(self.logIn)
        
        panelLogInLayout.addWidget(self.fieldUserName)
        panelLogInLayout.addWidget(self.fieldPassword)
        panelLogInLayout.addWidget(self.buttonLogIn)
        self.panelLogIn.setLayout(panelLogInLayout)
        #self.panelLogIn.setMaximumHeight(35)
        
        self.panelLogOut = QWidget()
        panelLogOutLayout = QHBoxLayout()
        self.labelLoggedInAs = QLabel("Logged in as:")
        self.labelUserName = QLabel("guest")
        self.buttonLogOut = QPushButton("Log Out",self)
        self.buttonLogOut.clicked.connect(self.logOut)
        
        panelLogOutLayout.addWidget(self.labelLoggedInAs)
        panelLogOutLayout.addWidget(self.labelUserName)
        panelLogOutLayout.addWidget(self.buttonLogOut)
        self.panelLogOut.setLayout(panelLogOutLayout)
        #self.panelLogOut.setMaximumHeight(35)
        
        self.addWidget(self.panelLogIn)
        self.addWidget(self.panelLogOut)
        #self.StackLogInOut.setMaximumHeight(40)
        self.setCurrentIndex(0) # 0 = login, 1 = logout

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
        password = self.fieldPassword.text()

        try:
            user = auth_ctrl.authenticate(username, password)
        
        except FileNotFoundError:
            common.show_message_box(
                'Users list missing',
                'Could not load users list. Please contact an administrator.',
                icon=QMessageBox.Critical
            )
            return

        except JSONDecodeError:
            common.show_message_box(
                'Users list corrupt',
                'Could not load users list. Please contact an administrator.',
                icon=QMessageBox.Critical
            )
            return

        if user is None:
            # invalid user
            common.show_message_box(
                'Invalid credentials',
                'Invalid username or password.',
                icon=QMessageBox.Critical
            )

        else:
            self.user_authenticated.emit(user)  

    def set_username(self, username: str):
        self.labelUserName.setText(username)