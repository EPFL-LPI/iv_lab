from PyQt5.QtWidgets import (
	QDialog,
	QPushButton,
	QGridLayout,
	QLabel,
	QLineEdit,
	QComboBox,
	QVBoxLayout,
	QHBoxLayout,
	QScrollArea,
	QFormLayout,
	QMessageBox,
	QWidget
)

from iv_lab_controller import authentication as auth
from iv_lab_controller.user import User, Permission

from .. import common


class UsersDialog(QDialog):
	"""
	Dialog to allow user editing.
	"""
	def __init__(self):
		super().__init__()

		self.users = auth.user_list()
		self.lo_users = QScrollArea()
		self._wgt_users = None

		self.setWindowTitle('Users')
		self.init_ui()
		self.register_connections()

	def init_ui(self):
		# users
		self.wgt_users = self._create_users_list()

		# ctrls
		self.btn_add = QPushButton('Add')
		self.btn_accept = QPushButton('Save')
		self.btn_reject = QPushButton('Cancel')

		lo_ctrls = QHBoxLayout()
		lo_ctrls.addWidget(self.btn_add)
		lo_ctrls.addStretch()
		lo_ctrls.addWidget(self.btn_reject)
		lo_ctrls.addWidget(self.btn_accept)

		# main
		lo_main = QVBoxLayout()
		lo_main.addWidget(self.lo_users)
		lo_main.addLayout(lo_ctrls)
		self.setLayout(lo_main)

	def _create_users_list(self) -> QGridLayout:
		"""
		Create the users list.
		"""
		# users
		frm_users = QGridLayout()
		frm_users.addWidget(QLabel('Username'), 0, 0)
		frm_users.addWidget(QLabel('Permissions'), 0, 1)
		frm_users.addWidget(QLabel('Pwd Reset'), 0, 2)
		frm_users.addWidget(QLabel('Delete User'), 0, 3)

		for row_i, user in enumerate(self.users):
			row = row_i + 1

			lbl_uname = QLabel(user.username)
			
			cb_permissions = QComboBox()
			active_perm = 0
			for ind, perm in enumerate(Permission):
				cb_permissions.addItem(perm.value, perm.name)
				if perm in user.permissions:
					active_perm = ind

			cb_permissions.setCurrentIndex(active_perm)

			btn_pwd_reset = QPushButton('Reset')
			btn_pwd_reset.clicked.connect(lambda: self.reset_password(user))

			btn_delete_user = QPushButton('X')
			btn_delete_user.clicked.connect(lambda: self.delete_user(user))

			frm_users.addWidget(lbl_uname, row, 0)
			frm_users.addWidget(cb_permissions, row, 1)
			frm_users.addWidget(btn_pwd_reset, row, 2)
			frm_users.addWidget(btn_delete_user, row, 3)

		wgt_users = QWidget()
		wgt_users.setLayout(frm_users)
		return wgt_users
		
	@property
	def wgt_users(self) -> QWidget:
		"""
		:returns: Widget containing the users list.
		"""
		return self._wgt_users

	@wgt_users.setter
	def wgt_users(self, wgt: QWidget):
		"""
		Updates the users widget.
		"""
		self._wgt_users = wgt
		self.lo_users.setWidget(self.wgt_users)

	def register_connections(self):
		self.btn_add.clicked.connect(self.add_user)
		self.btn_accept.clicked.connect(self.save_users)
		self.btn_reject.clicked.connect(self.reject)

	def add_user(self):
		"""
		Add a user.
		"""
		dlg_add_user = AddUserDialog(parent=self)

		def _add_user():
			user = dlg_add_user.value
			self.users.append(user)
			self.wgt_users = self._create_users_list()

		dlg_add_user.accepted.connect(_add_user)
		dlg_add_user.exec()

	def delete_user(self, user: User):
		"""
		Delete a user.

		:param user: User to delete.
		"""
		self.users.remove(user)
		self.wgt_users = self._create_users_list()

	def reset_password(self, user: User):
		"""
		Reset a user's password.

		:param user: User to reset the password of.
		"""
		dlg_pwd = AddUserDialog(parent=self)

		def _set_password():
			pwd = dlg_pwd.value
			user.password = pwd
			self.save_users()

		dlg_pwd.accepted.connect(_set_password)
		dlg_pwd.exec()

	def save_users(self):
		"""
		Persist users to file.
		"""
		try:
			auth.save_users(self.users)
		
		except Exception as err:
			common.show_message_box(
				'Error saving users',
				f'An error occurred when updating the users list\n{err}',
				icon=QMessageBox.Critical
			)

			self.reject()

		else:
			self.accept()



class AddUserDialog(QDialog):
	"""
	Dialog for adding a user.
	"""

	def __init__(self, parent=None):
		super().__init__(parent)

		self.setWindowTitle('Add User')
		self.init_ui()
		self.register_connections()

	def init_ui(self):
		self.in_username = QLineEdit()
		self.in_password = QLineEdit()
		self.cb_permissions = QComboBox()
		for perm in Permission:
				self.cb_permissions.addItem(perm.value, perm)

		lo_form = QFormLayout()
		lo_form.addRow('Username', self.in_username)
		lo_form.addRow('Password', self.in_password)
		lo_form.addRow('Permissions', self.cb_permissions)

		# ctrls
		self.btn_accept = QPushButton('Save')
		self.btn_reject = QPushButton('Cancel')

		lo_ctrls = QHBoxLayout()
		lo_ctrls.addWidget(self.btn_reject)
		lo_ctrls.addWidget(self.btn_accept)

		# main
		lo_main = QVBoxLayout()
		lo_main.addLayout(lo_form)
		lo_main.addLayout(lo_ctrls)
		self.setLayout(lo_main)

	def register_connections(self):
		self.btn_accept.clicked.connect(self.accept)
		self.btn_reject.clicked.connect(self.reject)

	@property
	def value(self) -> User:
		"""
		:returns: User.
		"""
		uname = self.in_username.text()
		pwd = self.in_password.text()
		perms = {self.cb_permissions.currentData()}

		return User(uname, password=pwd, permissions=perms)


class PasswordResetDialog(QDialog):
	"""
	Dialog for resetting a password.
	"""
	def __init__(self, parent=None):
		super().__init__(parent)

		self.setWindowTitle('Reset Password')
		self.init_ui()
		self.register_connections()

	def init_ui(self):
		self.in_password = QLineEdit()

		lo_form = QFormLayout()
		lo_form.addRow('New password', self.in_password)

		# ctrls
		self.btn_accept = QPushButton('Save')
		self.btn_reject = QPushButton('Cancel')

		lo_ctrls = QHBoxLayout()
		lo_ctrls.addWidget(self.btn_reject)
		lo_ctrls.addWidget(self.btn_accept)

		# main
		lo_main = QVBoxLayout()
		lo_main.addLayout(lo_form)
		lo_main.addLayout(lo_ctrls)
		self.setLayout(lo_main)

	def register_connections(self):
		self.btn_accept.clicked.connect(self.accept)
		self.btn_reject.clicked.connect(self.reject)

	@property
	def value(self) -> str:
		"""
		:returns: New password.
		"""
		return self.in_password.text()
	