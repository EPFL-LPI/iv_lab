from abc import abstractmethod
from typing import Tuple, Union

import numpy as np

from .hardware_base import HardwareBase


RangeValue = Union[float, None]


class SMU(HardwareBase):
	"""
	Base class providing a common API for source meter units (SMUs).
	"""
	def __init__(
		self
	):
		super().__init__()

		self._current_range = (None, None)
		self._voltage_range = (None, None)

	@property
	def current_range(self) -> Tuple[RangeValue, RangeValue]:
		"""
		:returns: Min and max current values.
		"""
		return self._current_range

	@property
	def voltage_range(self) -> Tuple[RangeValue, RangeValue]:
		"""
		:returns: Min and max voltage values.
		"""
		return self._voltage_range

	@staticmethod
	def set_voltage(
		self,
		voltage: float
	):
		"""
		Sets the applied voltage.

		:param voltage: Desired voltage.
		"""
		raise NotImplementedError()

	@staticmethod
	def set_current(
		self,
		current: float
	):
		"""
		Sets the applied current.

		:param current: Desired current.
		"""
		raise NotImplementedError()

	@staticmethod
	def enable_output(self):
		"""
		Enable output.
		"""
		raise NotImplementedError()

	@staticmethod
	def disable_output(self):
		"""
		Disable output.
		"""
		raise NotImplementedError()

	@staticmethod
	def measure_voltage(self) -> float:
		"""
		Measure the voltage.

		:returns: Measured voltage.
		"""
		raise NotImplementedError()

	@staticmethod
	def measure_current(self) -> float:
		"""
		Measure the current.

		:returns: Measured current.
		"""
		raise NotImplementedError()

	@staticmethod
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
		:returns: NumPy.array of measured values.  
		"""
		raise NotImplementedError()

	@staticmethod
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
		:returns: NumPy.array of measured values.  
		"""
		raise NotImplementedError()

	@staticmethod
	def measure_chronovoltometry(
		self,
		current: float,
		time: float
	) -> np.array:
		"""
		Perform a chronovoltometry experiment.

		:param current: Set point current.
		:param time: Run time.
		:returns: NumPy.array of measured values.  
		"""
		raise NotImplementedError()

	@staticmethod
	def measure_chronoampometry(
		self,
		voltage: float,
		time: float
	) -> np.array:
		"""
		Perform a chronoampometry experiment.

		:param voltage: Set point voltage.
		:param time: Run time.
		:returns: NumPy.array of measured values.  
		"""
		raise NotImplementedError()

	@staticmethod
	def measure_chrono_mpp(
		self,
		time: float
	) -> np.array:
		"""
		Measure MPP for a given amount of time.
		
		:param time: Run time.
		:returns: NumPy.array of measured values.  
		"""
		raise NotImplementedError()