"""Abstract base interface for the Arduino shutter / cell-selection
controller.

Extracted from the legacy ``arduino`` class in ``IVLab/IVlab.py``, which
is only used by the ``IV_Old`` system. It controls:

- the shutter (legacy digital pin 2: 1 = open, 0 = closed),
- the test/reference cell selection stage (legacy digital pin 4:
  1 = test cell, 0 = reference cell; the stage needs a settling time
  after moving, legacy 5 s).

The legacy class had no ``turn_off``; per the safety rules in
docs/HARDWARE.md the base provides one that closes the shutter, so
measurement cleanup can always leave the system dark.

This module is standard library only; the real driver defers its
``pyvisa`` import to connection time.
"""

from __future__ import annotations

from abc import abstractmethod

from iv_lab.config import ArduinoSettings
from iv_lab.hardware.base import HardwareDevice

#: Legacy stage settling time in seconds (``cell_stage_settling_time``).
CELL_STAGE_SETTLING_TIME = 5.0


class BaseArduino(HardwareDevice):
    """Abstract shutter / cell-selection controller."""

    def __init__(self, settings: ArduinoSettings, name: str = "") -> None:
        super().__init__(name or f"{settings.brand} {settings.model}")
        self.settings = settings
        #: Wait after moving the cell stage, in s (legacy
        #: ``cell_stage_settling_time``).
        self.cell_stage_settling_time: float = CELL_STAGE_SETTLING_TIME

    @abstractmethod
    def open_shutter(self) -> None:
        """Open the shutter (legacy ``shutter_open``, pin 2 -> 1)."""

    @abstractmethod
    def close_shutter(self) -> None:
        """Close the shutter (legacy ``shutter_close``, pin 2 -> 0)."""

    @abstractmethod
    def select_test_cell(self) -> None:
        """Move the test cell into the beam (legacy ``select_test_cell``,
        pin 4 -> 1), then wait for the stage to settle."""

    @abstractmethod
    def select_reference_cell(self) -> None:
        """Move the reference cell into the beam (legacy
        ``select_reference_cell``, pin 4 -> 0), then wait for the stage
        to settle."""

    def turn_off(self) -> None:
        """Leave the system safe by closing the shutter.

        Not present in the legacy class; added per the docs/HARDWARE.md
        safety rules ("shutter closed after measurements").
        """
        self.close_shutter()
