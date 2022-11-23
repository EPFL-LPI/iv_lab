from typing import Union

from pymeasure.experiment import FloatParameter, BooleanParameter

from ..base_classes import ExperimentParametersInterface


class IlluminationParameters(ExperimentParametersInterface):
    """
    Parameters for a cell.
    """
    manual: Union[BooleanParameter, None] = BooleanParameter('manual_light_level', default=False)
    intensity: Union[FloatParameter, None] = FloatParameter('light_intensity', units='suns', minimum=0)
    reference_diode_enabled: Union[BooleanParameter, None] = BooleanParameter('reference_diode_enabled', default=True)