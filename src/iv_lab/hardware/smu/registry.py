"""Registry of real SMU driver classes.

Drivers register themselves by brand and model with the
:func:`register_smu_driver` decorator; the factory looks them up from the
typed settings. Adding a new SMU then only requires creating the driver
file and registering it (see docs/HARDWARE.md).

Brand and model matching is case-insensitive. The emulated driver is not
registered here — the factory selects it directly when ``emulate`` is set.
"""

from __future__ import annotations

from typing import Callable, TypeVar

from .base import BaseSMU

_SMUDriver = TypeVar("_SMUDriver", bound=type[BaseSMU])

_registry: dict[tuple[str, str], type[BaseSMU]] = {}


def register_smu_driver(brand: str, *models: str) -> Callable[[_SMUDriver], _SMUDriver]:
    """Class decorator registering an SMU driver for one or more models.

    Example::

        @register_smu_driver("Keithley", "2400", "2401", "2450")
        class Keithley2400SMU(BaseSMU):
            ...
    """
    if not models:
        raise ValueError("register_smu_driver requires at least one model")

    def decorator(cls: _SMUDriver) -> _SMUDriver:
        for model in models:
            key = (brand.lower(), model.lower())
            if key in _registry and _registry[key] is not cls:
                raise ValueError(
                    f"SMU driver already registered for brand {brand!r} model {model!r}"
                )
            _registry[key] = cls
        return cls

    return decorator


def get_smu_driver(brand: str, model: str) -> type[BaseSMU]:
    """Return the driver class registered for ``brand`` and ``model``.

    Raises ``ValueError`` for unknown combinations — unlike the legacy
    if/elif dispatch chains, which silently did nothing for unsupported
    hardware.
    """
    try:
        return _registry[(brand.lower(), model.lower())]
    except KeyError:
        raise ValueError(
            f"no SMU driver registered for brand {brand!r} model {model!r}; "
            f"available: {sorted(available_smu_drivers())}"
        ) from None


def available_smu_drivers() -> list[tuple[str, str]]:
    """Return the registered ``(brand, model)`` combinations."""
    return list(_registry)
