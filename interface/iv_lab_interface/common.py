import logging
import inspect
from typing import Union

from PyQt6.QtWidgets import QMessageBox

from iv_lab_controller import Store


logger = logging.getLogger('iv_lab')


def show_message_box(
    title: str,
    message: str,
    info: str = '',
    icon: QMessageBox.Icon = QMessageBox.Icon.NoIcon
):
    """
    Shows a nonmodal message box.

    :param title: Title of the box.
    :param message: Message content.
    :param info: Information text. [Default: '']
    :param icon: Box icon. [Default: QMessageBox.Icon.NoIcon]
    """
    msg = QMessageBox()
    msg.setIcon(icon)
    msg.setText(message)
    msg.setInformativeText(info)
    msg.setWindowTitle(title)

    logger.debug('[message box] %s - %s - %s', title, message, info)
    msg.exec()


def debug(err: Exception, msg: Union[str, None] = None):
    """
    Logs the error at DEBUG level.

    :param err: The exception to log.
    :param msg: Message to insert before the error text.
    Separated by a line break.
    """
    # get stack trace info
    preamble = ''
    try:
        curr_frame = inspect.currentframe()
        caller_frame = inspect.getouterframes(curr_frame)[1]
        frame_info = inspect.getframeinfo(caller_frame)

    except Exception:
        # ignore stack trace info
        pass

    else:
        preamble = f'[{frame_info.filename}@{frame_info.lineno} ({frame_info.function})]'

    out = preamble
    if msg is not None:
        out += f' {msg}\n'

    out += f'{err}'
    logger.debug(out)
