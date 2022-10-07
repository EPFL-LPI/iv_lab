"""
Common functions used throughout the application.
"""
import os
import time

from PyQt6.QtCore import QSettings, QStandardPaths

from .user import User


def app_data_folder() -> str:
	"""
	:returns: Path to the directory where application data should be stored.
	"""
	return QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)


def default_system_parameters_file() -> str:
	"""
	:returns: Path to the default file to store SystemParameters
	"""
	return os.path.join(app_data_folder(), 'system_settings.json')


def application_systems_directory() -> str:
	"""
	:returns: Path to the application's system directory.
	"""
	default_path = os.path.join(app_data_folder(), 'systems')
	settings = QSettings()
	return settings.value('systems_directory', default_path, type=str)


def set_application_systems_directory(path: str):
	"""
	Set the application's systems directory path.

	:param path: Path to the desired directory.
	"""
	settings = QSettings()
	settings.setValue('systems_directory', path)


def system_path() -> str:
	"""
	:returns: Path to the currently selected system.
	"""
	settings = QSettings()
	return settings.value('system_file', type=str)


def set_system_path(path: str):
	"""
	Set the path to the currently active system.

	:param path: Path to the system's definition file.
	"""
	settings = QSettings()
	settings.setValue('system_file', path)

def data_directory() -> str:
	"""
	:returns: Path to the default measurement data folder.
	"""
	settings = QSettings()
	default = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DocumentsLocation)
	default = os.path.join(default, 'data')
	return settings.value('data_directory', default, type=str)

def set_data_directory(path: str):
	"""
	Set the default path for measurement data.
	"""
	settings = QSettings()
	settings.setValue('data_directory', path)

def user_data_directory(user: User) -> str:
    """
    :param user: User.
    :returns: Data directory for the given user.
    """
    # @todo: Raise exception instead of defaulting to `anonymous` 
    username = 'anonymous' if not user.username else user.username
    data_dir = data_directory()
    user_dir = os.path.join(data_dir, username)
    user_dir = os.path.normpath(user_dir)

    return user_dir

def user_daily_data_directory(user: User) -> str:
    """
    :param user: User.
    :returns: Data directory for the user's daily experiments.
    """
    day_path = time.strftime('%Y-%m-%d')
    user_dir = user_data_directory(user)
    daily_dir = os.path.join(user_dir, day_path)

    return daily_dir

def get_user_daily_data_directory(user: User) -> str:
    """
    Creates the user's daily data directory, if needed.
    
    :returns: Path of the user's daily data directory.
    """
    daily_dir = user_daily_data_directory(user)
    os.makedirs(daily_dir, exist_ok=True)
    return daily_dir

def unique_file(file: str) -> str:
    """
    Ensures a file name is unique by adding a
    running counter to the end if needed.

    :param file: Path to the file.
    :returns: Unique path of the form `<file_name>[-<index>][.<ext>]`
    """
    base, ext = os.path.splitext(file)
    u_fn = file
    i = 1
    while os.path.exists(u_fn):
        u_fn = f'{base}-{i}{ext}'
        i += 1

    return u_fn
