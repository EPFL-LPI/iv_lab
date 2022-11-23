import logging
import random

from iv_lab_controller.base_classes import HardwareBase, SMU
from iv_lab_controller.base_classes.smu import RangeValue


class MockSMU(SMU):
    """
    Mock SMU used for testing.
    """
    def __init__(self, emulate: bool = False):
        super().__init__(emulate=emulate)
        self._is_connected = False
        self._current_range: RangeValue = 0
        self._voltage_range: RangeValue = 0
        self._compliance_current: float = 0
        self._compliance_voltage: float = 0
        self._voltage: float = 0
        self._current: float = 0
        self._output_enabled = False

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
        self._is_connected = True

    def _disconnect(self):
        """
        Disconnect from the SMU.
        """
        logging.debug('disconnect')
        self._is_connected = False

    @property
    def current_range(self) -> float:
        """
        :returns: Min and max current values.
        """
        logging.debug('current range')
        return self._current_range

    @property
    def voltage_range(self) -> float:
        """
        :returns: Min and max voltage values.
        """
        logging.debug('voltage range')
        return self.voltage_range

    @property
    def compliance_current(self) -> float:
        """
        :returns: Compliance current.
        """
        logging.debug('compliance current')
        return self._compliance_current

    @compliance_current.setter
    def compliance_current(self, i: float):
        """
        Sets the compliance current.

        :param: Desired compliance current.
        """
        logging.debug('set compliance current')
        self._compliance_current = i

    @property
    def compliance_voltage(self) -> float:
        """
        :returns: Compliance voltage.
        """
        logging.debug('compliance voltage')
        return self._compliance_voltage

    @compliance_voltage.setter
    def compliance_voltage(self, v: float):
        """
        Sets the compliance voltage.

        :param v: Desired compliance voltage.
        """
        logging.debug('set compliance voltage')
        self._compliance_voltage = v

    def set_voltage(
        self,
        voltage: float
    ):
        """
        Sets the applied voltage.

        :param voltage: Desired voltage.
        """
        logging.debug('set_voltage')
        self._voltage = voltage

    def set_current(
        self,
        current: float
    ):
        """
        Sets the applied current.

        :param current: Desired current.
        """
        logging.debug('set_current')
        self._current = current

    def enable_output(self):
        """
        Enable output.
        """
        logging.debug('enable_output')
        self._output_enabled = True

    def disable_output(self):
        """
        Disable output.
        """
        logging.debug('disable_output')
        self._output_enabled = False

    def get_voltage(self) -> float:
        """
        :returns: Random float within compliance voltage.
        """
        logging.debug('measure_voltage')
        v = random.uniform(-self.compliance_voltage, self.compiance_voltage)
        return v

    def get_current(self) -> float:
        """
        :returns: Random float within compliance current.
        """
        logging.debug('measure_current')
        i = random.uniform(-self.compliance_current, self.compiance_current)
        return i
