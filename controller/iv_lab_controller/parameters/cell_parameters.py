from typing import Union

from pymeasure.experiment import FloatParameter

from ..base_classes import ExperimentParameters


class CellParameters(ExperimentParameters):
	"""
	Parameters for a cell.
	"""
	def __init__(self):
		self._cell_area: Union[FloatParameter, None] = None

	@property
	def cell_area(self) -> Union[FloatParameter, None]:
		"""
		:returns: Cell area
		"""
		return self._cell_area
	
	@cell_area.setter
	def cell_area(self, area: Union[FloatParameter, float, None]):
		"""
		:param area: Cell area.
		"""
		if isinstance(area, float):
			param = FloatParameter('cell_area', units='cm^2', minimum=0)
			param.value = area

		else:
			param = area

		self._cell_area = param

	def __iter__(self):
		yield self.cell_area

	def validate(self) -> bool:
		"""
		:returns: True is all parameters are valid. Otherwise raises an exception.
		:raises: If a parameter is invalid.
		"""
		# always valid
		return True
