from typing import Union

from pymeasure.experiment import (
    FloatParameter
)

from iv_lab_controller.base_classes import ExperimentParameters


class ChronopotentiometryParameters(ExperimentParameters):
    """
    Parameters for a chronopotentiometry experiment.
    """
    def __init__(self):
        self._set_current: Union[FloatParameter, None] = None
        self._settling_time: Union[FloatParameter, None] = None
        self._interval: Union[FloatParameter, None] = None
        self._duration: Union[FloatParameter, None] = None

    @property
    def set_current(self) -> Union[FloatParameter, None]:
        """
        :returns: Set current.
        """
        return self._set_current
    
    @set_current.setter
    def set_current(self, i: Union[FloatParameter, float, None]):
        """
        :param i: Desired set current.
        """
        if isinstance(i, float):
            param = FloatParameter('set_current', units='A')
            param.value = i

        else:
            param = i

        self._set_current = param

    @property
    def settling_time(self) -> Union[FloatParameter, None]:
        """
        :returns: Settling time before measurement begins.
        """
        return self._settling_time
    
    @settling_time.setter
    def settling_time(self, time: Union[FloatParameter, float, None]):
        """
        :param time: Desired settling time before measurement begins.
        """
        if isinstance(time, float):
            param = FloatParameter('settling_time', units='s')
            param.value = time

        else:
            param = time

        self._settling_time = param

    @property
    def interval(self) -> Union[FloatParameter, None]:
        """
        :returns: Interval between measurements.
        """
        return self._interval
    
    @interval.setter
    def interval(self, time: Union[FloatParameter, float, None]):
        """
        :param time: Desired interval between measurements.
        """
        if isinstance(time, float):
            param = FloatParameter('interval', units='s')
            param.value = time

        else:
            param = time

        self._interval = param

    @property
    def duration(self) -> Union[FloatParameter, None]:
        """
        :returns: Duration of the measurement.
        """
        return self._duration
    
    @duration.setter
    def duration(self, time: Union[FloatParameter, float, None]):
        """
        :param time: Desired duration of the measurement.
        """
        if isinstance(time, float):
            param = FloatParameter('duration', units='s')
            param.value = time

        else:
            param = time

        self._duration = param
