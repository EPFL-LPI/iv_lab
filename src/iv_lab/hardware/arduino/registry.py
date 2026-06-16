"""Registry of real Arduino driver classes.

Same pattern as the SMU and lamp registries: drivers register by brand
and model with :func:`register_arduino_driver`; the factory looks them
up from typed settings. Matching is case-insensitive. The emulated
driver is not registered; the factory selects it directly.
"""

from __future__ import annotations

from typing import Callable, TypeVar

from .base import BaseArduino

_ArduinoDriver = TypeVar("_ArduinoDriver", bound=type[BaseArduino])

_registry: dict[tuple[str, str], type[BaseArduino]] = {}


def register_arduino_driver(
    brand: str, *models: str
) -> Callable[[_ArduinoDriver], _ArduinoDriver]:
    """Class decorator registering an Arduino driver for one or more models."""
    if not models:
        raise ValueError("register_arduino_driver requires at least one model")

    def decorator(cls: _ArduinoDriver) -> _ArduinoDriver:
        for model in models:
            key = (brand.lower(), model.lower())
            if key in _registry and _registry[key] is not cls:
                raise ValueError(
                    f"Arduino driver already registered for brand {brand!r} "
                    f"model {model!r}"
                )
            _registry[key] = cls
        return cls

    return decorator


def get_arduino_driver(brand: str, model: str) -> type[BaseArduino]:
    """Return the driver class registered for ``brand`` and ``model``.

    Raises ``ValueError`` for unknown combinations.
    """
    try:
        return _registry[(brand.lower(), model.lower())]
    except KeyError:
        raise ValueError(
            f"no Arduino driver registered for brand {brand!r} model {model!r}; "
            f"available: {sorted(available_arduino_drivers())}"
        ) from None


def available_arduino_drivers() -> list[tuple[str, str]]:
    """Return the registered ``(brand, model)`` combinations."""
    return list(_registry)
