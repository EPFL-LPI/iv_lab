from datetime import datetime


class IVSystemParameters():
	"""
	Parameters describing the IV system.
	"""
	def __init__(
		self,
		name: str,
		reference_current: float,
		calibration_date: datetime
	):
		"""
		:param name: System name.
		:param reference current: 1 sun reference current.
		:param calibration_date: Date time of last calibration.
		"""
		self.name = name
		self.reference_current = reference_current
		self.calibration_date = calibration_date