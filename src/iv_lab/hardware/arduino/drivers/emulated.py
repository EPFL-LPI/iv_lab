"""Emulated Arduino shutter / cell-selection controller.

Tracks shutter state and the selected cell in memory without any serial
dependency (docs/HARDWARE.md emulation requirements). The stage settling
wait is zero by default so tests run instantly.
"""

from __future__ import annotations

from iv_lab.config import ArduinoSettings

from ..base import BaseArduino


class EmulatedArduino(BaseArduino):
    """In-memory shutter and cell-stage state."""

    def __init__(self, settings: ArduinoSettings) -> None:
        super().__init__(settings, name=f"Emulated {settings.brand} {settings.model}")
        #: No waiting in emulation (legacy slept even when emulating).
        self.cell_stage_settling_time = 0.0
        #: Shutter state; closed on startup.
        self.shutter_is_open = False
        #: Selected cell, 'test' or 'reference'; the legacy stage default
        #: position is the test cell.
        self.selected_cell = "test"

    def _open(self) -> None:
        pass

    def _close(self) -> None:
        pass

    def open_shutter(self) -> None:
        self.shutter_is_open = True

    def close_shutter(self) -> None:
        self.shutter_is_open = False

    def select_test_cell(self) -> None:
        self.selected_cell = "test"

    def select_reference_cell(self) -> None:
        self.selected_cell = "reference"
