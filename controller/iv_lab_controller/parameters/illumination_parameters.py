from typing import Union, Dict, Any

from pymeasure.experiment import FloatParameter, BooleanParameter

from ..base_classes import ExperimentParametersInterface


class IlluminationParameters(ExperimentParametersInterface):
    """
    Parameters for a cell.
    """
    def __init__(self):
        self._manual: Union[BooleanParameter, None] = BooleanParameter('light_level_manual', default=False)
        self._intensity: Union[FloatParameter, None] = None

    @property
    def manual(self) -> Union[BooleanParameter, None]:
        """
        :returns: Light intensity manually set.
        """
        return self._manual
    
    @manual.setter
    def manual(self, manual: Union[BooleanParameter, float, None]):
        """
        :param inten: Light intensity manually set.
        """
        if isinstance(manual, float):
            param = BooleanParameter('light_level_manual')
            param.value = manual

        else:
            param = manual

        self._manual = param

    @property
    def intensity(self) -> Union[FloatParameter, None]:
        """
        :returns: Desired light intensity.
        """
        return self._intensity
    
    @intensity.setter
    def intensity(self, inten: Union[FloatParameter, float, None]):
        """
        :param inten: Desired light intensity.
        """
        if isinstance(inten, float) or isinstance(inten, int):
            param = FloatParameter('light_intensity', units='suns', minimum=0)
            param.value = inten

        else:
            param = inten

        self._intensity = param

    def __iter__(self):
        yield self.manual
        yield self.intensity

    def validate(self) -> bool:
        """
        :returns: True is all parameters are valid. Otherwise raises an exception.
        :raises: If a parameter is invalid.
        """
        # always valid
        return True

    def to_dict(self) -> Dict[str, Any]:
        """
        :returns: Dictionary representation of the parameters.
        """
        manual_val = None if self.manual is None else self.manual.value
        intensity_val = None if self.intensity is None else self.intensity.value
        return {
            'light_level_manual': manual_val,
            'light_intensity': intensity_val
        }
