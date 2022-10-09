import os
from enum import Enum
from typing import Union

"""
Path-like object.
"""
PathLike = Union[str, os.PathLike]


class RunnerState(Enum):
    """
    Runner states.
    """
    Error = -1
    Standby = 0
    Running = 1
    Aborting = 2
