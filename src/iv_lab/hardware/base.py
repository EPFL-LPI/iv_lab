"""Common base class for all hardware devices (SMU, lamp, Arduino).

Defines the connection lifecycle shared by every device. Device-specific
base classes (``hardware/smu/base.py``, ``hardware/lamp/base.py``,
``hardware/arduino/base.py``) extend this with the full interface required
by the measurement protocols.

This module is standard library only. Optional hardware libraries
(``pyvisa``, ``pymeasure``, ``pytrinamic``, local ``Keithley26XX``) must be
imported by concrete drivers inside their ``_open()`` (or other
hardware-use) methods, never at module level — the package must import in
emulation mode without them installed (see docs/HARDWARE.md).
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class HardwareDevice(ABC):
    """Abstract base class for a connectable hardware device.

    Subclasses implement :meth:`_open` and :meth:`_close`; the public
    :meth:`connect` / :meth:`disconnect` methods manage the connection
    state around them:

    - ``connect()`` on an already connected device disconnects first and
      reconnects (the legacy ``SMU.connect`` / ``arduino.connect``
      re-connect behavior).
    - If ``_open()`` raises, the device is left disconnected.
    - ``disconnect()`` always ends with the device marked disconnected,
      even if ``_close()`` raises.

    Drivers should raise :class:`~iv_lab.hardware.errors.HardwareError`
    subclasses for hardware failures (e.g.
    :class:`~iv_lab.hardware.errors.HardwareConnectionError` from
    ``_open()``).
    """

    def __init__(self, name: str = "") -> None:
        #: Human-readable device name used in status and error messages.
        self.name = name or type(self).__name__
        self._connected = False

    def connect(self) -> None:
        """Open the connection to the device.

        Reconnects if the device is already connected.
        """
        if self._connected:
            self.disconnect()
        self._open()
        self._connected = True

    def disconnect(self) -> None:
        """Close the connection to the device.

        Does nothing if the device is not connected. The device is marked
        disconnected even if closing the underlying connection fails.
        """
        if not self._connected:
            return
        try:
            self._close()
        finally:
            self._connected = False

    def is_connected(self) -> bool:
        """Return whether the device is currently connected."""
        return self._connected

    @abstractmethod
    def _open(self) -> None:
        """Open the underlying connection.

        Concrete drivers import their optional hardware libraries here
        (deferred imports) and establish the instrument connection.
        Emulated drivers typically do nothing.
        """

    @abstractmethod
    def _close(self) -> None:
        """Close the underlying connection.

        Emulated drivers typically do nothing.
        """
