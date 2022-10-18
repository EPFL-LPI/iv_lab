import time
import logging

from iv_lab_controller.base_classes import Lamp, SMU


logger = logging.getLogger('iv_lab')

class KeithleyFilterWheel(Lamp):
    """
    Lamp driven by a Keithley connected to a filter wheel.
    """
    def __init__(self, smu: SMU, emulate: bool = False):
        """
        :param emulate: Whether to emulate the lamp or not. [Default: False]
        """
        super().__init__(emulate=emulate)
        self.sleep_time = 8

        self.smu = smu
        self.filter_wheel_map = {
            # map of intensities to filter wheel angles
            100: 0,
            55: 5,
            10: 4,
            1: 3,
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
        angle_code = self.filter_wheel_map[self.intensity]
        self.smu.write(f":SOUR2:TTL:LEV {angle_code}")
        time.sleep(self.sleep_time) # wait 8 seconds for filter wheel to reach position

    def _light_off(self):
        angle_code = self.filter_wheel_map[0]
        self.smu.write(f":SOUR2:TTL:LEV {angle_code}")
        time.sleep(self.sleep_time) # wait 8 seconds for filter wheel to reach position

    def _turn_off(self):
        """
        Lamp is controlled by SMU, no action taken.
        """
        pass
