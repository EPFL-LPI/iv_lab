from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QVBoxLayout,
    QWidget,
)

from iv_lab_controller.user import User

from .components.authentication import AuthenticationWidget


class LoginWidget(QWidget):
    """
    Login widget.
    """
    user_authenticated = pyqtSignal(User)

    def __init__(self):
        super().__init__()

        self.init_window()
        self.init_ui()
        self.register_connections()

    def init_window(self):
        pass

    def init_ui(self):
        wgt_auth = AuthenticationWidget()

        lo_main = QVBoxLayout()
        lo_main.addWidget(wgt_auth)
        self.setLayout(lo_main)

    def register_connections(self):
        pass
