from typing import Union

from pymeasure.experiment.parameters import FloatParameter

from .base_classes.measurement_parameters import MeasurementParameters


class CalibrationParameters(MeasurementParameters):
    """
    Measurement parameters for MPP measurements.
    """
    def __init__(self):
        """
        """
        super().__init__()

        self._reference_current: Union[FloatParameter, None] = None

    @property
    def reference_current(self) -> Union[FloatParameter, None]:
        return self.reference_current

    @reference_current.setter
    def reference_current(self, ref_current: float):
        if isinstance(ref_current, float):
            param = FloatParameter('reference_current', units='A', minimum=0)
            param.value = ref_current

        else:
            param = ref_current

        self._reference_current = param

    # @todo
    def validate(self) -> bool:
        """
        :returns: True is all parameters are valid. Otherwise raises an exception.
        :raises: If a parameter is invalid.
        """
        raise NotImplementedError()
