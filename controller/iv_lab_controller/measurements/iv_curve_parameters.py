from typing import Union

from pymeasure.experiment.parameters import (
	BooleanParameter,
	FloatParameter,
	IntegerParameter
)

from ..base_classes.measurement_parameters import MeasurementParameters
from .types import IVSweepDirection


class IVCurveParameters(MeasurementParameters):
	"""
	Parameters for an IV curve measurement.
	"""
	def __init__(self):
		self._use_automatic_limits: Union[BooleanParameter, None] = None
		self._current_limit: Union[FloatParameter, None] = None
		self._min_voltage: Union[FloatParameter, None] = None
		self._max_voltage: Union[FloatParameter, None] = None
		self._voltage_step: Union[FloatParameter, None] = None
		self._sweep_rate: Union[FloatParameter, None] = None
		self._stabilization_time: Union[FloatParameter, None] = None
		self._direction: Union[IntegerParameter, None] = None

	@property
	def use_automatic_limits(self) -> Union[BooleanParameter, None]:
		"""
		:returns: Parameter representing use of automatic voltage limits.
		"""
		return self._use_automatic_limits
	
	@use_automatic_limits.setter
	def use_automatic_limits(self, use_auto: Union[BooleanParameter, bool, None]):
		"""
		:param use_auto: Whether to us automatic voltage limits or not.
		"""
		if isinstance(use_auto, bool):
			param = BooleanParameter('use_automatic_limits')
			param.value = use_auto
			
		else:
			param = use_auto

		self._use_automatic_limits = param

	@property
	def current_limit(self) -> Union[FloatParameter, None]:
		"""
		:returns: Current limit when automatic voltage limits are used.
		"""
		return self._current_limit
	
	@current_limit.setter
	def current_limit(self, limit: Union[FloatParameter, float, None]):
		"""
		:param limit: Current limit when automatic voltage limits are used.
		"""
		if isinstance(limit, float):
			param = FloatParameter('current_limit', units='mA/cm^2')
			param.value = limit

		else:
			param = limit

		self._current_limit = param

	@property
	def min_voltage(self) -> Union[FloatParameter, None]:
		"""
		:returns: Minimum voltage of the scan.
		"""
		return self._min_voltage
	
	@min_voltage.setter
	def min_voltage(self, v: Union[FloatParameter, float, None]):
		"""
		:param v: Minimum voltage for the scan.
		"""
		if isinstance(v, float):
			param = FloatParameter('min_voltage', units='V')
			param.value = v

		else:
			param = v

		self._min_voltage = param

	@property
	def max_voltage(self) -> Union[FloatParameter, None]:
		"""
		:returns: Maximum voltage of the scan.
		"""
		return self._max_voltage
	
	@max_voltage.setter
	def max_voltage(self, v: Union[FloatParameter, float, None]):
		"""
		:param v: Maximum voltage for the scan.
		"""
		if isinstance(v, float):
			param = FloatParameter('max_voltage', units='V')
			param.value = v

		else:
			param = v

		self._max_voltage = param

	@property
	def voltage_step(self) -> Union[FloatParameter, None]:
		"""
		:returns: Voltage step of the scan.
		"""
		return self._voltage_step
	
	@voltage_step.setter
	def voltage_step(self, step: Union[FloatParameter, float, None]):
		"""
		:param v: Voltage step for the scan.
		"""
		if isinstance(step, float):
			param = FloatParameter('voltage_step', units='V', minimum=0)
			param.value = step

		else:
			param = step

		self._voltage_step = param

	@property
	def sweep_rate(self) -> Union[FloatParameter, None]:
		"""
		:returns: Sweep rate of the scan.
		"""
		return self._sweep_rate
	
	@sweep_rate.setter
	def sweep_rate(self, rate: Union[FloatParameter, float, None]):
		"""
		:param v: Sweep rate for the scan.
		"""
		if isinstance(rate, float):
			param = FloatParameter('sweep_rate', units='V/s', minimum=0)
			param.value = rate

		else:
			param = step

		self._sweep_rate = param

	@property
	def stabilization_time(self) -> Union[FloatParameter, None]:
		"""
		:returns: Stabilization time of the scan.
		"""
		return self._stabilization_time
	
	@stabilization_time.setter
	def stabilization_time(self, time: Union[FloatParameter, float, None]):
		"""
		:param time: Stabilization time for the scan.
		"""
		if isinstance(time, float):
			param = FloatParameter('stabilization_time', units='s', minimum=0)
			param.value = time

		else:
			param = time

		self._stabilization_time = param

	@property
	def direction(self) -> Union[IntegerParameter, None]:
		"""
		:returns: Sweep direction of the scan.
		"""
		return self._direction
	
	@direction.setter
	def direction(self, direction: Union[FloatParameter, IVSweepDirection, int, None]):
		"""
		:param direction: Sweep direction for the scan.
		"""
		if isinstance(direction, IVSweepDirection):
			direction = 1 if ( direction is IVSweepDirection.Forward ) else -1

		if isinstance(direction, int):
			param = IntegerParameter('direction', minimum=-1, maximum=1)
			param.value = direction

		else:
			param = step

		self._direction = param

	def __iter__(self):
		yield self.use_automatic_limits
		yield self.current_limit
		yield self.min_voltage
		yield self.max_voltage
		yield self.voltage_step
		yield self.sweep_rate
		yield self.stabilization_time
		yield self.direction

	def validate(self) -> bool:
		"""
		:returns: True is all parameters are valid. Otherwise raises an exception.
		:raises: If a parameter is invalid.
		"""
		if (
			(self.use_automatic_limits is not None)
			and (self.use_automatic_limits.value)
		):
			# min and max voltage must be None
			if (
				(self.min_voltage is not None)
				or (self.max_voltage is not None)
			):
				raise ValueError('Voltage limits can not be set when using automatic limits.')

		else:
			if (
				(self.min_voltage is None)
				or (self.max_voltage is None)
			):
				raise ValueError('Both voltage limits must be set.')

			if (self.min_voltage.value >= self.max_voltage.value):
				raise ValueError('Minimum voltage limit must be less than the maximum limit.')

		# valid
		return True