"""Registry of real lamp driver classes.

Same pattern as the SMU registry: drivers register by brand and model
with :func:`register_lamp_driver`; the factory looks them up from typed
settings. Matching is case-insensitive (the legacy code was inconsistent
about brand casing, e.g. ``'manual'`` vs ``'Manual'``).

The emulated driver is not registered; the factory selects it directly
when ``emulate`` is set.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from .base import BaseLamp

_LampDriver = TypeVar("_LampDriver", bound=type[BaseLamp])

_registry: dict[tuple[str, str], type[BaseLamp]] = {}


def register_lamp_driver(brand: str, *models: str) -> Callable[[_LampDriver], _LampDriver]:
    """Class decorator registering a lamp driver for one or more models.

    Example::

        @register_lamp_driver("Trinamic", "TMCM-1260", "TMCM-1160", "TMCM-3110")
        class TrinamicFilterWheelLamp(BaseLamp):
            ...
    """
    if not models:
        raise ValueError("register_lamp_driver requires at least one model")

    def decorator(cls: _LampDriver) -> _LampDriver:
        for model in models:
            key = (brand.lower(), model.lower())
            if key in _registry and _registry[key] is not cls:
                raise ValueError(
                    f"lamp driver already registered for brand {brand!r} model {model!r}"
                )
            _registry[key] = cls
        return cls

    return decorator


def get_lamp_driver(brand: str, model: str) -> type[BaseLamp]:
    """Return the driver class registered for ``brand`` and ``model``.

    Raises ``ValueError`` for unknown combinations — unlike the legacy
    if/elif dispatch chains, which silently did nothing for unsupported
    hardware.
    """
    try:
        return _registry[(brand.lower(), model.lower())]
    except KeyError:
        raise ValueError(
            f"no lamp driver registered for brand {brand!r} model {model!r}; "
            f"available: {sorted(available_lamp_drivers())}"
        ) from None


def available_lamp_drivers() -> list[tuple[str, str]]:
    """Return the registered ``(brand, model)`` combinations."""
    return list(_registry)
