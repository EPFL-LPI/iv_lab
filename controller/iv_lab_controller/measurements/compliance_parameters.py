from typing import Union

from pymeasure.experiment.parameters import FloatParameter

from ..base_classes.measurement_parameters import MeasurementParameters


# @todo: Create correct parameters, currently placeholder
class ComplianceParameters(MeasurementParameters):
	"""
	Parameters for measurement compliance.
	"""
	def __init__(self):
		self._current_limit: Union[FloatParameter, None] = None
		self._voltage_limit: Union[FloatParameter, None] = None

	@property
	def current_limit(self) -> Union[FloatParameter, None]:
		"""
		:returns: Current limit
		"""
		return self._current_limit
	
	@current_limit.setter
	def current_limit(self, limit: Union[FloatParameter, float, None]):
		"""
		:param limit: Current limit to set.
		"""
		if isinstance(limit, float):
			param = FloatParameter('current_limit', units='A', minimum=0)
			param.value = limit

		else:
			param = limit

		self._current_limit = param

	@property
	def voltage_limit(self) -> Union[FloatParameter, None]:
		"""
		:returns: Voltage limit
		"""
		return self._voltage_limit
	
	@voltage_limit.setter
	def voltage_limit(self, limit: Union[FloatParameter, float, None]):
		"""
		:param limit: Voltage limit to set.
		"""
		if isinstance(limit, float):
			param = FloatParameter('voltage_limit', units='V', minimum=0)
			param.value = limit

		else:
			param = limit

		self._voltage_limit = param

	def validate(self) -> bool:
		"""
		:returns: True is all parameters are valid. Otherwise raises an exception.
		:raises: If a parameter is invalid.
		"""
		# always valid
		return True
