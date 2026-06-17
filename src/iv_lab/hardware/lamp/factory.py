"""Factory creating the right lamp driver from typed settings.

Mirrors the SMU factory. The optional ``smu`` argument is passed to the
driver because the Keithley-controlled filter wheel moves via the SMU's
digital output lines (legacy ``lamp(..., smu=self.SMU)``).
"""

from __future__ import annotations

from iv_lab.config import LampSettings
from iv_lab.hardware.smu.base import BaseSMU

from .base import BaseLamp
from .registry import get_lamp_driver


def create_lamp(settings: LampSettings, smu: BaseSMU | None = None) -> BaseLamp:
    """Create a lamp driver instance for the given settings.

    Returns the emulated driver when ``settings.emulate`` is set;
    otherwise looks up the registered real driver for the configured
    brand and model (``ValueError`` if there is none).
    """
    if settings.emulate:
        from .drivers.emulated import EmulatedLamp

        return EmulatedLamp(settings, smu=smu)

    # import driver modules so their registry decorators have run
    from . import drivers  # noqa: F401

    driver_cls = get_lamp_driver(settings.brand, settings.model)
    return driver_cls(settings, smu=smu)
