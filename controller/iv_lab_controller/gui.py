import os
import platform
import subprocess
from typing import Union

from PyQt6.QtWidgets import QFileDialog

from .user import User
from . import common


def open_path(path: str):
    """
    Open a file with its default application.
    See https://stackoverflow.com/a/435669/2961550 for more info.

    :param path: Path to open.
    """
    if platform.system() == 'Darwin':
        # macOS
        subprocess.call(('open', path))

    elif platform.system() == 'Windows':
        # Windows
        os.startfile(path)

    else:
        # linux variants
        subprocess.call(('xdg-open', path))


def get_parameters_save_path(user: Union[User, None] = None) -> str:
    """
    Opens a dialog for the user to select a file path to save a file to.

    :param user: If `None` opens to the app's data directory.
        If provided a user, opens to the user's data directory.
    :returns: Path, or `None` if user cancels.
    """
    dir_path = (
        common.data_directory()
        if user is None else
        common.user_data_directory(user)
    )

    path, _fltr = QFileDialog.getSaveFileName(
        caption='Save system parameters',
        directory=dir_path,
        filter='Parameter files (*.json)'
    )

    # add extension if needed
    if not path.endswith('.json'):
        path += '.json'

    return path


def get_parameters_file_path(user: Union[User, None] = None) -> str:
    """
    Opens a dialog for the user to select a parameters file.

    :param user: If `None` opens to the app's data directory.
        If provided a user, opens to the user's data directory.
    :returns: Path, or `None` if user cancels.
    """
    dir_path = (
        common.data_directory()
        if user is None else
        common.user_data_directory(user)
    )

    path, _fltr = QFileDialog.getOpenFileName(
        caption='Load system parameters',
        directory=dir_path,
        filter='Parameter files (*.json)'
    )

    return path
