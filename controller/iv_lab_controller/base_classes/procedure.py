from abc import ABC

from pymeasure.experiment import Procedure as PyMeasProcedure
from pymeasure.experiment import FloatParameter

class Procedure(PyMeasProcedure):
    """
    An IV Lab procedure with standard parameters.
    """
    active_area = FloatParameter('Active area', units='cm^2')
    
    # compliance
    compliance_voltage = FloatParameter(
        'Compliance voltage',
        units='V',
        minimum=0,
        default=1.5
    )

    compliance_current = FloatParameter(
        'Compliance current',
        units='A',
        minimum=0,
        default=0.05
    )

    # light
    light_intensity = FloatParameter(
        'Light intensity',
        units='suns',
        minimum=0,
        default=1
    )

    light_intensity_error = FloatParameter(
        'Light intensity error',
        units='%',
        minimum=0,
        default=0.1
    )

    def validate_parameters(self) -> bool: 
        """
        :returns: `True` if all parameters and parameter combinations are valid.
        :raises ValueError: if a parameter or combination of parameters are
        invalid.
        """
        raise NotImplementedError()
