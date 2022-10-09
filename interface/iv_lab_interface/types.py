import os
from typing import Union
from enum import Enum


class ApplicationState(Enum):
    """
    Application states.
    """
    Error = -1
    Disabled = 0
    Active = 1


class HardwareState(Enum):
    """
    Hardware states.
    """
    Error = -1
    Uninitialized = 0
    Initializing = 1
    Initialized = 2


class ExperimentAction(Enum):
    """
    Experiment actions.
    """
    Run = 0
    Abort = 1
