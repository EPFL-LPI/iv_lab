from typing import Union, Dict, Any

from ..base_classes import ExperimentParametersInterface
from . import (
    CellParameters,
    ComplianceParameters,
    IlluminationParameters,
)


class SystemParameters(ExperimentParametersInterface):
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

    def to_dict(self) -> Dict[str, Any]:
        cell_params = (
            CellParameters()
            if self.cell_parameters is None else
            self.cell_parameters
        )

        illumination_params = (
            IlluminationParameters()
            if self.illumination_parameters is None else
            self.illumination_parameters
        )

        compliance_params = (
            ComplianceParameters()
            if self.compliance_parameters is None else
            self.compliance_parameters
        )

        return {
            **cell_params.to_dict(),
            **compliance_params.to_dict(),
            **illumination_params.to_dict(),
        }

