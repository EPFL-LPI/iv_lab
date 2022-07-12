import logging
from abc import abstractmethod

from .hardware_base import HardwareBase


class Lamp(HardwareBase):
    """
    Base class providing a common API for lamps.
    """

    def __init__(self, emulate: bool = False):
        """
        :param emulate: Whether to emulate the lamp or not. [Default: False]
        """
        super().__init__(emulate=emulate)

        self._light_is_on = False
        self._intensity: float = 100  # light intensity set point
            
    @property
    def light_is_on(self) -> bool:
        """
        :returns: Whether or not the light is on.
        """
        return self._light_is_on

    @property
    def intensity(self) -> float:
        """
        :returns: Intesnity set point in W/cm2.
        """
        return self._intensity

    @intensity.setter
    def intensity(self, intensity: float):
        self._intensity = intensity
    
    def light_on(self):
        """
        Turn light on.
        """
        if not self.emulate:
            self._light_on()

        self._light_is_on = True
    
    def light_off(self):
        """
        Turn light off.
        """
        if not self.emulate:
            self._light_off()
        
        self._light_is_on = False

    def turn_off(self):
        """
        Turn off the system.
        """
        if not self.emulate:
            self._turn_off()

    @abstractmethod
    def _light_on(self):
        """
        Turn light on.
        """
        raise NotImplementedError()

    @abstractmethod
    def _light_off(self):
        """
        Turn light off.
        """
        raise NotImplementedError()
                
    def _turn_off(self):
        """
        Turn off system.
        """
        raise NotImplementedError()