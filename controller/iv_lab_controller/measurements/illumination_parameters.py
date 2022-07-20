from typing import Union

from pymeasure.experiment.parameters import FloatParameter, BooleanParameter

from ..base_classes.measurement_parameters import MeasurementParameters


class IlluminationParameters(MeasurementParameters):
	"""
	Parameters for a cell.
	"""
	def __init__(self):
		self._manual: Union[BooleanParameter, None] = BooleanParameter('manual_illumination', default=False)
		self._intensity: Union[FloatParameter, None] = None

	@property
	def manual(self) -> Union[BooleanParameter, None]:
		"""
		:returns: Light intensity manually set.
		"""
		return self._intensity
	
	@manual.setter
	def manual(self, manual: Union[BooleanParameter, float, None]):
		"""
		:param inten: Light intensity manually set.
		"""
		if isinstance(inten, float):
			param = BooelanParameter('manual_illumination')
			param.value = manual

		else:
			param = manual

		self._manual = param

	@property
	def intensity(self) -> Union[FloatParameter, None]:
		"""
		:returns: Desired light intensity.
		"""
		return self._intensity
	
	@intensity.setter
	def intensity(self, inten: Union[FloatParameter, float, None]):
		"""
		:param inten: Desired light intensity.
		"""
		if isinstance(inten, float) or isinstance(inten, int):
			param = FloatParameter('light_intensity', units='suns', minimum=0)
			param.value = inten

		else:
			param = inten

		self._intensity = param

	def __iter__(self):
		yield self.manual
		yield self.intensity

	def validate(self) -> bool:
		"""
		:returns: True is all parameters are valid. Otherwise raises an exception.
		:raises: If a parameter is invalid.
		"""
		# always valid
		return True