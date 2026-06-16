"""Factory creating the right Arduino driver from typed settings."""

from __future__ import annotations

from iv_lab.config import ArduinoSettings

from .base import BaseArduino
from .registry import get_arduino_driver


def create_arduino(settings: ArduinoSettings) -> BaseArduino:
    """Create an Arduino driver instance for the given settings.

    Returns the emulated driver when ``settings.emulate`` is set;
    otherwise looks up the registered real driver for the configured
    brand and model (``ValueError`` if there is none).
    """
    if settings.emulate:
        from .drivers.emulated import EmulatedArduino

        return EmulatedArduino(settings)

    # import driver modules so their registry decorators have run
    from . import drivers  # noqa: F401

    driver_cls = get_arduino_driver(settings.brand, settings.model)
    return driver_cls(settings)
