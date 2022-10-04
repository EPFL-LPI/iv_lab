from abc import ABC, abstractmethod
from typing import Dict, Any


class MeasurementParameters(ABC):
    """
    Holds parameters for a measurement.
    """

    @abstractmethod 
    def validate(self) -> bool:
        """
        :returns: True if all parameters are valid. Otherwise raises an exception.
        :raises: If a parameter, or combination of parameters, is invalid.
        """
        raise NotImplementedError()

    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """
        :returns: Dictionary representation of the parameters.
        """
        raise NotImplementedError()
