from pytrinamic.connections import ConnectionManager
from pytrinamic.modules import TMCM1260

from .trinamic_base import TrinamicLamp


class TrinamicTMCM1260(TrinamicLamp):
    """
    A Trinamic TMCM-1260 lamp.
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

    @property
    def name(self) -> str:
        """
        :returns: 'trinamic tmcm-1260'
        """
        return 'trinamic tmcm-1260'

    def _connect(self):
        connectionManager = ConnectionManager()
        self.interface = connectionManager.connect()
        self.motor = TMCM1260(myInterface)
        
        self.motor.setMaxAcceleration(0, 1000)
        self.motor.setMaxVelocity(0, 1000)
        self.motor.setMaxCurrent(0, 50)
        self.microstepResolution = 8
        self.stepsPerRevolution = 200
        self.motor.setAxisParameter(self.motor.APs.MicrostepResolution, 0, self.microstepResolution)

    def _light_on(self):
        """
        Turn the light on.
        """
        angle = self.filterWheelDict[self.intensity]
        self.motor.moveTo(self.convert_angle_to_microsteps(angle))

        while not self.motor.positionReached():
            if self.should_abort:
                break

    def _light_off(self):
        angle = self.filterWheelDict[0]
        self.motor.moveTo(self.convert_angle_to_microsteps(angle))

        while not self.motor.positionReached():
            if self.should_abort:
                break
