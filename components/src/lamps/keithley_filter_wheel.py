import time

from iv_lab_controller.base_classes.lamp import Lamp
from ..smu import SMU


class KeithleyFilterWheel(Lamp):
    """
    Lamp driven by a Keithley connected to a filter wheel.
    """
    def __init__(self, smu: SMU, emulate: bool = False):
        """
        :param emulate: Whether to emulate the lamp or not. [Default: False]
        """
        super().__init__()

        self.smu = smu
        self.filter_wheel_map = {
            # map of intensities to filter wheel angles
            100: 0,
            50: 5,
            20: 4,
            10: 3,
            0: 2
        }

    @property
    def name(self) -> str:
        """
        :returns: 'keithley filter wheel'
        """
        return 'keithley filter wheel'

    def _connect(self):
        """
        Lamp is controlled by SMU, no action taken.
        """
        self.light_off()

    def _disconnect(self):
        """
        Lamp is controlled by SMU, no action taken.
        """
        pass

    def _light_on(self):
        angle_code = self.filterWheelDict[self.intensity]
        self.smu.set_TTL_level(angle_code)
        time.sleep(8.0) # wait 8 seconds for filter wheel to reach position

    def _light_off(self):
        angle_code = self.filterWheelDict[0]
        self.smu.set_TTL_level(angle_code)
        time.sleep(8.0) # wait 8 seconds for filter wheel to reach position

    def _turn_off(self):
        """
        Lamp is controlled by SMU, no action taken.
        """
        pass