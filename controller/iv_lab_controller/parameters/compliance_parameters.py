from typing import Union, Any, Dict

from pymeasure.experiment import FloatParameter

from ..base_classes import ExperimentParametersInterface


# @todo: Create correct parameters, currently placeholder
class ComplianceParameters(ExperimentParametersInterface):
    """
    Parameters for measurement compliance.
    """
    current: Union[FloatParameter, None] = FloatParameter('compliance_current', units='A', minimum=0)
    voltage: Union[FloatParameter, None] = FloatParameter('compliance_voltage', units='V', minimum=0)
