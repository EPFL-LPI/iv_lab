from PyQt5.QtWidgets import QMessageBox


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