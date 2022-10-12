from typing import Union, Dict, Any

from ..base_classes import ExperimentParametersInterface
from . import SystemParameters


class CompleteParameters():
    """
    Container for complete parameters.
    """
    def __init__(self):
        self.system_parameters: Union[SystemParameters, None] = None
        self.experiment_parameters: Union[ExperimentParametersInterface, None] = None

    def validate(self) -> bool:
        """
        :returns: True if all parameters are present and valid. Otherwise raises an exception.
        :raises: If a parameter is invalid or missing.
        """
        if self.system_parameters is None:
            raise ValueError('System parameters not set')

        else:
            self.system_parameters.validate()

        if self.experiment_parameters is None:
            raise ValueError('Experiment parameters not set')

        else:
            self.experiment_parameters.validate()

        return True

    def to_dict_set(self) -> Dict[str, Any]:
        d = {}
        if self.system_parameters is not None:
            d['system_parameters'] = self.system_parameters.to_dict_set()

        if self.experiment_parameters is not None:
            d['experiment_parameters'] = self.experiment_parameters.to_dict_set()

        return d

    def to_dict_parameters(self) -> Dict[str, Any]:
        system_params = (
            SystemParameters()
            if self.system_parameters is None else
            self.system_parameters
        )

        experiment_params = (
            {}
            if self.experiment_parameters is None else
            self.experiment_parameters.to_dict_parameters()
        )

        return {
            **system_params.to_dict_parameters(),
            **experiment_params
        }

    @classmethod
    def from_dict(cls, d: Dict) -> 'CompleteParameters':
        """
        Converts a dictionary to CompleteParameters.
        Unrecognized key are ignored.
        Missing values are initialized to `None`.

        :param d: Dictionary to convert.
        :returns: CompleteParameters with corresponding values.
        """
        params = cls()
        if 'system_parameters' in d:
            params.system_parameters = d['system_parameters']

        if 'experiment_parameters' in d:
            params.experiment_parameters = d['experiment_parameters']

        return params
