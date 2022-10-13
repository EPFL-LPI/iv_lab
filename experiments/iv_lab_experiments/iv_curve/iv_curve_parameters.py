from typing import Union

from pymeasure.experiment import (
    BooleanParameter,
    FloatParameter,
    IntegerParameter
)

from iv_lab_controller.base_classes import ExperimentParametersInterface
from iv_lab_controller.parameters.types import SweepDirection


class IVCurveParameters(ExperimentParametersInterface):
    """
    Parameters for an IV curve measurement.
    """
    use_automatic_limits = BooleanParameter('use_automatic_limits')
    compliance_current = FloatParameter('compliance_current', units='mA/cm^2')
    min_voltage = FloatParameter('min_voltage', units='V')
    max_voltage = FloatParameter('max_voltage', units='V')
    voltage_step = FloatParameter('voltage_step', units='V', minimum=0)
    sweep_rate = FloatParameter('sweep_rate', units='V/s', minimum=0)
    stabilization_time = FloatParameter('stabilization_time', units='s', minimum=0)
    direction = IntegerParameter('direction', minimum=-1, maximum=1)
    
# =============================================================================
#     @direction.setter
#     def direction(self, direction: Union[FloatParameter, IVSweepDirection, int, None]):
#         """
#         :param direction: Sweep direction for the scan.
#         """
#         if isinstance(direction, SweepDirection):
#             direction = 1 if ( direction is SweepDirection.Forward ) else -1
# 
#         if isinstance(direction, int):
#             param = IntegerParameter('direction', minimum=-1, maximum=1)
#             param.value = direction
# 
#         else:
#             param = step
# 
#         self._direction = param
# =============================================================================


    def validate(self) -> bool:
        """
        :returns: True is all parameters are valid. Otherwise raises an exception.
        :raises: If a parameter is invalid.
        """
        if (
            (self.use_automatic_limits is not None)
            and (self.use_automatic_limits.value)
        ):
            # min and max voltage must be None
            if (
                (self.min_voltage is not None)
                or (self.max_voltage is not None)
            ):
                raise ValueError('Voltage limits can not be set when using automatic limits.')

        else:
            if (
                (self.min_voltage is None)
                or (self.max_voltage is None)
            ):
                raise ValueError('Both voltage limits must be set.')

            if (self.min_voltage.value >= self.max_voltage.value):
                raise ValueError('Minimum voltage limit must be less than the maximum limit.')

        # valid
        return True
