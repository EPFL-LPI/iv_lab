from typing import Union, Dict, Any

from pymeasure.experiment import FloatParameter

from ..base_classes import ExperimentParametersInterface


class CellParameters(ExperimentParametersInterface):
    """
    Parameters for a cell.
    """
    cell_area = FloatParameter('active_area', units='cm^2', minimum=0)
