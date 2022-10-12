from abc import ABC
import inspect
from copy import deepcopy
from typing import Dict, Any, Union, Callable

from pymeasure.experiment import (
    Parameter,
    BooleanParameter,
    FloatParameter,
    IntegerParameter,
)

from .parameters_dictionary import ParametersDictionaryInterface


class ExperimentParametersInterface(ParametersDictionaryInterface, ABC):
    """
    Holds parameters for an experiment.
    """
    # hold original parameters because overwritten on first intialization
    _parameter_defaults: Union[Dict[str, Parameter], None] = None

    def __init__(self, **kwargs):
        """
        Initialize parameters.
        Based off of [`pymeasure.experiment.procedure.Procedure#__init__`](https://github.com/pymeasure/pymeasure/blob/18b63ff64f3eed4de1e37356b071a811867b9c85/pymeasure/experiment/procedure.py#L68).

        :param **kwargs: Initial values for parameters.
        """
        self._init_attrs()
        for key in kwargs:
            if key in self._parameter_defaults:
                setattr(self, key, kwargs[key])

    def _init_attrs(self):
        """
        Initialize attributes based on class attributes.
        Based on [`pymeasure.experiment.procedure.Procedure#_update_parameters`](https://github.com/pymeasure/pymeasure/blob/18b63ff64f3eed4de1e37356b071a811867b9c85/pymeasure/experiment/procedure.py#L99).
        """
        cls = self.__class__
        if cls._parameter_defaults is None:
            # parameter properties have not yet been set
            first_init = True
            cls._parameter_defaults = {}
            parameter_properties = inspect.getmembers(cls)

        else:
            first_init = False
            parameter_properties = cls._parameter_defaults.items()

        for item, parameter in parameter_properties:
            if not isinstance(parameter, Parameter):
                continue

            if first_init:
                # store original parameter value
                cls._parameter_defaults[item] = deepcopy(parameter)

            # overwrite parameter properties with getter and setter
            if isinstance(parameter, BooleanParameter):
                prop = parameter_property_bool(item)

            elif isinstance(parameter, FloatParameter):
                prop = parameter_property_float(item)

            elif isinstance(parameter, IntegerParameter):
                prop = parameter_property_int(item)

            else:
                prop = parameter_property_default(item)

            setattr(self.__class__, item, prop)

            # intialize value
            p_name = internal_parameter_name(item)
            setattr(self, p_name, None)

    def __setattr__(self, key: str, value: Any):
        """
        Restrict attributes to those defined on the class.

        :raises AttributeError: If attribute key is invalid.
        """
        param_defaults = self.__class__._parameter_defaults
        # @todo: Code here used to protect from settings
        #   unintended properties.
        #   Perhaps should only allow `Property`s or other
        #   ExperimentParametersInterface.
        if (
            (param_defaults is not None)
            and isinstance(value, Parameter)
        ):
            valid_keys = set(map(
                internal_parameter_name,
                param_defaults.keys()
            ))

            if key not in valid_keys:
                raise AttributeError(f'Invalid property `{key}`')

        object.__setattr__(self, key, value)
        
    def __iter__(self):
        """
        Iterates over parameters.
        """
        cls = self.__class__
        param_defaults = (
            inspect.getmembers(cls)
            if cls._parameter_defaults is None else
            cls._parameter_defaults.items()
        )

        for p_name, parameter in param_defaults:
            if not isinstance(parameter, Parameter):
                continue

            yield (parameter.name, getattr(self, p_name))

    def validate(self) -> bool:
        """
        Validate parameter values.

        :returns: True if all parameters are valid. Otherwise raises an exception.
        :raises: If a parameter, or combination of parameters, is invalid.
        """
        return True

    def to_dict_default(self) -> Dict[str, Any]:
        """
        Converts parameter values into a dictionary of
        key-value pairs, where the value is the value of the parameter.
        If the parameter has not yet been set, its default value is used.

        :returns: Dictionary of key-value pairs.
        """
        vals = {}
        for p_name, param in self.parameter_defaults():
            p_val = getattr(self, p_name)
            if p_val is None:
                p_val = param.default

            else:
                p_val = p_val.value if p_val.is_set() else p_val.default

            vals[param.name] = p_val

        return vals

    def to_dict_set(self) -> Dict[str, Any]:
        """
        Converts parameter values into a dictionary of
        key-value pairs, where the value is the value of the parameter.
        If the parameter has not yet been set, it is not included.

        :returns: Dictionary of key-value pairs.
        """
        vals = {}
        for p_name, param in self.parameter_defaults():
            p_val = getattr(self, p_name)
            if p_val is None:
                continue

            vals[param.name] = p_val.value

        return vals

    def to_dict_parameters(self) -> Dict[str, Any]:
        """
        Converts to a flattened dictionary.
        Unset parameters are ignored.
 
        :returns: Dictionary of set parameters.
        """
        return self.to_dict_set()

    @classmethod
    def from_dict(cls, d: Dict) -> Any:
        """
        Converts a dictionary to the class.
        Unrecognized key are ignored.
        Missing values are initialized to `None`.

        :param d: Dicitionary to convert.
        :returns: Class with corresponding values.
        """
        params = cls()
        for item, parameter in cls.parameter_defaults():
            p_name = parameter.name
            if p_name in d:
                setattr(params, item, d[p_name])

        return params

    @classmethod
    def parameter_defaults(cls):
        if cls._parameter_defaults is None:
            params = {}
            for item, parameter in inspect.getmembers(cls):
                if not isinstance(parameter, Parameter):
                    continue

                params[item] = parameter

            return params

        else:
            return cls._parameter_defaults.items()


