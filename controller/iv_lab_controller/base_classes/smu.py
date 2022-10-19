from abc import abstractmethod
from enum import Enum
from typing import Union

from .hardware_base import HardwareBase


RangeValue = Union[float, Enum]
"""
Value representing a voltage or current range.
"""


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
    def current_range(self) -> RangeValue:
        """
        :returns: Current measurement range.
        """
        raise NotImplementedError()

    @current_range.setter
    @abstractmethod
    def current_range(self, rng: RangeValue):
        """
        Set the SMU's current range.

        :param rng: Current measurement range.
        """
        raise NotImplementedError()

    @property
    @abstractmethod
    def voltage_range(self) -> RangeValue:
        """
        :returns: Voltage measurement range.
        """
        raise NotImplementedError()

    @voltage_range.setter
    @abstractmethod
    def voltage_range(self, rng: RangeValue):
        """
        Set the SMU's voltage range.

        :param rng: Voltage measurement range.
        """
        raise NotImplementedError()

    @property
    @abstractmethod
    def compliance_current(self) -> float:
        """
        :returns: Compliance current.
        """
        raise NotImplementedError()

    @compliance_current.setter
    @abstractmethod
    def compliance_current(self, i: float):
        """
        Sets the compliance current.

        :param: Desired compliance current.
        """
        raise NotImplementedError()

    @property
    @abstractmethod
    def compliance_voltage(self) -> float:
        """
        :returns: Compliance voltage.
        """
        raise NotImplementedError()

    @compliance_voltage.setter
    @abstractmethod
    def compliance_voltage(self, v: float):
        """
        Sets the compliance voltage.

        :param v: Desired compliance voltage.
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
    def get_voltage(self) -> float:
        """
        Measure the voltage.

        :returns: Measured voltage.
        """
        raise NotImplementedError()

    @abstractmethod
    def get_current(self) -> float:
        """
        Measure the current.

        :returns: Measured current.
        """
        raise NotImplementedError()
