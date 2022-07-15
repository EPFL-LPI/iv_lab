"""
User functionality.
"""
from typing import Union, Iterable, List
from enum import Enum


class Permission(Enum):
	Basic = 'basic'
	Admin = 'admin'


class User:
	"""
	Represents a user.
	"""
	def __init__(
		self,
		username: str,
		password: Union[str, None] = None,
		permissions: Iterable[Permission] = {Permission.Basic}
	):
		"""
		:param username: Username.
		:param password: Password. [Default: None]
		:param  permissions: Set of Permissions. [Default: {Permission.Basic}]
		"""
		self.username = username
		self.password = password

		permissions = set(map(Permission, permissions))
		self.permissions = permissions

	def __repr__(self) -> str:
		"""
		:returns: String representation of the user.
		"""
		u = {
			'username': self.username,
			'password': self.password,
			'permissions': self.permissions
		}

		return str(u)