"""Manual lamp driver.

Legacy brand ``manual``: the user operates the lamp by hand and the GUI
shows the manual light-level controls. Every hardware action is a no-op;
only the ``light_is_on`` bookkeeping is kept (legacy ``light_on`` /
``light_off`` fall through all brand branches and just set the flag).

The manual lamp has no ``lightLevelDict`` (the only brand exempted in
the settings validation).
"""

from __future__ import annotations

from ..base import BaseLamp
from ..registry import register_lamp_driver


@register_lamp_driver("manual", "manual")
class ManualLamp(BaseLamp):
    """Lamp operated by hand; no hardware control."""

    def _open(self) -> None:
        pass

    def _close(self) -> None:
        pass

    def light_on(self, light_int: float = 100.0) -> None:
        self.light_is_on = False
        self.light_int = light_int
        self.light_is_on = True

    def light_off(self) -> None:
        self.light_is_on = False
