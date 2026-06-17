"""Keithley 2400 / 2401 / 2450 SMU driver (via ``pymeasure``).

Migrated from the 2400-family branches of the legacy ``SMU`` class in
``IVLab/IVlab.py``. ``pymeasure`` is imported only at connection time in
``_open()`` so the package imports without it (see docs/HARDWARE.md).

These instruments have a single physical SMU channel. The legacy code
emulates the two logical channels (cell / reference photodiode) by
switching between the front and rear terminals: every operation that
targets a different channel than the currently active one first runs
``toggle_output_2400`` — output off, switch terminals, replay all cached
per-channel settings, output back on if it was on. That behavior is
preserved here in :meth:`_activate_channel`.

Preserved legacy quirks:

- ``measure_voltage`` / ``measure_current`` do *not* switch channels;
  they read whichever terminals are active (legacy behavior).
- ``measure_iv_point`` returns the *set* voltage with the measured
  current ("2400 doesn't like to read voltage in voltage mode").
- Parallel dual-channel reads (``measure_both_currents``) are not
  possible on this hardware; the reference diode is read by switching
  terminals.
- ``set_ttl_level`` (Keithley filter wheel) exists only on 2400/2401,
  not on the 2450.
- The beep-off command and the front-panel display key commands are not
  sent to the 2450.
- Switching source mode while the output is on briefly disables the
  output (the instrument cannot change mode with output on).
"""

from __future__ import annotations

import contextlib
from dataclasses import dataclass

from iv_lab.config import SMUSettings
from iv_lab.hardware.errors import HardwareCommandError

from ..base import BaseSMU, SMUChannel
from ..registry import register_smu_driver

# Default RS-232 parameters for a serial Keithley 2400.  These must match the
# instrument's front-panel RS-232 settings; override per-machine via the
# ``baud_rate`` / ``read_termination`` / ``write_termination`` settings keys.
# Over GPIB/USB the bus signals end-of-message (EOI), so no termination
# character is needed and these defaults are not applied.
_SERIAL_DEFAULTS = {
    "baud_rate": 9600,
    "read_termination": "\n",   # Keithley COMM menu TERMINATOR <LF> (SCPI default)
    "write_termination": "\n",
}
#: Default VISA read timeout (ms).  Serial reads are slower than GPIB; a too
#: short timeout turns a slow-but-valid read into a spurious VI_ERROR_TMO.
_DEFAULT_TIMEOUT_MS = 5000.0


@dataclass
class _ChannelState:
    """Cached per-channel settings (legacy ``smu_*`` dictionaries' defaults).

    Replayed onto the instrument when switching front/rear terminals.
    """

    v_limit: float = 1.0
    i_limit: float = 0.005
    v_range: float = 5.0
    i_range: float = 0.01
    source_mode: str = "voltage"  # 'voltage' or 'current'
    display_mode: str = "current"
    v_set: float = 0.0
    i_set: float = 0.0
    volt_autorange: bool = True
    curr_autorange: bool = True
    output: bool = False


