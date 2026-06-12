"""Factory creating the right SMU driver from typed settings.

The factory may import local driver modules (so registry decorators run),
but real hardware libraries stay deferred inside the drivers' connection
methods (see docs/HARDWARE.md).
"""

from __future__ import annotations

from iv_lab.config import SMUSettings

from .base import BaseSMU
from .registry import get_smu_driver


def create_smu(settings: SMUSettings) -> BaseSMU:
    """Create an SMU driver instance for the given settings.

    Returns the emulated driver when ``settings.emulate`` is set;
    otherwise looks up the registered real driver for the configured
    brand and model (``ValueError`` if there is none).
    """
    if settings.emulate:
        from .drivers.emulated import EmulatedSMU

        return EmulatedSMU(settings)

    # import driver modules so their registry decorators have run
    from . import drivers  # noqa: F401

    driver_cls = get_smu_driver(settings.brand, settings.model)
    return driver_cls(settings)
