"""Keithley-controlled filter wheel driver.

Migrated from the ``keithley`` / ``filter wheel`` branches of the legacy
``lamp`` class in ``IVLab/IVlab.py``. The wheel is moved by writing a
digital code to the SMU's TTL output lines (``BaseSMU.set_ttl_level``,
2400-series only), so this driver needs the SMU instance and has no
hardware library of its own.

``lightLevelDict`` maps light level in % sun to the digital filter code.
The wheel position is not readable; the legacy code simply waits a fixed
time for the wheel to reach position (11 s after ``light_on``, 7 s after
``light_off``) — the waits are attributes so tests can shorten them.
"""

from __future__ import annotations

import time
from typing import Optional

from iv_lab.config import LampSettings
from iv_lab.hardware.errors import HardwareConnectionError
from iv_lab.hardware.smu.base import BaseSMU

from ..base import BaseLamp
from ..registry import register_lamp_driver

#: Legacy waits: range(1, 12) / range(1, 8) iterations of 1 s sleeps.
LIGHT_ON_WAIT = 11.0
LIGHT_OFF_WAIT = 7.0


@register_lamp_driver("keithley", "filter wheel")
class KeithleyFilterWheelLamp(BaseLamp):
    """Filter wheel driven by the SMU's digital output lines."""

    def __init__(self, settings: LampSettings, smu: Optional[BaseSMU] = None) -> None:
        super().__init__(settings, smu=smu)
        self.light_on_wait = LIGHT_ON_WAIT
        self.light_off_wait = LIGHT_OFF_WAIT

    def _wait_for_wheel(self, duration: float) -> None:
        """Wait for the wheel to reach position (legacy 1 s sleep steps)."""
        deadline = time.time() + duration
        while time.time() < deadline:
            time.sleep(min(1.0, max(0.0, deadline - time.time())))

    def _open(self) -> None:
        if self.smu is None:
            raise HardwareConnectionError(
                f"{self.name}: the Keithley filter wheel requires the SMU instance"
            )
        # legacy connect: move the wheel to the dark position
        self.light_off()

    def _close(self) -> None:
        # legacy disconnect: nothing to do, the SMU owns the connection
        pass

    def light_on(self, light_int: float = 100.0) -> None:
        self.light_is_on = False

        angle_code = self._light_level_value(light_int)
        self.smu.set_ttl_level(angle_code)
        self._wait_for_wheel(self.light_on_wait)

        self.light_int = light_int
        self.light_is_on = True

    def light_off(self) -> None:
        # legacy: always moves to the dark position, regardless of state
        angle_code = self._light_level_value(0)
        self.smu.set_ttl_level(angle_code)
        self._wait_for_wheel(self.light_off_wait)

        self.light_is_on = False
