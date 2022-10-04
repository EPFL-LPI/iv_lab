from abc import ABC
from datetime import datetime


class SystemParameters(ABC):
	"""
	Parameters describing the IV system.
	"""
	@property
	def name(self) -> str:
		"""
		:returns: IV system's name.
		"""
		return self._name
	
	@property
	def reference_current(self) -> float:
		"""
		:returns: 1 sun reference current.
		"""
		return self._reference_current
	
	@property
	def calibration_date(self) -> datetime:
		"""
		:returns: Date time of last calibration.
		"""
		return self._calibration_date
