"""
Common functions used throughout the application.
"""
import os
from PyQt5.QtCore import QStandardPaths 


def app_data_folder() -> str:
	"""
	:returns: Path to the directory where application data should be stored.
	"""
	return QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)


def default_system_parameters_file() -> str:
	"""
	:returns: Path to the default file to store SystemParameters
	"""
	return os.path.join(app_data_folder(), 'system_settings.json')
