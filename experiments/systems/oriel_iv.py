from iv_lab_controller.user import Permission
from iv_lab_controller.base_classes import System

from iv_lab_instruments.lamps.keithley_filter_wheel import KeithleyFilterWheel
from iv_lab_instruments.smus.keithley_2400 import Keithley2400
from iv_lab_instruments.system_parameters.mock_system_parameters import MockSystemParameters

from iv_lab_experiments.mock_experiment import MockExperiment
from iv_lab_experiments.iv_curve import IVCurve

class OrielIV(System):
    """
    OrielIV system in IV lab.
    """
    def __init__(self, emulate: bool = False):
        """
        :param emulate: Run in emulation mode. [Default: False]
        """
        addr = "GPIB0::24::INSTR"
        smu = Keithley2400(adapter=addr, emulate=emulate)
        lamp = KeithleyFilterWheel(smu=smu, emulate=emulate)
        system_parameters = MockSystemParameters()
        super().__init__(lamp, smu, system_parameters, emulate=emulate)

        self.add_experiment(Permission.Basic, MockExperiment)
        self.add_experiment(Permission.Basic, IVCurve)
