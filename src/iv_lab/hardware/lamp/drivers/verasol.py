"""VeraSol LSS-7120 LED solar simulator driver.

Uses the low-level USBTMC library in ``_verasol_lib.py``.  Connection is USB
(USBTMC); pyvisa and the Windows IVI USBTMC fallback are loaded inside
``_open()`` only (never at package import time).

The VeraSol accepts a continuous amplitude from 0.1 to 1.0 sun.  The lamp
interface passes ``light_int`` as percent of one sun, so the conversion is::

    amplitude [suns] = light_int [%] / 100

``light_int == 0`` is the dark condition: the output is turned off but
``light_is_on`` is still set ``True`` (consistent with legacy behavior for
other lamp types).  Values between 0 and 10 % exclusive are rejected because
the instrument's minimum amplitude is 0.1 sun (10 %).

No ``lightLevelDict`` is required in the settings: the VeraSol takes any
amplitude in its operating range directly from ``light_int``.
"""

from __future__ import annotations

from iv_lab.config import LampSettings
from iv_lab.hardware.errors import HardwareCommandError, HardwareConnectionError
from iv_lab.hardware.smu.base import BaseSMU

from ..base import BaseLamp
from ..registry import register_lamp_driver

_VERASOL_IDN_HINT = "LSS-7120"
_MIN_SUNS = 0.1   # instrument minimum amplitude


@register_lamp_driver("VeraSol", "LSS-7120")
class VeraSolLamp(BaseLamp):
    """Oriel VeraSol LSS-7120 LED solar simulator (USB/USBTMC)."""

    def __init__(self, settings: LampSettings, smu: BaseSMU | None = None) -> None:
        super().__init__(settings, smu=smu)
        # None / empty string both trigger auto-discovery in _verasol_lib.VeraSol
        self._visa_address: str | None = settings.visa_address or None
        self._lamp = None

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    def _open(self) -> None:
        try:
            from ._verasol_lib import VeraSol
        except ImportError as exc:
            raise HardwareConnectionError(
                "pyvisa is required for the VeraSol lamp: "
                "pip install pyvisa pyvisa-py"
            ) from exc

        try:
            self._lamp = VeraSol(self._visa_address)
            idn = self._lamp.identify()
        except ImportError as exc:
            # pyvisa missing — raised at VeraSol() instantiation time in tests
            raise HardwareConnectionError(
                "pyvisa is required for the VeraSol lamp: "
                "pip install pyvisa pyvisa-py"
            ) from exc
        except RuntimeError as exc:
            raise HardwareConnectionError(str(exc)) from exc

        if _VERASOL_IDN_HINT not in idn:
            self._lamp.close()
            self._lamp = None
            raise HardwareConnectionError(
                f"VeraSol IDN check failed: expected {_VERASOL_IDN_HINT!r} "
                f"in response, got {idn!r}"
            )

    def _close(self) -> None:
        if self._lamp is not None:
            self._lamp.close()
            self._lamp = None

    # ------------------------------------------------------------------
    # Light control
    # ------------------------------------------------------------------

    def light_on(self, light_int: float = 100.0) -> None:
        self.light_is_on = False

        if light_int == 0.0:
            # Dark condition: ensure output is off; still mark as "configured".
            if self._lamp is not None:
                try:
                    self._lamp.set_output(False)
                except RuntimeError as exc:
                    raise HardwareCommandError(str(exc)) from exc
            self.light_int = light_int
            self.light_is_on = True
            return

        suns = light_int / 100.0
        if suns < _MIN_SUNS:
            raise HardwareCommandError(
                f"VeraSol minimum amplitude is {_MIN_SUNS} sun "
                f"({_MIN_SUNS * 100:.0f} %). Requested {light_int:.2f} %."
            )

        try:
            self._lamp.set_amplitude(suns)
            self._lamp.set_output(True)
        except RuntimeError as exc:
            raise HardwareCommandError(str(exc)) from exc

        actual = self._lamp.get_amplitude()
        if abs(actual - suns) > 0.005:
            raise HardwareCommandError(
                f"VeraSol amplitude mismatch: requested {suns:.3f} sun, "
                f"instrument reports {actual:.3f} sun."
            )

        self.light_int = light_int
        self.light_is_on = True

    def light_off(self) -> None:
        if self._lamp is not None:
            try:
                self._lamp.set_output(False)
            except RuntimeError as exc:
                raise HardwareCommandError(str(exc)) from exc
        self.light_is_on = False
