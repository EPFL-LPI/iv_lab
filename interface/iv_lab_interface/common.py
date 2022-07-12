from typing import Union

from PyQt5.QtWidgets import (
    QMessageBox,
    QStatusBar
)


def show_message_box(
    title: str,
    message: str,
    info: str = '',
    icon: QMessageBox.Icon = QMessageBox.NoIcon
):
    """
    Shows a nonmodal message box.

    :param title: Title of the box.
    :param message: Message content.
    :param info: Information text. [Default: '']
    :param icon: Box icon. [Default: QMessageBox.NoIcon]
    """
    msg = QMessageBox()
    msg.setIcon(icon)
    msg.setText(message)
    msg.setInformativeText(info)
    msg.setWindowTitle(title)
    msg.exec_()


class StatusBar():
    """
    Singleton class used to hold the applications status bar.
    Used for easy access to the status bar from anywhere in the application.
    Should be initialized with the main wdiget.
    """
    _instance: Union[QStatusBar, None] = None

    def __new__(cls, statusbar: QStatusBar = None) -> 'StatusBar':
        """
        :param statusbar: Status bar to store.
        """
        if (statusbar is None) and (cls._instance is None):
            raise RuntimeError('Status bar has not yet been intialized.')

        if (statusbar is not None) and (cls._instance is not None):
            raise RuntimeError('Status bar is a singleton class and has already been initialized.')

        if cls._instance is None:
            cls._instance = statusbar

        return cls._instance