import os

from PyQt5.Qt import QDir
from PyQt5.QtCore import QSettings
from PyQt5.QtWidgets import (
	QDialog,
	QPushButton,
	QGridLayout,
	QLabel,
	QVBoxLayout,
	QHBoxLayout,
	QMessageBox,
	QListWidget,
	QFileDialog
)

from iv_lab_controller import common as ctrl

from .. import common


class SystemsDialog(QDialog):
	"""
	Dialog to set the system.
	"""
	def __init__(self):
		super().__init__()

		self.init_ui()
		self.register_connections()

	def init_ui(self):
		# systems dir
		self.lbl_systems_dir = QLabel(self.systems_dir)
		self.btn_set_dir = QPushButton('Change')

		lo_systems_dir = QHBoxLayout()
		lo_systems_dir.addWidget(QLabel('Systems Directory:'))
		lo_systems_dir.addWidget(self.lbl_systems_dir)
		lo_systems_dir.addWidget(self.btn_set_dir)

		# sytems
		self.wgt_systems = QListWidget()
		self.update_systems_list()

		# main
		lo_main = QVBoxLayout()
		lo_main.addLayout(lo_systems_dir)
		lo_main.addWidget(self.wgt_systems)
		self.setLayout(lo_main)

	def register_connections(self):
		self.btn_set_dir.clicked.connect(self.set_systems_directory)
		self.wgt_systems.itemSelectionChanged.connect(self.set_system_file)

	def update_systems_list(self):
		"""
		Update list of the systems in the systems directory.
		"""
		if not os.path.isdir(self.systems_dir):
			common.show_message_box(
				'Systems directory does not exists',
				'The current systems directory does not exist.\n'
				+ 'Please create a directory at\n'
				+ self.systems_dir
				+ '\nto conintue.',
				icon=QMessageBox.Critical
			)
			return

		systems_dir = self.systems_dir
		files = [
			f for f in os.listdir(systems_dir)
			if os.path.isfile(os.path.join(systems_dir, f))
		]
		
		sys_names = list(map(lambda f: os.path.splitext(f)[0], files))
		self.wgt_systems.clear()
		self.wgt_systems.addItems(sys_names)

		# set current to selected
		current_sys_path = ctrl.system_path()
		for row, name in enumerate(sys_names):
			sys_path = os.path.join(systems_dir, f'{name}.py')
			if sys_path == current_sys_path:
				self.wgt_systems.setCurrentRow(row)
				break

	def set_systems_directory(self) -> str:
		"""
		Allow user to select the systems directory.

		:returns: Path to selected directory.
		"""
		sys_dir = QFileDialog.getExistingDirectory()
		in_systems_dir.accept.connect(lambda: self.set_systems_directory(sys_dir))

	def save_systems_directory(self, sys_dir: str):
		"""
		Set the systems directory to the given path.
		"""
		try:
			ctrl.set_application_systems_directory(sys_dir)

		except Exception as err:
			common.show_message_box(
				'Could not save systems directory',
				f'An error occurred when save the new systems diretory\n{err}',
				icon=QMessageBox.Critical
			)
			return

		self.lbl_systems_dir.setText(self.systems_dir)
		self.update_systems_list()

	def set_system_file(self):
		"""
		Set the path to the system file.
		"""
		sys_name = self.wgt_systems.selectedItems()
		if len(sys_name) != 1:
			common.show_message_box(
				'Invalid system selection',
				'Must select one and only one system.',
				icon=QMessageBox.Critical
			)
			return

		sys_name = sys_name[0].text()
		sys_path = os.path.join(self.systems_dir, f'{sys_name}.py')
		try:
			ctrl.set_system_path(sys_path)

		except Exception as err:
			common.show_message_box(
				'Error saving system',
				f'An error occurred when saving the system.\n{err}',
				icon=QMessageBox.Critical
			)

	@property
	def systems_dir(self) -> str:
		"""
		:returns: Path the current systems directory.
		"""
		return ctrl.application_systems_directory()
	