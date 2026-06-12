"""Keithley 2600 / 2602 SMU driver (via the local ``Keithley26XX`` module).

Migrated from the 2602 branches of the legacy ``SMU`` class in
``IVLab/IVlab.py``. The local ``Keithley26XX.py`` driver (historically in
the ``IVLab/`` directory, which must be importable) is imported only at
connection time in ``_open()`` so the package imports without it (see
docs/HARDWARE.md).

Unlike the 2400 family, these instruments have two real SMU channels:

- :attr:`SMUChannel.CELL` maps to legacy channel A (``k``),
- :attr:`SMUChannel.REFERENCE` maps to legacy channel B (``kb``, the
  reference photodiode).

Both channels can be read in the same measurement cycle through the
parent ``SMU26xx`` object (legacy ``CHAN_BOTH``), which is what enables
parallel reference-diode measurement during scans
(``reference_diode_parallel``).
"""

from __future__ import annotations

from iv_lab.config import SMUSettings
from iv_lab.hardware.errors import HardwareCommandError

from ..base import BaseSMU, SMUChannel
from ..registry import register_smu_driver


@register_smu_driver("Keithley", "2600", "2602")
class Keithley26xxSMU(BaseSMU):
    """Keithley 2600-series dual-channel source meter (2600, 2602)."""

    def __init__(self, settings: SMUSettings) -> None:
        super().__init__(f"{settings.brand} {settings.model}")
        self.settings = settings
        self.model = settings.model
        self.visa_address = settings.visa_address

        # legacy SMU.__init__ configuration
        self.autorange = settings.autorange
        self.meas_speed = settings.measSpeed
        self.use_reference_diode = settings.useReferenceDiode
        #: Sense mode of channel A (legacy ``senseModeA``; the legacy code
        #: never overrides its '2 wire' default from the settings file).
        self.sense_mode_a: str = "2 wire"
        #: Sense mode of channel B (legacy ``senseModeB``, from the
        #: ``referenceDiodeSenseMode`` setting; anything but '4 wire'
        #: means 2-wire).
        self.sense_mode_b: str = settings.referenceDiodeSenseMode

        self.smu = None  # SMU26xx instance, created in _open()
        self._channel_objects: dict[SMUChannel, object] = {}

    def _chan(self, channel: SMUChannel):
        """Return the Keithley26XX channel object (legacy ``k`` / ``kb``)."""
        return self._channel_objects[channel]

    # --- connection (legacy connect/disconnect, 2602 branch) ---

    def _open(self) -> None:
        # deferred import: must not be loaded at package import time
        from Keithley26XX import SMU26xx

        self.smu = SMU26xx(self.visa_address)
        self._channel_objects = {
            SMUChannel.CELL: self.smu.get_channel(SMU26xx.CHANNEL_A),
            SMUChannel.REFERENCE: self.smu.get_channel(SMU26xx.CHANNEL_B),
        }

        # initial voltage and current range settings, used if autoranging is off
        for channel in (SMUChannel.CELL, SMUChannel.REFERENCE):
            self._chan(channel).set_voltage_range(2)
            self._chan(channel).set_current_range(0.01)

        if self.autorange:
            for channel in (SMUChannel.CELL, SMUChannel.REFERENCE):
                self.enable_voltage_autorange(channel)
                self.enable_current_autorange(channel)

        # default sense modes; channel B (reference diode) comes from the
        # system settings file
        self._apply_sense_mode(SMUChannel.CELL, self.sense_mode_a)
        self._apply_sense_mode(SMUChannel.REFERENCE, self.sense_mode_b)

        # measurement speed (integration time) and the legacy measured
        # minimum measurement periods
        if self.meas_speed == "fast":
            for channel in (SMUChannel.CELL, SMUChannel.REFERENCE):
                self._chan(channel).set_measurement_speed_fast()  # 200µs
            self.meas_period_min = 1 / 65
        elif self.meas_speed == "medium":
            for channel in (SMUChannel.CELL, SMUChannel.REFERENCE):
                self._chan(channel).set_measurement_speed_med()  # 2ms
            self.meas_period_min = 1 / 50
        else:  # 'normal'
            for channel in (SMUChannel.CELL, SMUChannel.REFERENCE):
                self._chan(channel).set_measurement_speed_normal()  # 20ms
            self.meas_period_min = 1 / 16

    def _close(self) -> None:
        self.smu.disconnect()

    # --- compliance, ranges, autorange ---

    def set_current_limit(self, channel: SMUChannel, current: float) -> None:
        self._chan(channel).set_current_limit(current)

    def set_voltage_limit(self, channel: SMUChannel, voltage: float) -> None:
        self._chan(channel).set_voltage_limit(voltage)

    def enable_current_autorange(self, channel: SMUChannel) -> None:
        self._chan(channel).enable_current_autorange()

    def enable_voltage_autorange(self, channel: SMUChannel) -> None:
        self._chan(channel).enable_voltage_autorange()

    def disable_current_autorange(self, channel: SMUChannel) -> None:
        self._chan(channel).disable_current_autorange()

    def disable_voltage_autorange(self, channel: SMUChannel) -> None:
        self._chan(channel).disable_voltage_autorange()

    def set_current_range(self, channel: SMUChannel, current_range: float) -> None:
        self._chan(channel).set_current_range(current_range)

    def set_voltage_range(self, channel: SMUChannel, voltage_range: float) -> None:
        self._chan(channel).set_voltage_range(voltage_range)

    # --- source mode (legacy set_mode_*_source, including display update) ---

    def set_mode_current_source(self, channel: SMUChannel) -> None:
        self._chan(channel).set_mode_current_source()
        self.display_voltage(channel)

    def set_mode_voltage_source(self, channel: SMUChannel) -> None:
        self._chan(channel).set_mode_voltage_source()
        self.display_current(channel)

    # --- front panel display ---

    def display_voltage(self, channel: SMUChannel) -> None:
        self._chan(channel).display_voltage()

    def display_current(self, channel: SMUChannel) -> None:
        self._chan(channel).display_current()

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
        self._chan(channel).set_voltage(voltage)

    def set_current(self, channel: SMUChannel, current: float) -> None:
        self._chan(channel).set_current(current)

    def enable_output(self, channel: SMUChannel) -> None:
        self._chan(channel).enable_output()

    def disable_output(self, channel: SMUChannel) -> None:
        self._chan(channel).disable_output()

    # --- sensing ---

    def _apply_sense_mode(self, channel: SMUChannel, mode: str) -> None:
        # legacy: anything but '4 wire' selects 2-wire sensing
        if mode == "4 wire":
            self._chan(channel).set_sense_4wire()
        else:
            self._chan(channel).set_sense_2wire()

    def set_sense_mode(self, channel: SMUChannel, nwire: int) -> None:
        if int(nwire) == 4:
            self._chan(channel).set_sense_4wire()
        elif int(nwire) == 2:
            self._chan(channel).set_sense_2wire()
        else:
            raise HardwareCommandError(
                f"sense mode {nwire} is not supported. Valid values are 2 and 4"
            )

    # --- measuring ---

    def measure_voltage(self, channel: SMUChannel) -> float:
        return self._chan(channel).measure_voltage()

    def measure_current(self, channel: SMUChannel) -> float:
        return self._chan(channel).measure_current()

    def measure_both_currents(self) -> tuple[float, float]:
        # legacy measure_current("CHAN_BOTH"): both channels in the same
        # measurement cycle through the parent SMU26xx object, returning
        # [i_channel_a, i_channel_b]
        i_cell, i_ref = self.smu.measure_current()
        return (i_cell, i_ref)

    def measure_iv_point(self, channel: SMUChannel) -> tuple[float, float]:
        # legacy measure_current_and_voltage: channel returns [i, v]
        i, v = self._chan(channel).measure_current_and_voltage()
        return (i, v)

    # --- safety ---

    def turn_off(self) -> None:
        # legacy turn_off for the 2602: disable both channel outputs
        self._chan(SMUChannel.CELL).disable_output()
        self._chan(SMUChannel.REFERENCE).disable_output()
