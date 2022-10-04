"""
Common functions used throughout the application.
"""
import os
from PyQt6.QtCore import QSettings, QStandardPaths


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
