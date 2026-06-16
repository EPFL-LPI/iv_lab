"""Hardware-specific exceptions.

A simple, flat hierarchy: every hardware problem derives from
:class:`HardwareError`, so callers (measurement protocols, workers, the
core system) can catch all hardware failures with a single ``except``
clause while still distinguishing specific cases when needed.

Per docs/HARDWARE.md, hardware errors must never be silently hidden:
drivers raise them, workers propagate them, and the GUI receives them
through error signals.
"""

from __future__ import annotations


class HardwareError(Exception):
    """Base exception for hardware-related errors."""


class HardwareConnectionError(HardwareError):
    """Raised when a device cannot be connected or the connection is lost."""


class HardwareCommandError(HardwareError):
    """Raised when a device command fails or returns an invalid response."""


class HardwareTimeoutError(HardwareError):
    """Raised when a device does not respond within the expected time."""


class HardwareSafetyError(HardwareError):
    """Raised when a device cannot be brought into a safe state.

    Examples: SMU output cannot be disabled, or a shutter cannot be
    closed after a measurement, an error, or a cancellation.
    """
