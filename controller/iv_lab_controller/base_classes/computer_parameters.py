from abc import ABC


class ComputerParameters(ABC):
	"""
	Parameters describing the computer system.
	"""
	@property
	def name(self) -> str:
		"""
		:returns: Name of the computer system.
		"""
		return self._name
	
	@property
	def os(self) -> str:
		"""
		:returns: Name of the computer's operating system.
		"""
		return self._os
	
	@property
	def data_path(self) -> str:
		"""
		:returns: Path of the data folder.
		"""
		return self._data_path