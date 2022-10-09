from typing import Union, Dict, Any

from pymeasure.experiment import FloatParameter

from ..base_classes import ExperimentParametersInterface


class CellParameters(ExperimentParametersInterface):
    """
    Parameters for a cell.
    """
    def __init__(self):
        self._cell_area: Union[FloatParameter, None] = None

    @property
    def cell_area(self) -> Union[FloatParameter, None]:
        """
        :returns: Cell area
        """
        return self._cell_area
    
    @cell_area.setter
    def cell_area(self, area: Union[FloatParameter, float, None]):
        """
        :param area: Cell area.
        """
        if isinstance(area, float):
            param = FloatParameter('cell_area', units='cm^2', minimum=0)
            param.value = area

        else:
            param = area

        self._cell_area = param

    def __iter__(self):
        yield self.cell_area

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
        area_val = None if self.cell_area is None else self.cell_area.value
        return {
            'active_area': area_val
        }
