"""Emulated lamp driver.

Provides the state behavior required by docs/HARDWARE.md (settable light
level, on/off state) without any hardware action or waiting. The legacy
code emulated lamps inside each brand branch by skipping the hardware
calls but keeping the ``light_is_on`` bookkeeping; this driver does the
same for any configured brand.
"""

from __future__ import annotations

from iv_lab.config import LampSettings
from iv_lab.hardware.smu.base import BaseSMU

from ..base import BaseLamp


class EmulatedLamp(BaseLamp):
    """In-memory lamp tracking light level and on/off state."""

    def __init__(self, settings: LampSettings, smu: BaseSMU | None = None) -> None:
        super().__init__(settings, smu=smu, name=f"Emulated {settings.display_name}")

    def _open(self) -> None:
        pass

    def _close(self) -> None:
        pass

    def light_on(self, light_int: float = 100.0) -> None:
        self.light_is_on = False
        if self.light_level_dict is not None:
            # validate the level like the real drivers do
            self._light_level_value(light_int)
        self.light_int = light_int
        # legacy sets light_is_on True after any successful light_on,
        # including at 0 % sun
        self.light_is_on = True

    def light_off(self) -> None:
        self.light_is_on = False
