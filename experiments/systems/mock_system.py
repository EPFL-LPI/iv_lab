from iv_lab_controller.user import Permission
from iv_lab_controller.base_classes import System

from iv_lab_instruments.lamps.mock_lamp import MockLamp
from iv_lab_instruments.smus.mock_smu import MockSMU
from iv_lab_instruments.system_parameters.mock_system_parameters import MockSystemParameters

from iv_lab_experiments.mock_experiment import MockExperiment


class MockSystem(System):
    """
    Mock system used for testing.
    """
    def __init__(self, emulate: bool = False):
        """
        :param emulate: Run in emulation mode. [Default: False]
        """
        lamp = MockLamp(emulate=emulate)
        smu = MockSMU(emulate=emulate)
        system_parameters = MockSystemParameters()
        super().__init__(lamp, smu, system_parameters, emulate=emulate)

        self.add_experiment(Permission.Basic, MockExperiment)

        # procedure functions
        def mock_startup():
            print('startup')
            self.lamp.light_on()
            self.smu.connect()

        def mock_shutdown():
            self.lamp.light_off()
            self.smu.disconnect()

        self.set_procedure_functions(
            MockExperiment,
            startup=mock_startup,
            shutdown=mock_shutdown
        )
