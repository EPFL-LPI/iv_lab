import logging

from .hardware_base import HardwareBase


class Lamp(HardwareBase):
    def __init__(self, emulate: bool = False):
        """
        :param emulate: Whether to emulate the lamp or not. [Default: False]
        """
        super().__init__()

        self._connected = False
        self._light_is_on = False
        self._emulate = emulate

        self._intensity: float = 100  # light intensity set point
            
    @property
    def connected(self) -> bool:
        """
        :returns: Whether or not the lamp is connected.
        """
        return self._connected

    @property
    def light_is_on(self) -> bool:
        """
        :returns: Whether or not the light is on.
        """
        return self._light_is_on

    @property
    def emulation_mode(self) -> bool:
        """
        :returns: Whetehr the lamp is running in emulation mode or not.
        """
        return self._emulate

    @property
    def intensity(self) -> float:
        """
        :returns: Intesnity set point in W/cm2.
        """
        return self._intensity

    @intensity.setter
    def intensity(self, intensity: float):
        self._intensity = intensity
    
    def _connect(self):
        """
        Connect to the lamp.
        """
        raise NotImplementedError()

    def _disconnect(self):
        """
        Disconnect from the lamp.
        """
        raise NotImplementedError()

    def connect(self):
        """
        Connects to the lamp.
        """
        if (not self.emulate) and (not self.connected):
            self._connect()
            
        self._connected = True
    
    def disconnect(self):
        """
        Disconnects from the lamp.
        """
        if (not self.emulate) and self.connected:
            self._disconnect()

        self._connected = False
    
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

    def _light_on(self):
        """
        Turn light on.
        """
        raise NotImplementedError()

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