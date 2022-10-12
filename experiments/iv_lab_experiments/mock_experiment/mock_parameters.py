from typing import Union

from pymeasure.experiment.parameters import (
    BooleanParameter,
    IntegerParameter,
)

from iv_lab_controller.base_classes import ExperimentParametersInterface


class MockExperimentParameters(ExperimentParametersInterface):
    """
    Parameters for an mock experiment.
    """
    log = BooleanParameter('log', default=False)
    iterations = IntegerParameter('iterations', minimum=0, default=0)
