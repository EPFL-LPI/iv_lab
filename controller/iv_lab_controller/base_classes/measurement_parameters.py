from abc import abstractmethod


class MeasurementParameters():
	"""
	Holds parameters for a measurement.
	"""
	@abstractmethod	
	def validate(self) -> bool:
		"""
		:returns: True if all parameters are valid. Otherwise raises an exception.
		:raises: If a parameter is invalid.
		"""
		raise NotImplementedError()