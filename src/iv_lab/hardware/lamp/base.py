"""Abstract base interface for lamps / solar simulators / filter wheels.

Extracted from the legacy ``lamp`` class in ``IVLab/IVlab.py``. The
interface the application actually uses is small:

- ``light_on(light_int)`` — turn the light on at (or move the filter
  wheel to) the requested intensity in percent of one sun,
- ``light_off()`` — turn the light off / move the wheel to the dark
  position,
- ``turn_off()`` — final safety cleanup (legacy closes a socket left
  open; a no-op for most lamp types),
- the ``light_is_on`` state flag,
- the ``light_level_dict`` mapping from intensity in % sun to a
  lamp-type-specific value (Wavelabs recipe name, filter wheel angle,
  or digital filter code).

The legacy GUI-facing ``light_int`` attribute (last requested level,
default 100) is kept as well.

This module is standard library only; concrete drivers defer optional
hardware imports (``pyvisa``, ``pytrinamic``) into connection-time code.
"""

from __future__ import annotations

from abc import abstractmethod
from typing import Any

from iv_lab.config import LampSettings
from iv_lab.hardware.base import HardwareDevice
from iv_lab.hardware.errors import HardwareCommandError
from iv_lab.hardware.smu.base import BaseSMU


class BaseLamp(HardwareDevice):
    """Abstract lamp / solar simulator / filter wheel.

    All drivers share the constructor signature
    ``(settings, smu=None)``; only the Keithley-controlled filter wheel
    uses the SMU (its digital output lines drive the wheel).
    """

    def __init__(
        self,
        settings: LampSettings,
        smu: BaseSMU | None = None,
        name: str = "",
    ) -> None:
        super().__init__(name or settings.display_name or "")
        self.settings = settings
        self.smu = smu
        #: Light level in % sun -> recipe name / wheel angle / filter code
        #: (legacy ``lightLevelDict``; ``None`` only for the manual lamp).
        self.light_level_dict: dict[float, int | float | str] | None = (
            settings.lightLevelDict
        )
        #: Whether the light is currently considered on (legacy ``light_is_on``).
        #: Legacy sets this True after any successful ``light_on`` call,
        #: including at 0 % sun.
        self.light_is_on: bool = False
        #: Last requested light intensity in % sun (legacy ``light_int``).
        self.light_int: float = 100.0

    def _light_level_value(self, light_int: float) -> Any:
        """Look up the lamp-specific value for a light level in % sun.

        Raises :class:`HardwareCommandError` with the legacy Wavelabs
        wording when the level is not defined (the legacy code raised a
        bare ``KeyError`` for the other lamp types).
        """
        if self.light_level_dict is None or light_int not in self.light_level_dict:
            raise HardwareCommandError(
                f'Light intensity "{light_int} % sun" is not defined.'
            )
        return self.light_level_dict[light_int]

    @abstractmethod
    def light_on(self, light_int: float = 100.0) -> None:
        """Turn the light on at ``light_int`` percent of one sun.

        Legacy ``light_on``: sets ``light_is_on`` False on entry and True
        after the hardware action completed without error.
        """

    @abstractmethod
    def light_off(self) -> None:
        """Turn the light off (or move the filter wheel to the dark
        position) and clear ``light_is_on``. Legacy ``light_off``."""

    def turn_off(self) -> None:
        """Final safety cleanup (legacy ``turn_off``).

        The legacy implementation only ever closes a Wavelabs socket that
        was left open mid-command; for every other lamp type it is
        effectively a no-op, which is the default here.
        """
