from typing import Union

from pymeasure.experiment import (
    BooleanParameter,
    FloatParameter,
    IntegerParameter
)

from iv_lab_controller.base_classes import ExperimentParametersInterface


class IVCurveParameters(ExperimentParametersInterface):
    """
    Parameters for an IV curve measurement.
    """
    automatic_limits = BooleanParameter('automatic_limits')
    start_voltage = FloatParameter('start_voltage', units='V')
    stop_voltage = FloatParameter('stop_voltage', units='V')
    voltage_step = FloatParameter('voltage_step', units='V', minimum=0)
    sweep_rate = FloatParameter('sweep_rate', units='V/s', minimum=0)
    settling_time = FloatParameter('settling_time', units='s', minimum=0)
    check_polarity = BooleanParameter('check_polarity', default=False)

    def validate(self) -> bool:
        """
        :returns: True is all parameters are valid. Otherwise raises an exception.
        :raises: If a parameter is invalid.
        """
        if (
            (self.automatic_limits is not None)
            and (self.automatic_limits.value)
        ):
            # min and max voltage must be None
            if (
                (self.min_voltage is not None)
                or (self.max_voltage is not None)
            ):
                raise ValueError('Voltage limits can not be set when using automatic limits.')

        else:
            if (
                (self.start_voltage is None)
                or (self.stop_voltage is None)
            ):
                raise ValueError('Both voltage limits must be set.')

        # valid
        return True
