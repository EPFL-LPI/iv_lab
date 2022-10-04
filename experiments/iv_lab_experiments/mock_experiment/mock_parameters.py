from typing import Union, Dict, Any

from pymeasure.experiment.parameters import (
    BooleanParameter,
    IntegerParameter
)

from iv_lab_controller.base_classes.measurement_parameters import MeasurementParameters


class MockExperimentParameters(MeasurementParameters):
    """
    Parameters for an mock experiment.
    """
    def __init__(self):
        self._log: Union[BooleanParameter, None] = None
        self._times: Union[IntegerParameter, None] = None

    @property
    def log(self) -> Union[BooleanParameter, None]:
        """
        :returns: Value of the `print` parameter.
        """
        return self._log

    @log.setter
    def log(self, log: bool):
        """
        Sets the `print` parameter.
        """
        self._log = BooleanParameter('log')
        self._log.value = log

    @property
    def times(self) -> Union[IntegerParameter, None]:
        """
        :returns: Value of the `times` parameter.
        """
        return self._times

    @times.setter
    def times(self, times: int):
        """
        Sets the `times` parameter.
        """
        self._times = IntegerParameter('times')
        self._times.value = times

    def validate(self) -> bool:
        """
        :returns: True is all parameters are valid. Otherwise raises an exception.
        :raises: If a parameter is invalid.
        """
        return True

    def to_dict(self) -> Dict[str, Any]:
        """
        :returns: Parameters as a name-value dictionary.
        """
        log_val = None if self.log is None else self.log.value
        times_val = None if self.times is None else self.times.value
        return {
            'log': log_val,
            'times': times_val
        }