# ------------------------
# --- helper functions ---
# ------------------------

def internal_parameter_name(param: str) -> str:
    """
    :returns: Internal name for a parameter.
    """
    return f'_{param}'

def parameter_property_bool(param: str) -> property:
    """
    Creates a property for `BooleanParameter`s

    :param param: Name of the parameter.
    :returns: Property with getter and setter set.
    """
    p_name = internal_parameter_name(param)

    @property
    def prop(self) -> Union[BooleanParameter, None]:
        return getattr(self, p_name)

    @prop.setter
    def prop(self, value: Union[BooleanParameter, bool, None]):
        if isinstance(value, BooleanParameter):
            p_value = value

        elif isinstance(value, bool):
            p_value = deepcopy(self._parameter_defaults[param])
            p_value.value = value

        elif value is None:
            p_value = None

        else:
            raise TypeError('Value can not be converted to a BooleanParameter')

        p_name = internal_parameter_name(param)
        setattr(self, p_name, p_value)

    return prop


def parameter_property_float(param: str) -> property:
    """
    Creates a property for `FloatParameter`s

    :param param: Name of the parameter.
    :returns: Property with getter and setter set.
    """
    p_name = internal_parameter_name(param)

    @property
    def prop(self) -> Union[FloatParameter, None]:
        return getattr(self, p_name)

    @prop.setter
    def prop(self, value: Union[FloatParameter, float, None]):
        if isinstance(value, FloatParameter):
            p_value = value

        elif isinstance(value, float) or isinstance(value, int):
            p_value = deepcopy(self._parameter_defaults[param])
            p_value.value = value

        elif value is None:
            p_value = None

        else:
            raise TypeError('Value can not be converted to a FloatParameter')

        p_name = internal_parameter_name(param)
        setattr(self, p_name, p_value)

    return prop


def parameter_property_int(param: str):
    """
    Creates a property for `IntegerParameter`s

    :param param: Name of the parameter.
    :returns: Property with getter and setter set.
    """
    p_name = internal_parameter_name(param)

    @property
    def prop(self) -> Union[IntegerParameter, None]:
        return getattr(self, p_name)

    @prop.setter
    def prop(self, value: Union[IntegerParameter, float, None]):
        if isinstance(value, IntegerParameter):
            p_value = value

        elif isinstance(value, int):
            p_value = deepcopy(self._parameter_defaults[param])
            p_value.value = value

        elif value is None:
            p_value = None

        else:
            raise TypeError('Value can not be converted to a IntegerParameter')

        p_name = internal_parameter_name(param)
        setattr(self, p_name, p_value)

    return prop


def parameter_property_default(param: str) -> property:
    """
    Creates a property for default parameters.

    :param param: Name of the parameter.
    :returns: Property with getter and setter set.
    """
    @property
    def prop(self) -> Any:
        """
        :raises NotImplementedError: Always.
        """
        raise NotImplementedError(f'The getter for `{param}` is not implemented.')

    @prop.setter
    def prop(param: str, value: Any):
        """
        :raises NotImplementedError: Always.
        """
        raise NotImplementedError(f'The setter for `{param}` is not implemented.')

    return prop
