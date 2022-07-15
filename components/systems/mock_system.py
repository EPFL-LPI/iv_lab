from iv_lab_controller.base_classes.system import System

from iv_lab_components.lamps.mock_lamp import MockLamp
from iv_lab_components.smus.mock_smu import MockSMU
from iv_lab_components.computer_parameters.mock_computer_parameters import MockComputerParameters
from iv_lab_components.iv_system_parameters.mock_iv_system_parameters import MockIVSystemParameters


class MockSystem(System):
    """
    Mock system used for testing.
    """
    def __init__(self, emulate: bool = False):
        """
        :param emulate: Run in emulation mode. [Default: False]
        """
        super().__init__(emulate=emulate)

        self._lamp = MockLamp(emulate=emulate)
        self._smu = MockSMU(emulate=emulate)
        self._computer_parameters = MockComputerParameters()
        self._iv_system_parameters = MockIVSystemParameters()