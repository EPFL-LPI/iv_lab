import logging
from enum import Enum
from json import JSONDecodeError

from PyQt6.QtWidgets import (
    QLabel,
    QPushButton,
    QLineEdit,
    QHBoxLayout,
    QStackedWidget,
    QMessageBox,
    QWidget,
)

from iv_lab_controller.user import User
from iv_lab_controller.store import Store, Observer
from iv_lab_controller.types import RunnerState
import iv_lab_controller.authentication as auth_ctrl

from .. import common


# logger 
logger = logging.getLogger('iv_lab')


class Actions(Enum):
    Login = 0
    Logout = 1


class AuthenticationWidget(QStackedWidget):
    """
    Handles logging users in and out.
    """
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.register_connections()
        self.init_observers()

    def init_ui(self):
        # login
        self.in_username = QLineEdit()
        self.in_username.setPlaceholderText("Username")
        self.in_username.setMinimumWidth(100)

        self.in_password = QLineEdit()
        self.in_password.setPlaceholderText("Password")
        self.in_password.setMinimumWidth(100)

        self.btn_log_in = QPushButton("Log In")
        
        lo_log_in = QHBoxLayout()
        lo_log_in.addWidget(self.in_username)
        lo_log_in.addWidget(self.in_password)
        lo_log_in.addWidget(self.btn_log_in)

        self.wgt_log_in = QWidget()
        self.wgt_log_in.setLayout(lo_log_in)
        
        # logout
        lbl_username_title = QLabel("Logged in as:")
        self.lbl_username = QLabel("guest")
        self.btn_log_out = QPushButton("Log Out")
        
        lo_log_out = QHBoxLayout()
        lo_log_out.addWidget(lbl_username_title)
        lo_log_out.addWidget(self.lbl_username)
        lo_log_out.addWidget(self.btn_log_out)

        self.wgt_log_out = QWidget()
        self.wgt_log_out.setLayout(lo_log_out)
        
        # main
        self.addWidget(self.wgt_log_in)
        self.addWidget(self.wgt_log_out)
        self.setCurrentIndex(Actions.Login.value)

    def register_connections(self):
        self.in_password.returnPressed.connect(self.log_in)
        self.btn_log_in.clicked.connect(self.log_in)
        self.btn_log_out.clicked.connect(self.log_out)

    def init_observers(self):
        # user
        def user_changed(user: User, o_user: User):
            if user is None:
                # show login
                self.in_username.setFocus()
                self.setCurrentIndex(Actions.Login.value)

            else:
                # show logout
                self.setCurrentIndex(Actions.Logout.value)

        user_observer = Observer(changed=user_changed)
        Store.subscribe('user', user_observer)

        # runner state
        def runner_state_changed(state: RunnerState, o_state: RunnerState):
            if state is RunnerState.Standby:
                self.setEnabled(True)
        
            elif state is RunnerState.Running:
                self.setEnabled(False)

            if state is RunnerState.Aborting:
                self.setEnabled(False)

        runner_state_observer = Observer(changed=runner_state_changed)
        Store.subscribe('experiment_state', runner_state_observer)

    def log_in(self):
        """
        Attempt to log in a user.
        If successful update controls, otherwise display error message.
        """
        username = self.in_username.text()
        password = self.in_password.text()

        try:
            user = auth_ctrl.authenticate(username, password)

        except FileNotFoundError as err:
            common.debug(err)
            common.show_message_box(
                'Users list missing',
                'Could not load users list. Please contact an administrator.',
                icon=QMessageBox.Icon.Critical
            )
            return

        except JSONDecodeError as err:
            common.debug(err)
            common.show_message_box(
                'Users list corrupt',
                'Could not load users list. Please contact an administrator.',
                icon=QMessageBox.Icon.Critical
            )
            return

        if user is None:
            # invalid user
            logger.info(f'Invalid login attempt for username `{username}`')
            common.show_message_box(
                'Invalid credentials',
                'Invalid username or password.',
                icon=QMessageBox.Icon.Critical
            )
            return

        # successful log in
        self.set_username(user.username)
        Store.set('status_msg', f'Logged in as {user.username}')
        Store.set('user', user)

        # clear credential fields
        self.in_username.clear()
        self.in_password.clear()

        # log activity
        logger.info(f'User `{user.username}` logged in')

    def log_out(self):
        user = Store.get('user')

        Store.set('status_msg', 'Logged out')
        Store.set('user', None)

        # log activity
        logger.info(f'User `{user.username}` logged out')

    def set_username(self, username: str):
        self.lbl_username.setText(username)
