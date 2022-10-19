from pymeasure.experiment import Procedure as PyMeasProcedure
from pymeasure.experiment import FloatParameter, BooleanParameter


class Procedure(PyMeasProcedure):
    """
    An IV Lab procedure with standard parameters.

    # Instance variables
    + `smu`: The `System`'s SMU. Conforms to the `SMU` interface.
    + `lamp`: The `System`'s lamp. Conforms to the `Lamp` inteface.
    + `system_functions`: The `ProcedureFunctions` corresponding to the
        associated `Experiment` on the `System`.
    """
    # cell
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
    light_level_manual = BooleanParameter(
        'Manual light level',
        default=False
    )

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

    def startup(self):
        """
        Calls the startup method defined by the `System`.
        """
        self.system_functions.startup()

    def shutdown(self):
        """
        Calls the shutdown method defined by the `System`.
        """
        self.system_functions.shutdown()

    def validate_parameters(self) -> bool:
        """
        :returns: `True` if all parameters and parameter combinations are valid.
        :raises ValueError: if a parameter or combination of parameters are
        invalid.
        """
        raise NotImplementedError()
