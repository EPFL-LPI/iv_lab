from datetime import datetime

from iv_lab_controller.base_classes.system_parameters import SystemParameters


class MockSystemParameters(SystemParameters):
	"""
	Mock system parameters used for testing.
	"""
	def __init__(self):
		self._name = 'mock system parameters'
		self._reference_current = 1.0
		self._calibration_date = datetime.now()
