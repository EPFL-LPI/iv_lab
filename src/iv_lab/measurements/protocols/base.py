"""Base class and shared helpers for measurement protocols.

Protocols contain the experiment logic migrated from the legacy
``IVLab/IVlab.py``: each protocol's ``run(params)`` replicates one
legacy ``system.measure_*`` routine end to end (lamp on, light-level
check, scan loop, lamp off) and returns a result dataclass from
``iv_lab.data``.

Protocols are pure Python (no GUI imports). Interaction with the
outside world goes through callbacks, which the Qt workers (step 10 of
docs/MIGRATION.md) connect to signals:

- ``status_callback(message)`` — legacy ``show_status``,
- ``warning_callback(message)`` — legacy non-fatal ``error_window`` uses,
- ``data_callback(data_dict)`` — live data for plotting (legacy
  ``updatePlot*``), called with a protocol-specific dict of arrays,
- ``cancel_callback() -> bool`` — legacy ``abortRunFlag``; protocols
  poll it at the same points the legacy code did and return partial
  data when cancelled.

``params`` dictionaries keep the legacy key names (``light_int``,
``start_V``, ``Imax``, ``Nwire``, ...) since they mirror what the legacy
GUI assembles; each ``run()`` works on its own copy.

Hardware safety: every ``run()`` uses ``try/finally`` to turn the SMU
off and the lamp off (including the IV_Old shutter), even on error or
cancellation — the legacy code did not guarantee this on exceptions.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any

from iv_lab.hardware.arduino.base import BaseArduino
from iv_lab.hardware.lamp.base import BaseLamp
from iv_lab.hardware.smu.base import BaseSMU, SMUChannel


class VocPolarityError(Exception):
    """Wrong Voc polarity detected before a scan (legacy abort case)."""


def _nwire_value(nwire: int | str) -> int:
    """Map the legacy ``Nwire`` parameter to 2 or 4.

    The legacy GUI passes ``'2 wire'`` / ``'4 wire'`` strings; the legacy
    SMU code treated everything but '4 wire' as 2-wire.
    """
    return 4 if "4" in str(nwire) else 2


def linspace(start: float, stop: float, num: int) -> list[float]:
    """Evenly spaced values including both endpoints (like np.linspace)."""
    if num <= 1:
        return [start]
    step = (stop - start) / (num - 1)
    return [start + step * k for k in range(num)]


class MeasurementProtocol(ABC):
    """Base measurement protocol.

    ``system_name`` enables the legacy ``IV_Old`` behavior (shutter and
    reference-diode stage on the Arduino controller).
    """

    def __init__(
        self,
        smu: BaseSMU,
        lamp: BaseLamp,
        arduino: BaseArduino | None = None,
        *,
        system_name: str = "",
        check_voc_before_scan: bool = True,
        status_callback: Callable[[str], None] | None = None,
        warning_callback: Callable[[str], None] | None = None,
        data_callback: Callable[[dict], None] | None = None,
        cancel_callback: Callable[[], bool] | None = None,
    ) -> None:
        self.smu = smu
        self.lamp = lamp
        self.arduino = arduino
        self.system_name = system_name
        #: Legacy ``checkVOCBeforeScan`` system preference.
        self.check_voc_before_scan = check_voc_before_scan

        self._status_callback = status_callback
        self._warning_callback = warning_callback
        self._data_callback = data_callback
        self._cancel_callback = cancel_callback
        self._confirm_callback: Callable[[str, float], bool] | None = None

        #: Legacy ``system.measure_light_intensity`` measured for 5 s.
        self.light_intensity_measure_time = 5.0
        #: Legacy reading interval during the light measurement.
        self.light_intensity_poll_interval = 0.1
        #: Legacy Voc polarity check measured for 1 s at 0.1 s intervals.
        self.voc_check_wait = 1.0
        self.voc_poll_interval = 0.1

    # --- callback plumbing ---

    def set_callbacks(
        self,
        *,
        status: Callable[[str], None] | None = None,
        warning: Callable[[str], None] | None = None,
        data: Callable[[dict], None] | None = None,
        cancel: Callable[[], bool] | None = None,
        confirm: Callable[[str, float], bool] | None = None,
    ) -> None:
        """Attach or replace the interaction callbacks.

        Used by the Qt measurement workers to wire their signals to a
        protocol instance after construction. Only the callbacks passed
        are replaced.
        """
        if status is not None:
            self._status_callback = status
        if warning is not None:
            self._warning_callback = warning
        if data is not None:
            self._data_callback = data
        if cancel is not None:
            self._cancel_callback = cancel
        if confirm is not None:
            self._confirm_callback = confirm

    def status(self, message: str) -> None:
        """Report a status message (legacy ``show_status``)."""
        if self._status_callback is not None:
            self._status_callback(message)

    def warn(self, message: str) -> None:
        """Report a non-fatal warning (legacy warning ``error_window``)."""
        if self._warning_callback is not None:
            self._warning_callback(message)

    def confirm_warning(self, message: str, adjusted_dv: float = 0.0) -> bool:
        """Ask the user to confirm before proceeding after a warning.

        Returns True (proceed) or False (abort). When no confirm callback
        is wired (non-GUI / test use), falls back to warning-and-proceed.

        ``adjusted_dv`` is the new voltage step in volts, or 0 if not
        applicable; passed through to the GUI so the field can be updated.
        """
        if self._confirm_callback is not None:
            return bool(self._confirm_callback(message, adjusted_dv))
        self.warn(message)
        return True

    def emit_data(self, data: dict) -> None:
        """Report live data for plotting (legacy ``updatePlot*``)."""
        if self._data_callback is not None:
            self._data_callback(data)

    def cancelled(self) -> bool:
        """Whether cancellation was requested (legacy ``abortRunFlag``)."""
        if self._cancel_callback is not None:
            return bool(self._cancel_callback())
        return False

    # --- lamp orchestration (legacy system.turn_lamp_on / turn_lamp_off) ---

    @property
    def _is_iv_old(self) -> bool:
        return self.system_name == "IV_Old"

    def turn_lamp_on(self, light_int: float) -> None:
        """Turn the lamp on; on IV_Old also open the shutter.

        Unlike legacy (which caught errors and returned a flag), lamp
        errors propagate; the worker reports them.
        """
        self.lamp.light_on(light_int)
        if self._is_iv_old and self.arduino is not None and light_int > 0.0:
            self.arduino.open_shutter()

    def turn_lamp_off(self) -> None:
        """Turn the lamp off; on IV_Old also close the shutter."""
        self.lamp.light_off()
        if self._is_iv_old and self.arduino is not None:
            self.arduino.close_shutter()

    # --- light intensity (legacy SMU.measureLightIntensity + system wrapper) ---

    def measure_light_intensity(self) -> float:
        """Measure the light level on the reference diode in % sun.

        Legacy behavior: averages reference diode readings over
        ``light_intensity_measure_time`` seconds and scales by the
        full-sun reference current. On IV_Old the reference diode is
        moved into the beam first and the test cell back afterwards.
        Returns -1.0 when cancelled (legacy).
        """
        if self._is_iv_old and self.arduino is not None:
            self.status("Moving Reference Diode Into Measurement Position...")
            self.arduino.select_reference_cell()

        self.status("Measuring Light Intensity on Reference Diode...")

        self.smu.setup_reference_diode()
        readings: list[float] = []
        deadline = time.time() + self.light_intensity_measure_time
        while time.time() < deadline:
            readings.append(self.smu.measure_current(SMUChannel.REFERENCE))
            time.sleep(self.light_intensity_poll_interval)
            if self.cancelled():
                return -1.0
        if not readings:
            readings.append(self.smu.measure_current(SMUChannel.REFERENCE))

        self.smu.disable_output(SMUChannel.REFERENCE)
        average_current = sum(readings) / len(readings)
        light_level = abs(
            100.0 * average_current / self.smu.full_sun_reference_current
        )

        if self._is_iv_old and self.arduino is not None:
            self.status("Moving Test Cell Into Measurement Position...")
            self.arduino.select_test_cell()

        return light_level

    def check_light_level(self, light_int: float) -> float:
        """Measure the light level and warn when it is >10% off (legacy)."""
        light_level = self.measure_light_intensity()
        if self.cancelled():
            return light_level
        if light_int > 1.0 and abs((light_level - light_int) / light_int) > 0.1:
            self.warn(
                "WARNING: Light level measured by reference diode is more "
                "than 10% off from requested level"
            )
        return light_level

    # --- Voc helpers (legacy SMU.measureVoc / checkVOCPolarity) ---

    def measure_voc(self, params: dict, wait: float) -> float:
        """Source 0 A and measure the voltage (legacy ``measureVoc``).

        Returns -1.0 when cancelled (legacy).
        """
        self.smu.setup_current_output(SMUChannel.CELL, params["Vmax"])
        self.smu.set_current(SMUChannel.CELL, 0.0)
        self.smu.enable_output(SMUChannel.CELL)

        deadline = time.time() + wait
        while time.time() < deadline:
            self.smu.measure_voltage(SMUChannel.CELL)
            time.sleep(self.voc_poll_interval)
            if self.cancelled():
                return -1.0

        voltage = self.smu.measure_voltage(SMUChannel.CELL)
        self.smu.disable_output(SMUChannel.CELL)
        return voltage

    def check_voc_polarity(self, params: dict) -> bool:
        """Whether the Voc has the expected polarity (legacy)."""
        return self.measure_voc(params, self.voc_check_wait) >= 0.0

    # --- shared time-keeping ---

    @staticmethod
    def _dwell(measure: Callable[[], Any], dwell_time: float, cancelled: Callable[[], bool]) -> None:
        """Stabilize at the initial operating point (legacy dwell loops)."""
        deadline = time.time() + dwell_time
        while time.time() < deadline:
            measure()
            if cancelled():
                break

    # --- protocol interface ---

    @abstractmethod
    def run(self, params: dict):
        """Run the measurement and return a result dataclass."""
