"""Emulated SMU driver.

Replicates the legacy emulation model built into the legacy ``SMU`` class
(``measure_voltage`` / ``measure_current`` in ``IVLab/IVlab.py``): both
channels behave as an illuminated diode with

- ``Isc = -full_sun_reference_current``,
- ``Voc = 0.55 V``, ``tau = 10``,
- ``i(v) = Isc + K * exp(tau * v - 1)`` with ``K = -Isc / exp(tau * Voc - 1)``,
- readings clipped to the channel compliance limits,
- a simulated integration time of 20 ms per reading.

Extensions over the legacy model (see docs/HARDWARE.md emulation
requirements): optional gaussian current noise (off by default, seeded —
deterministic for tests) and a configurable :attr:`integration_delay`
that tests can set to 0.

Standard library only; no hardware library is imported.
"""

from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass
from typing import Optional

from iv_lab.config import SMUSettings

from ..base import BaseSMU, SMUChannel

#: Legacy emulation constants (IVLab/IVlab.py).
EMULATED_VOC = 0.55
EMULATED_TAU = 10.0
#: Legacy simulated Keithley integration time in s.
LEGACY_INTEGRATION_DELAY = 0.02


@dataclass
class _ChannelState:
    """Per-channel state (legacy ``emulate_*`` dictionaries' defaults)."""

    source_mode: str = "voltage"  # 'voltage' or 'current'
    v_set: float = 0.0
    i_set: float = 0.0
    v_limit: float = 1.0
    i_limit: float = 0.005
    nwire: int = 2
    output: bool = False


class EmulatedSMU(BaseSMU):
    """In-memory SMU presenting a diode-shaped solar cell on both channels."""

    def __init__(self, settings: Optional[SMUSettings] = None) -> None:
        if settings is None:
            name = "Emulated SMU"
        else:
            name = f"Emulated {settings.brand} {settings.model}"
        super().__init__(name)

        self.settings = settings
        if settings is not None:
            self.autorange = settings.autorange
            self.meas_speed = settings.measSpeed
            self.use_reference_diode = settings.useReferenceDiode

        #: Simulated integration time per reading in s; 0 disables waiting.
        self.integration_delay: float = LEGACY_INTEGRATION_DELAY
        #: Gaussian current noise sigma in A; 0 (default) is fully
        #: deterministic, matching the legacy emulation.
        self.current_noise: float = 0.0
        self._noise_rng = random.Random(0)

        self._channels = {
            SMUChannel.CELL: _ChannelState(),
            SMUChannel.REFERENCE: _ChannelState(),
        }

    def seed_noise(self, seed: int) -> None:
        """Re-seed the noise generator for reproducible noisy runs."""
        self._noise_rng = random.Random(seed)

    # --- connection ---

    def _open(self) -> None:
        pass

    def _close(self) -> None:
        # leave the emulated instrument safe, as a real driver would
        self.turn_off()

    # --- diode model ---

    def _isc(self) -> float:
        return -1.0 * self.full_sun_reference_current

    def _k(self) -> float:
        return -self._isc() / math.exp(EMULATED_TAU * EMULATED_VOC - 1)

    def _diode_current(self, channel: SMUChannel) -> float:
        state = self._channels[channel]
        i = self._isc() + self._k() * math.exp(EMULATED_TAU * state.v_set - 1)
        return min(max(i, -state.i_limit), state.i_limit)

    def _diode_voltage(self, channel: SMUChannel) -> float:
        state = self._channels[channel]
        arg = (state.i_set - self._isc()) / self._k()
        if arg <= 0.0:
            # sourcing below Isc; legacy produced nan here, clamp instead
            return -state.v_limit
        v = (math.log(arg) + 1) / EMULATED_TAU
        return min(max(v, -state.v_limit), state.v_limit)

    def _integrate(self) -> None:
        if self.integration_delay > 0:
            time.sleep(self.integration_delay)

    def _noisy(self, current: float) -> float:
        if self.current_noise > 0:
            current += self._noise_rng.gauss(0.0, self.current_noise)
        return current

    # --- compliance and measurement configuration ---

    def set_voltage_limit(self, channel: SMUChannel, voltage: float) -> None:
        self._channels[channel].v_limit = abs(voltage)

    def set_current_limit(self, channel: SMUChannel, current: float) -> None:
        self._channels[channel].i_limit = abs(current)

    def set_sense_mode(self, channel: SMUChannel, nwire: int) -> None:
        self._channels[channel].nwire = int(nwire)

    def setup_voltage_output(self, channel: SMUChannel, current_limit: float) -> None:
        self.set_current_limit(channel, current_limit)
        self._channels[channel].source_mode = "voltage"

    def setup_current_output(self, channel: SMUChannel, voltage_limit: float) -> None:
        self.set_voltage_limit(channel, voltage_limit)
        self._channels[channel].source_mode = "current"

    # --- sourcing ---

    def set_voltage(self, channel: SMUChannel, voltage: float) -> None:
        self._channels[channel].v_set = voltage

    def set_current(self, channel: SMUChannel, current: float) -> None:
        self._channels[channel].i_set = current

    def enable_output(self, channel: SMUChannel) -> None:
        self._channels[channel].output = True

    def disable_output(self, channel: SMUChannel) -> None:
        self._channels[channel].output = False

    # --- measuring ---

    def measure_voltage(self, channel: SMUChannel) -> float:
        state = self._channels[channel]
        self._integrate()
        if state.source_mode == "voltage":
            return state.v_set
        return self._diode_voltage(channel)

    def measure_current(self, channel: SMUChannel) -> float:
        state = self._channels[channel]
        self._integrate()
        if state.source_mode == "current":
            return state.i_set
        return self._noisy(self._diode_current(channel))

    def measure_both_currents(self) -> tuple[float, float]:
        # legacy CHAN_BOTH: both channels in one measurement cycle
        self._integrate()
        results = []
        for channel in (SMUChannel.CELL, SMUChannel.REFERENCE):
            state = self._channels[channel]
            if state.source_mode == "current":
                results.append(state.i_set)
            else:
                results.append(self._noisy(self._diode_current(channel)))
        return (results[0], results[1])

    def measure_iv_point(self, channel: SMUChannel) -> tuple[float, float]:
        # legacy emulation: measure_current then measure_voltage
        return (self.measure_current(channel), self.measure_voltage(channel))

    def measure_both_iv_points(self) -> tuple[float, float, float, float]:
        # legacy CHAN_BOTH current-and-voltage read in one cycle
        self._integrate()
        values: list[float] = []
        for channel in (SMUChannel.CELL, SMUChannel.REFERENCE):
            state = self._channels[channel]
            if state.source_mode == "current":
                i = state.i_set
                v = self._diode_voltage(channel)
            else:
                i = self._noisy(self._diode_current(channel))
                v = state.v_set
            values.extend((i, v))
        return (values[0], values[1], values[2], values[3])

    # --- safety ---

    def turn_off(self) -> None:
        for state in self._channels.values():
            state.output = False

    # --- optional behavior ---

    def set_ttl_level(self, level: int) -> None:
        """Accepted and ignored, as in the legacy emulation mode.

        The legacy ``set_TTL_level`` only talks to the instrument when not
        emulating, so the emulated Keithley filter wheel lamp must not fail.
        """

    # --- introspection helpers for tests and emulated peripherals ---

    def output_enabled(self, channel: SMUChannel) -> bool:
        """Return whether the channel output is enabled."""
        return self._channels[channel].output
