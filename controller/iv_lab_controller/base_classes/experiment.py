from abc import ABC
from typing import Type, Dict, Any

from pymeasure.experiment.procedure import Procedure as Procedure
from pymeasure.experiment.parameters import Parameter

from .parameters_widget import MeasurementParametersWidget


class Experiment(ABC):
    """
    An experiment that can be run by a System.
    """
    # display name of the procedure
    name: str
    procedure: Type[Procedure]
    ui: MeasurementParametersWidget

    def __init__(self):
        """
        """
        pass

    @classmethod
    def create_procedure(cls, params: Dict[str, Any]) -> Procedure:
        """
        Creates a procedure with the given parameters set.
        """
        proc: Procedure = cls.procedure()
        proc.set_parameters(params)
        return proc
