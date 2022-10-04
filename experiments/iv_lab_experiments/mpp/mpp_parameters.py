from .base_classes.measurement_parameters import MeasurementParameters


class MPPParameters(MeasurementParameters):
    """
    Measurement parameters for MPP measurements.
    """
    def __init__(self):
        """
        """
        super().__init__()

    # @todo
    def validate(self) -> bool:
        """
        :returns: True is all parameters are valid. Otherwise raises an exception.
        :raises: If a parameter is invalid.
        """
        raise NotImplementedError()