@register_smu_driver("Keithley", "2400", "2401", "2450")
class Keithley2400FamilySMU(BaseSMU):
    """Keithley 2400-family source meter (2400, 2401, 2450)."""

    def __init__(self, settings: SMUSettings) -> None:
        super().__init__(f"{settings.brand} {settings.model}")
        self.settings = settings
        self.model = settings.model
        self.visa_address = settings.visa_address

        # legacy SMU.__init__ configuration
        self.autorange = settings.autorange
        self.meas_speed = settings.measSpeed
        self.use_reference_diode = settings.useReferenceDiode
        #: Sense mode of the cell channel (legacy ``senseModeA``; the legacy
        #: code never overrides its '2 wire' default from the settings file).
        self.sense_mode_a: str = "2 wire"
        #: Sense mode of the reference diode channel (legacy ``senseModeB``,
        #: from the ``referenceDiodeSenseMode`` setting; anything but
        #: '4 wire' means 2-wire).
        self.sense_mode_b: str = settings.referenceDiodeSenseMode

        self.smu = None  # pymeasure instrument, created in _open()
        self._channels = {
            SMUChannel.CELL: _ChannelState(),
            SMUChannel.REFERENCE: _ChannelState(),
        }
        self._current_channel = SMUChannel.CELL

    # --- connection (legacy connect/disconnect, 2400-family branch) ---

    def _connection_kwargs(self) -> dict:
        """Build the pyvisa connection kwargs for the pymeasure adapter.

        For serial (``ASRL``) addresses, RS-232 needs explicit baud rate and
        termination characters or every read hangs until the VISA timeout
        (GPIB/USB signal end-of-message on the bus, so they need none). The
        defaults come from ``_SERIAL_DEFAULTS`` and can be overridden per
        machine via the settings file. A read ``timeout`` is always applied.
        """
        kwargs: dict = {}
        timeout = self.settings.timeout_ms
        kwargs["timeout"] = _DEFAULT_TIMEOUT_MS if timeout is None else timeout

        if str(self.visa_address)[:4].upper() == "ASRL":
            for key, default in _SERIAL_DEFAULTS.items():
                override = getattr(self.settings, key, None)
                kwargs[key] = default if override is None else override
        return kwargs

    def _open(self) -> None:
        kwargs = self._connection_kwargs()

        # deferred import: must not be loaded at package import time
        if self.model == "2450":
            from pymeasure.instruments.keithley import Keithley2450

            self.smu = Keithley2450(self.visa_address, **kwargs)
        else:
            from pymeasure.instruments.keithley import Keithley2400

            self.smu = Keithley2400(self.visa_address, **kwargs)

        self.smu.reset()
        self.smu.front_terminals_enabled = True
        self._current_channel = SMUChannel.CELL

        self.smu.wires = 4 if self.sense_mode_a == "4 wire" else 2

        # measurement integration time in power line cycles
        if self.meas_speed == "fast":
            self.smu.voltage_nplc = 0.01
            self.smu.current_nplc = 0.01
        elif self.meas_speed == "medium":
            self.smu.voltage_nplc = 0.1
            self.smu.current_nplc = 0.1
        else:  # 'normal'
            self.smu.voltage_nplc = 1
            self.smu.current_nplc = 1

        # measurement speed is limited by the interface on the 2400;
        # legacy measured values for serial vs. GPIB
        if self.visa_address[0:4] == "ASRL":
            self.meas_period_min = 1 / 6
        else:
            self.meas_period_min = 1 / 8.5

        self.smu.source_current_range = 0.01
        self.smu.compliance_current = 0.01
        self.smu.source_voltage_range = 2.0
        self.smu.compliance_voltage = 2.0
        self.smu.trigger_delay = 0.0
        self.smu.source_delay = 0.0

        if self.model != "2450":
            # disable beep sound when output enabled
            self.smu.write(":SYST:BEEP:STAT OFF")

    def _close(self) -> None:
        # no explicit disconnect in pymeasure; disable the output in case
        # it is enabled, then close the adapter (legacy disconnect)
        self.smu.disable_source()
        with contextlib.suppress(Exception):
            self.smu.adapter.close()

    # --- channel switching (legacy toggle_output_2400) ---

    def _activate_channel(self, channel: SMUChannel) -> None:
        """Switch front/rear terminals if ``channel`` is not active."""
        if channel == self._current_channel:
            return
        self._current_channel = channel
        self._toggle_output_2400(channel)

    def _toggle_output_2400(self, channel: SMUChannel) -> None:
        state = self._channels[channel]

        # first disable the sourcemeter output
        self.smu.disable_source()

        # front terminals are the cell, rear terminals the reference diode
        if channel == SMUChannel.CELL:
            self.smu.front_terminals_enabled = True
            sense_mode = self.sense_mode_a
        else:
            self.smu.front_terminals_enabled = False
            sense_mode = self.sense_mode_b
        self.smu.wires = 4 if sense_mode == "4 wire" else 2

        # replay the cached channel settings (legacy order)
        self.set_voltage_limit(channel, state.v_limit)
        self.set_current_limit(channel, state.i_limit)

        if state.curr_autorange:
            self.enable_current_autorange(channel)
        else:
            self.set_current_range(channel, state.i_range)

        if state.volt_autorange:
            self.enable_voltage_autorange(channel)
        else:
            self.set_voltage_range(channel, state.v_range)

        self.set_current(channel, state.i_set)
        self.set_voltage(channel, state.v_set)

        if state.source_mode == "current":
            self.set_mode_current_source(channel)
            self.display_voltage(channel)
        else:
            self.set_mode_voltage_source(channel)
            self.display_current(channel)

        # re-enable the output if it was on before
        if state.output:
            self.enable_output(channel)

    # --- compliance, ranges, autorange ---

    def set_current_limit(self, channel: SMUChannel, current: float) -> None:
        self._activate_channel(channel)
        self.smu.source_current_range = current
        self.smu.compliance_current = current
        self._channels[channel].i_limit = current

    def set_voltage_limit(self, channel: SMUChannel, voltage: float) -> None:
        self._activate_channel(channel)
        self.smu.source_voltage_range = voltage
        self.smu.compliance_voltage = voltage
        self._channels[channel].v_limit = voltage

    def enable_current_autorange(self, channel: SMUChannel) -> None:
        self._activate_channel(channel)
        self.smu.write(":CURR:RANG:AUTO ON")
        self._channels[channel].curr_autorange = True

    def enable_voltage_autorange(self, channel: SMUChannel) -> None:
        self._activate_channel(channel)
        self.smu.write(":VOLT:RANG:AUTO ON")
        self._channels[channel].volt_autorange = True

    def disable_current_autorange(self, channel: SMUChannel) -> None:
        self._activate_channel(channel)
        self.smu.write(":CURR:RANG:AUTO OFF")
        self._channels[channel].curr_autorange = False

    def disable_voltage_autorange(self, channel: SMUChannel) -> None:
        self._activate_channel(channel)
        self.smu.write(":VOLT:RANG:AUTO OFF")
        self._channels[channel].volt_autorange = False

    def set_current_range(self, channel: SMUChannel, current_range: float) -> None:
        # setting a fixed measurement range disables autorange
        self._activate_channel(channel)
        self.smu.current_range = current_range
        self._channels[channel].i_range = current_range

    def set_voltage_range(self, channel: SMUChannel, voltage_range: float) -> None:
        self._activate_channel(channel)
        self.smu.voltage_range = voltage_range
        self._channels[channel].v_range = voltage_range

    # --- source mode (legacy set_mode_*_source) ---

    def set_mode_current_source(self, channel: SMUChannel) -> None:
        self._activate_channel(channel)
        state = self._channels[channel]

        # the 2400 series can't change between voltage and current mode
        # while the output is on; toggle it off and back on around the change
        if state.output:
            self.smu.disable_source()
        self.smu.source_mode = "current"
        # legacy passed its whole range/autorange dicts here, which are
        # always truthy: the effective call is nplc=1 with autoranging on.
        # pymeasure 0.16 deprecated the measure_voltage(nplc, range, auto)
        # config form; configure the equivalent explicitly instead.
        self.smu.voltage_nplc = 1
        self.smu.voltage_range_auto_enabled = True
        if state.output:
            self.smu.enable_source()
        state.source_mode = "current"

        self.display_voltage(channel)

    def set_mode_voltage_source(self, channel: SMUChannel) -> None:
        self._activate_channel(channel)
        state = self._channels[channel]

        if state.output:
            self.smu.disable_source()
        self.smu.source_mode = "voltage"
        # see set_mode_current_source: effectively nplc=1, autorange on.
        # pymeasure 0.16 deprecated the measure_current(nplc, range, auto)
        # config form; configure the equivalent explicitly instead.
        self.smu.current_nplc = 1
        self.smu.current_range_auto_enabled = True
        if state.output:
            self.smu.enable_source()
        state.source_mode = "voltage"

        self.display_current(channel)

    # --- front panel display (legacy display_voltage/display_current) ---

    def display_voltage(self, channel: SMUChannel) -> None:
        self._activate_channel(channel)
        if self.model != "2450":
            self.smu.write("SYST:KEY 15")  # set voltage display
        self._channels[channel].display_mode = "voltage"

    def display_current(self, channel: SMUChannel) -> None:
        self._activate_channel(channel)
        if self.model != "2450":
            self.smu.write("SYST:KEY 22")  # set current display
        self._channels[channel].display_mode = "current"

    # --- setup helpers (legacy setup_voltage_output/setup_current_output) ---

    def setup_voltage_output(self, channel: SMUChannel, current_limit: float) -> None:
        self.set_current_limit(channel, current_limit)
        if self.autorange:
            self.enable_current_autorange(channel)
        else:
            self.disable_current_autorange(channel)
            self.set_current_range(channel, current_limit)
        self.set_mode_voltage_source(channel)

    def setup_current_output(self, channel: SMUChannel, voltage_limit: float) -> None:
        self.set_voltage_limit(channel, voltage_limit)
        if self.autorange:
            self.enable_voltage_autorange(channel)
        else:
            self.disable_voltage_autorange(channel)
            self.set_voltage_range(channel, voltage_limit)
        self.set_mode_current_source(channel)

    # --- sourcing ---

    def set_voltage(self, channel: SMUChannel, voltage: float) -> None:
        self._activate_channel(channel)
        self.smu.source_voltage = voltage
        self._channels[channel].v_set = voltage

    def set_current(self, channel: SMUChannel, current: float) -> None:
        self._activate_channel(channel)
        self.smu.source_current = current
        self._channels[channel].i_set = current

    def enable_output(self, channel: SMUChannel) -> None:
        self._activate_channel(channel)
        self.smu.enable_source()
        self._channels[channel].output = True

    def disable_output(self, channel: SMUChannel) -> None:
        self._activate_channel(channel)
        self.smu.disable_source()
        self._channels[channel].output = False

    # --- sensing ---

    def set_sense_mode(self, channel: SMUChannel, nwire: int) -> None:
        self._activate_channel(channel)
        if int(nwire) not in (2, 4):
            raise HardwareCommandError(
                f"sense mode {nwire} is not supported. Valid values are 2 and 4"
            )
        self.smu.wires = int(nwire)

    # --- measuring (legacy: no channel switch, reads the active terminals) ---

    def measure_voltage(self, channel: SMUChannel) -> float:
        return self.smu.voltage

    def measure_current(self, channel: SMUChannel) -> float:
        return self.smu.current

    def measure_both_currents(self) -> tuple[float, float]:
        raise HardwareCommandError(
            f"{self.name}: parallel cell/reference measurement is not supported; "
            "the 2400 family reads the reference diode by switching terminals"
        )

    def measure_iv_point(self, channel: SMUChannel) -> tuple[float, float]:
        # legacy: "2400 doesn't like to read voltage in voltage mode",
        # so the set voltage is returned instead of a measured one
        return (self.smu.current, self._channels[channel].v_set)

    # --- safety ---

    def turn_off(self) -> None:
        self.smu.disable_source()
        # the legacy code did not update its cached output state here; we
        # mark the outputs off so a later terminal switch cannot silently
        # re-enable the source (physical state is identical)
        for state in self._channels.values():
            state.output = False

    # --- digital lines (legacy set_TTL_level; Keithley filter wheel) ---

    def set_ttl_level(self, level: int) -> None:
        if self.model in ("2400", "2401"):
            self.smu.write(":SOUR2:TTL:LEV " + str(int(level)))
        else:
            # legacy raises for anything but the 2400 series
            super().set_ttl_level(level)
