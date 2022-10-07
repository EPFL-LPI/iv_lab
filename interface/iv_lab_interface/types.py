from typing import List, Tuple
from enum import Enum

from iv_lab_controller.base_classes import Experiment, ExperimentParameters

"""
Experiment queue type
"""
ExperimentQueue = List[Tuple[Experiment, ExperimentParameters]]

class ApplicationState(Enum):
    """
    Application states.
    """
    LoggedOut = 0
    Standby = 1
    Running = 2
    Error = 3

class HardwareState(Enum):
    """
    Hardware states.
    """
    Standby = 0
    Initialized = 1


class ExperimentAction(Enum):
    """
    Experiment actions.
    """
    Run = 0
    Abort = 1


class ExperimentState(Enum):
    """
    Experiment states.
    """
    Standby = 0
    Running = 1
    Aborting = 2
