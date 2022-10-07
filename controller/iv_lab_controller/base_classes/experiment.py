from abc import ABC
from typing import Type, Dict, Union, Any

from pymeasure.experiment import Procedure
from pymeasure.display.widgets import TabWidget

from .experiment_parameters_widget import ExperimentParametersWidget


class Experiment(ABC):
    """
    An experiment that can be run by a System.
    """
    # display name of the procedure
    name: str
    procedure: Type[Procedure]
    ui: ExperimentParametersWidget
    plot_widget: Union[TabWidget, None]

    @classmethod
    def create_procedure(cls, params: Dict[str, Any]) -> Procedure:
        """
        Creates a procedure with the given parameters set.
        """
        proc: Procedure = cls.procedure()
        proc.set_parameters(params)
        return proc
