from PyQt5.QtWidgets import (
	QMessageBox
)

from iv_lab_controller import common


class ApplicationLocationsDialog(QMessageBox):
	"""
	Dialog showing important application directory and file locations.
	"""
	def __init__(self):
		super().__init__()

		txt = '\n'.join([
			f'Application data folder: {common.app_data_folder()}'
		])

		self.setText(txt)
		self.setWindowTitle('Application Locations')

