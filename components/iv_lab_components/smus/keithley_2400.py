from typing import Tuple

from pymeasure.instruments.keithley.keithley2400 import Keithley2400 as Keithley2400Base
from pymeasure.adapters import Adapter

from iv_lab_controller.base_classes.smu import SMU, RangeValue


class Keithley2400(SMU, Keithley2400Base):
	def __init__(self, adapter: Adapter, **kwargs):
		Keithley2400Base.__init__(self, adapter, **kwargs)

	@property
	def current_range(self) -> Tuple[RangeValue, RangeValue]:
		"""
		:returns: Min and max current values.
		"""
		curr_lim = self.compliance_current 
		return (-curr_lim, curr_lim)

	@property
	def voltage_range(self) -> Tuple[RangeValue, RangeValue]:
		"""
		:returns: Min and max voltage values.
		"""
		volt_lim = self.compliance_voltage 
		return (-volt_lim, volt_lim)

	def set_voltage(
		self,
		voltage: float
	):
		"""
		Sets the applied voltage.

		:param voltage: Desired voltage.
		"""
		self.source_voltage = voltage

	def set_current(
		self,
		current: float
	):
		"""
		Sets the applied current.

		:param current: Desired current.
		"""
		self.source_current = current

	def enable_output(self):
		"""
		Enable output.
		"""
		self.enable_source()

	def disable_output(self):
		"""
		Disable output.
		"""
		self.disable_source()

	def measure_voltage(self) -> float:
		"""
		Measure the voltage.

		:returns: Measured voltage.
		"""
		return self.voltage

	def measure_current(self) -> float:
		"""
		Measure the current.

		:returns: Measured current.
		"""
		return self.current

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