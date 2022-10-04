from abc import abstractmethod
from typing import Tuple, Union

import numpy as np

from .hardware_base import HardwareBase

"""
Value that indicates the endpoint of a range.
If `None`, indicates no limit.
"""
RangeValue = Union[float, None]


class SMU(HardwareBase):
	"""
	Base class providing a common API for source meter units (SMUs).
	"""
	def __init__(self, emulate: bool = False):
		"""
		:param emualte: Run in emulation mode. [Default: False]
		"""
		super().__init__(emulate=emulate)

	@property
	@abstractmethod
	def current_range(self) -> Tuple[RangeValue, RangeValue]:
		"""
		:returns: Min and max current values.
		"""
		raise NotImplementedError()

	@property
	@abstractmethod
	def voltage_range(self) -> Tuple[RangeValue, RangeValue]:
		"""
		:returns: Min and max voltage values.
		"""
		raise NotImplementedError()

	@abstractmethod
	def set_voltage(
		self,
		voltage: float
	):
		"""
		Sets the applied voltage.

		:param voltage: Desired voltage.
		"""
		raise NotImplementedError()

	@abstractmethod
	def set_current(
		self,
		current: float
	):
		"""
		Sets the applied current.

		:param current: Desired current.
		"""
		raise NotImplementedError()

	@abstractmethod
	def enable_output(self):
		"""
		Enable output.
		"""
		raise NotImplementedError()

	@abstractmethod
	def disable_output(self):
		"""
		Disable output.
		"""
		raise NotImplementedError()

	@abstractmethod
	def measure_voltage(self) -> float:
		"""
		Measure the voltage.

		:returns: Measured voltage.
		"""
		raise NotImplementedError()

	@abstractmethod
	def measure_current(self) -> float:
		"""
		Measure the current.

		:returns: Measured current.
		"""
		raise NotImplementedError()

	@abstractmethod
	def measure_iv_curve(
		self,
		start: float,
		stop: float,
		step: float,
		rate: float,
	) -> np.array:
		"""
		Measure an IV curve.

		:param start: Start voltage.
		:param stop: Stop voltage.
		:param step: Absolute voltage step size.
		:param rate: Scan rate.
		:returns: numpy.array of measured values.  
		"""
		raise NotImplementedError()

	@abstractmethod
	def measure_iv_point_by_point(
		self,
		start: float,
		stop: float,
		step: float,
		rate: float
	) -> np.array:
		"""
		Measure an IV curve.

		:param start: Start voltage.
		:param stop: Stop voltage.
		:param step: Absolute voltage step size.
		:param rate: Scan rate.
		:returns: numpy.array of measured values.  
		"""
		raise NotImplementedError()

	@abstractmethod
	def measure_chronopotentiometry(
		self,
		current: float,
		time: float
	) -> np.array:
		"""
		Perform a chronopotentiometry experiment.

		:param current: Set point current.
		:param time: Run time.
		:returns: numpy.array of measured values.  
		"""
		raise NotImplementedError()

	@abstractmethod
	def measure_chronoampometry(
		self,
		voltage: float,
		time: float
	) -> np.array:
		"""
		Perform a chronoampometry experiment.

		:param voltage: Set point voltage.
		:param time: Run time.
		:returns: numpy.array of measured values.  
		"""
		raise NotImplementedError()
