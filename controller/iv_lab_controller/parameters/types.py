from enum import Enum


class SweepDirection(Enum):
    """
    Enum for the direction of a voltage or current sweep.
    """
    Forward = 'forward'
    Reverse = 'reverse'
