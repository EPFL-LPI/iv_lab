"""
User functionality.
"""
import json
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
		u = self.todict()
		return str(u)

	def todict(self) -> dict:
		"""
		:returns: Dictionary represetnation of the user.
		"""
		return {
			'username': self.username,
			'password': self.password,
			'permissions': self.permissions
		}


class UserJSONEncoder(json.JSONEncoder):
	def default(self, o):
		"""
		:returns: Dictionary representation of the User for serialization.
		"""
		if isinstance(o, User):
			user = o.todict()
			user['permissions'] = list(map(lambda p: p.value, o.permissions))
			return user

		return super().default(o)