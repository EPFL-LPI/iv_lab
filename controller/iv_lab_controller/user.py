"""
User functionality.
"""
from typing import Union, Iterable
from enum import Enum


class Permissions(Enum):
	Basic = 0
	Admin = 1


class User:
	"""
	Represents a user.
	"""
	def __init__(
		self,
		username: str,
		password: Union[str, None] = None,
		permissions: Iterable[Permissions] = {Permissions.Basic}
	):
		"""
		:param username: Username.
		:param password: Password. [Default: None]
		:param  permissions: Iterable of Permissions. [Default: {Permissions.Basic}]
		"""
		self.username = username
		self.password = password
		self.permissions = permissions
