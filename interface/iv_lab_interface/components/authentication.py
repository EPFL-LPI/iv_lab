from json import JSONDecodeError

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
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
        self.fieldPassword.setPlaceholderText("Password")
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

    def logIn(self):
        """
        Attempt to log in a user.
        If successful update controls, otherwise display error message.
        """
        username = self.fieldUserName.text()
        password = self.fieldPassword.text()

        try:
            user = auth_ctrl.authenticate(username, password)
        
        except FileNotFoundError:
            common.show_message_box(
                'Users list missing',
                'Could not load users list. Please contact an administrator.',
                icon=QMessageBox.Icon.Critical
            )
            return

        except JSONDecodeError:
            common.show_message_box(
                'Users list corrupt',
                'Could not load users list. Please contact an administrator.',
                icon=QMessageBox.Icon.Critical
            )
            return

        if user is None:
            # invalid user
            common.show_message_box(
                'Invalid credentials',
                'Invalid username or password.',
                icon=QMessageBox.Icon.Critical
            )
            return

        # successful log in
        self.set_username(user.username)
        self.show_log_out()

        # clear credential fields
        self.fieldUserName.setText('')
        self.fieldPassword.setText('')

        common.StatusBar().showMessage(f'Logged in as {user.username}')
        self.user_authenticated.emit(user)

    def logOut(self):
        self.show_log_in()
        common.StatusBar().showMessage('Logged out')
        self.user_logged_out.emit()

    def set_username(self, username: str):
        self.labelUserName.setText(username)

    def show_log_in(self):
        """
        Shows log in controls.
        """
        self.fieldUserName.setFocus()
        self.setCurrentIndex(0)

    def show_log_out(self):
        """
        Show log out controls.
        """
        self.setCurrentIndex(1)
