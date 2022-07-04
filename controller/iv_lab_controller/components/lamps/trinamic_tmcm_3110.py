from PyTrinamic.connections.ConnectionManager import ConnectionManager
from PyTrinamic.modules.TMCM3110.TMCM_3110 import TMCM_3110

from .trinamic_base import TrinamicLamp


class TrinamicTMCM3110(TrinamicLamp):
    """
    A Trinamic TMCM-3110 lamp.
    """
    def __init__(
        self,
        microstep_resolution: float,
        steps_per_revolution: int,
        **kwargs
    ):
        """
        :param microstep_resolution: 
        :param steps_per_revolution: Number of steps per revolution.
        :param **kwargs: Additional arguments passed to TrinamicLamp.
        """
        super().__init__(microstep_resolution, steps_per_revolution, **kwargs)
        self.interface = None

    def _connect(self):
        connectionManager = ConnectionManager()
        self.interface = connectionManager.connect()
        self.motor = TMCM_3110(myInterface)
        
        self.motor.setMaxAcceleration(0, 1000)
        self.motor.setMaxVelocity(0, 1000)
        self.motor.setMaxCurrent(0, 50)
        self.microstepResolution = 8
        self.stepsPerRevolution = 200
        self.motor.setAxisParameter(self.motor.APs.MicrostepResolution, 0, self.microstepResolution)

    def _light_on(self):
        angle = self.filter_wheel_map[self.intensity]
        self.motor.moveTo(0, self.convert_angle_to_microsteps(angle))

        while not(self.motor.positionReached(0)):
            if self.should_abort:
                break

    def _light_off(self):
        angle = self.filterWheelDict[0]
        self.motor.moveTo(0, self.convert_angle_to_microsteps(angle))

        while not(self.motor.positionReached(0)):
            if self.should_abort:
                break
