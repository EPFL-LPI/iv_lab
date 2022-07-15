from abc import ABC

from iv_lab_controller.base_classes.lamp import Lamp


class TrinamicLamp(ABC, Lamp):
    """
    Trinamic lamps base class.
    """
    def __init__(
        self,
        microstep_resolution: float,
        steps_per_revolution: int,
        emulate: bool = False
    ):
        """
        :param microstep_resolution: 
        :param steps_per_revolution: Number of steps per revolution.
        :param emulate: Whether to emulate the lamp or not. [Default: False]
        """
        super().__init__(emulate=emulate)
        
        self.microstep_resolution = microstep_resolution
        self.steps_per_revolution = steps_per_revolution
        self.interface = None
        self.filter_wheel_map = {
            # map of intensities to filter wheel angles
            100: 0,
            50: 5,
            20: 4,
            10: 3,
            0: 2
        }

    def __del__(self):
        if self.interface is not None:
            self.interface.close()

    def _disconnect(self):
        self.interface.close()

    def _turn_off(self):
        self.disconnect()

    @Lamp.intensity.setter
    def intensity(self, intensity: float):
        """
        :param intensity: Intensity set point in W/cm2.
        :raises ValueError: If intensity is invalid.
        """
        if intensity not in self.filter_wheel_map:
            raise ValueError('Invalid intensity.')

        self._intensity = intensity
        if self.light_is_on:
            self.light_on()

    def convert_angle_to_microsteps(self, angle: float) -> int:
        microstepsPerFullStep = 2**self.microstep_resolution
        targetPosition = int(angle*(self.steps_per_revolution/360)*microstepsPerFullStep)
        return targetPosition