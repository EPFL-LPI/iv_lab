from abc import ABC, abstractmethod, abstractclassmethod
from typing import Dict, Any


class ParametersDictionaryInterface(ABC):
    @abstractmethod
    def to_dict_default(self) -> Dict[str, Any]:
        """
        Converts parameter values into a dictionary of
        key-value pairs, where the value is the value of the parameter.
        If the parameter has not yet been set, its default value is used.

        :returns: Dictionary of key-value pairs.
        """
        pass

    @abstractmethod
    def to_dict_set(self) -> Dict[str, Any]:
        """
        Converts parameter values into a dictionary of
        key-value pairs, where the value is the value of the parameter.
        If the parameter has not yet been set, it is not included.

        :returns: Dictionary of key-value pairs.
        """
        pass

    @abstractmethod
    def to_dict_parameters(self) -> Dict[str, Any]:
        """
        Converts to a flattened dictionary.
        Unset parameters are ignored.
 
        :returns: Dictionary of set parameters.
        """
        pass

    @abstractclassmethod
    def from_dict(cls, d: Dict) -> Any:
        """
        Converts a dictionary to the class.
        Unrecognized key are ignored.
        Missing values are initialized to `None`.

        :param d: Dicitionary to convert.
        :returns: Class with corresponding values.
        """
        pass
