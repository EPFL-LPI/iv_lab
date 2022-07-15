from datetime import datetime

from iv_lab_controller.base_classes.iv_system_parameters import IVSystemParameters


class MockIVSystemParameters(IVSystemParameters):
	"""
	Mock IV system parameters used for testing.
	"""
	def __init__(self):
		self._name = 'mov iv system parameters'
		self._reference_current = 1.0
		self._calibration_date = datetime.now()