import logging
from typing import Tuple, Union

import numpy as np

from iv_lab_controller.base_classes.hardware_base import HardwareBase
from iv_lab_controller.base_classes.smu import SMU, RangeValue


class MockSMU(SMU):
    """
    Mock SMU used for testing.
    """
    @HardwareBase.name.getter
    def name(self) -> str:
        """
        :returns: 'mock smu'.
        """
        return 'mock smu'

    def _connect(self):
        """
        Connect to the SMU.
        """
        logging.debug('connect')

    def _disconnect(self):
        """
        Disconnect from the SMU.
        """
        logging.debug('disconnect')

    @property
    def current_range(self) -> Tuple[RangeValue, RangeValue]:
        """
        :returns: Min and max current values.
        """
        logging.debug('current range')

    @property
    def voltage_range(self) -> Tuple[RangeValue, RangeValue]:
        """
        :returns: Min and max voltage values.
        """
        logging.debug('voltage range')

    def set_voltage(
        self,
        voltage: float
    ):
        """
        Sets the applied voltage.

        :param voltage: Desired voltage.
        """
        logging.debug('set_voltage')

    def set_current(
        self,
        current: float
    ):
        """
        Sets the applied current.

        :param current: Desired current.
        """
        logging.debug('set_current')

    def enable_output(self):
        """
        Enable output.
        """
        logging.debug('enable_output')

    def disable_output(self):
        """
        Disable output.
        """
        logging.debug('disable_output')

    def measure_voltage(self) -> float:
        """
        :returns: 0.0
        """
        logging.debug('measure_voltage')
        return 0.0

    def measure_current(self) -> float:
        """
        :returns: 0.0
        """
        logging.debug('measure_current')
        return 0.0

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
        :returns: numpy.zeroes(10).
        """
        logging.debug('measure_iv_curve')
        return np.zeros(10)

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
        :returns: numpy.zeroes(10). 
        """
        logging.debug('measure_iv_point_by_point')
        return np.zeros(10)

    def measure_chronopotentiometry(
        self,
        current: float,
        time: float
    ) -> np.array:
        """
        Perform a chronovoltometry experiment.

        :param current: Set point current.
        :param time: Run time.
        :returns: numpy.zeroes(10).
        """
        logging.debug('measure_chronopotentiometry')
        return np.zeroes(10)

    def measure_chronoampometry(
        self,
        voltage: float,
        time: float
    ) -> np.array:
        """
        Perform a chronoampometry experiment.

        :param voltage: Set point voltage.
        :param time: Run time.
        :returns: numpy.zeroes(10).
        """
        logging.debug('measure_chronoampometry')
        return np.zeroes(10)