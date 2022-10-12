import json
from typing import Union, Dict, Any, Tuple

from ..base_classes import (
    ParametersDictionaryInterface,
    ExperimentParametersInterface,
)

from . import (
    CellParameters,
    ComplianceParameters,
    IlluminationParameters,
)


class SystemParameters(ParametersDictionaryInterface):
    """
    Container for system parameters.
    """
    def __init__(self):
        self.cell_parameters: Union[CellParameters, None] = None
        self.compliance_parameters: Union[ComplianceParameters, None] = None
        self.illumination_parameters: Union[IlluminationParameters, None] = None

    def validate(self) -> bool:
        """
        :returns: True if all parameters are present and valid. Otherwise raises an exception.
        :raises: If a parameter is invalid or missing.
        """
        if self.cell_parameters is None:
            raise ValueError('Cell parameters not set')

        else:
            self.cell_parameters.validate()

        if self.compliance_parameters is None:
            raise ValueError('Compliance parameters not set')

        else:
            self.compliance_parameters.validate()

        if self.illumination_parameters is None:
            raise ValueError('Illumination parameters not set')

        else:
            self.illumination_parameters.validate()

        return True

    def to_dict_set(self) -> Dict[str, Any]:
        """
        Converts parameter values into a dictionary of
        key-value pairs, where the value is the value of the parameter.
        If the parameter has not yet been set, it is not included.

        :returns: Dictionary of key-value pairs.
        """
        d = {}
        if self.cell_parameters is not None:
            d['cell_parameters'] = self.cell_parameters.to_dict_set()

        if self.compliance_parameters is not None:
            d['compliance_parameters'] = self.compliance_parameters.to_dict_set()

        if self.illumination_parameters is not None:
            d['illumination_parameters'] = self.illumination_parameters.to_dict_set()

        return d

    def to_dict_default(self) -> Dict[str, Any]:
        vals = self._children_values_with_defaults()
        d = {k: v.to_dict_default() for k, v in vals.items()}
        return d

    def to_dict_parameters(self) -> Dict[str, Any]:
        """
        :returns: Dictionary of flattened parameters.
            Unset parameters are ignored.
        """
        cell_params = (
            {}
            if self.cell_parameters is None else
            self.cell_parameters.to_dict_parameters()
        )

        compliance_params = (
            {}
            if self.compliance_parameters is None else
            self.compliance_parameters.to_dict_parameters()
        )

        illumination_params = (
            {}
            if self.illumination_parameters is None else
            self.illumination_parameters.to_dict_parameters()
        )

        return {
            **cell_params,
            **compliance_params,
            **illumination_params,
        }

    @classmethod
    def from_dict(cls, d: Dict) -> 'SystemParameters':
        """
        Converts a dictionary to a SystemParameters from standard keys.
        Attributes with missing keys are initialized to `None`.
        Unrecognized keys are ignored.

        :param d: Dictionary with values.
            Keys are ['cell_parameters', 'compliance_parameters', 'illumination_parameters'],
            with corresponding values.
        :returns SystemParameters: SystemParameters constructed from the dictionary.
        """
        params = cls()
        if 'cell_parameters' in d:
            params.cell_parameters = CellParameters.from_dict(
                d['cell_parameters']
            )

        if 'compliance_parameters' in d:
            params.compliance_parameters = ComplianceParameters.from_dict(
                d['compliance_parameters']
            )

        if 'illumination_parameters' in d:
            params.illumination_parameters = IlluminationParameters.from_dict(
                d['illumination_parameters']
            )

        return params

    def _children_values_with_defaults(self) -> Dict[str, ExperimentParametersInterface]:
        cell_params = (
            CellParameters()
            if self.cell_parameters is None else
            self.cell_parameters
        )

        compliance_params = (
            ComplianceParameters()
            if self.compliance_parameters is None else
            self.compliance_parameters
        )

        illumination_params = (
            IlluminationParameters()
            if self.illumination_parameters is None else
            self.illumination_parameters
        )

        return {
            'cell_parameters': cell_params,
            'compliance_parameters': compliance_params,
            'illumination_parameters': illumination_params,
        }


# ------------
# --- json ---
# ------------

class SystemParametersJSONEncoder(json.JSONEncoder):
    """
    JSON encoder for SystemParameters.
    """
    def default(self, o: Any):
        if isinstance(o, SystemParameters):
            return o.to_dict_default()

        return json.JSONEncoder.default(self, o)
