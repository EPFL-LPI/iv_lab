from typing import Union, Dict, Any

from ..base_classes import ExperimentParametersInterface
from . import SystemParameters


class CompleteParameters(ExperimentParametersInterface):
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

    def to_dict(self) -> Dict[str, Any]:
        system_params = (
            SystemParameters()
            if self.system_parameters is None else
            self.system_parameters
        )

        experiment_params = (
            {}
            if self.experiment_parameters is None else
            self.experiment_parameters.to_dict()
        )

        return {
            **system_params.to_dict(),
            **experiment_params
        }

