"""Abstract base interface for source meter units (SMUs).

The interface is extracted from the legacy ``SMU`` class in
``IVLab/IVlab.py``: it contains exactly the channel-level primitives that
the legacy measurement routines (``measure_IV_point_by_point``,
``measure_V_time_dependent``, ``measure_I_time_dependent``,
``measure_MPP_time_dependent``, ``measure_reference_calibration``,
``measureVoc``, ``measureVFwd``, ``measureLightIntensity``) call, plus the
safety method ``turn_off``. The high-level routines themselves are *not*
part of this interface — they become measurement protocols in
``measurements/protocols/`` (step 9 of docs/MIGRATION.md).

This module is standard library only. Concrete drivers defer their
hardware library imports (``pymeasure``, local ``Keithley26XX``) into
``_open()`` / hardware-use methods.
"""

from __future__ import annotations

from abc import abstractmethod
from enum import Enum

from iv_lab.hardware.base import HardwareDevice
from iv_lab.hardware.errors import HardwareCommandError


class SMUChannel(Enum):
    """SMU measurement channel.

    Values keep the legacy channel names. Channel A is the solar cell;
    channel B is the reference photodiode for parallel light intensity
    measurement (on the 2400 family, "channel B" is emulated by switching
    between front and back terminals).
    """

    CELL = "CHAN_A"
    REFERENCE = "CHAN_B"


class BaseSMU(HardwareDevice):
    """Abstract source meter unit.

    Legacy mapping notes:

    - Channel arguments replace the legacy ``"CHAN_A"`` / ``"CHAN_B"``
      strings; the legacy ``"CHAN_BOTH"`` reads map to
      :meth:`measure_both_currents`.
    - Configuration attributes mirror the legacy ``SMU.__init__`` values;
      they are overwritten from the settings file by the factory / core
      system in later migration steps.
    """

    def __init__(self, name: str = "") -> None:
        super().__init__(name)

        # configuration (legacy SMU.__init__ defaults, legacy names in comments)
        #: Use measurement autoranging (legacy ``autorange``).
        self.autorange: bool = True
        #: Measurement speed / integration time setting (legacy ``measSpeed``).
        self.meas_speed: str = "normal"
        #: Whether a reference photodiode is installed (legacy ``useReferenceDiode``).
        self.use_reference_diode: bool = True
        #: Whether cell and reference diode can be read in parallel
        #: (legacy ``referenceDiodeParallel``; True only for 2600/2602
        #: systems where the diode is illuminated together with the cell).
        self.reference_diode_parallel: bool = False
        #: Reference diode current at 100% sun, in A
        #: (legacy ``fullSunReferenceCurrent``).
        self.full_sun_reference_current: float = 1.0
        #: Reference diode compliance current in A (legacy ``referenceDiodeImax``).
        self.reference_diode_imax: float = 0.005
        #: Formatted date of the last calibration (legacy ``calibrationDateTime``).
        self.calibration_datetime: str = "Mon, Jan 01 00:00:00 1900"
        #: Minimum achievable measurement period in s (legacy
        #: ``meas_period_min``; overwritten per SMU model on connect).
        self.meas_period_min: float = 1 / 16

    # --- compliance and measurement configuration ---

    @abstractmethod
    def set_voltage_limit(self, channel: SMUChannel, voltage: float) -> None:
        """Set the compliance voltage limit in V (legacy ``set_voltage_limit``)."""

    @abstractmethod
    def set_current_limit(self, channel: SMUChannel, current: float) -> None:
        """Set the compliance current limit in A (legacy ``set_current_limit``)."""

    @abstractmethod
    def set_sense_mode(self, channel: SMUChannel, nwire: int) -> None:
        """Set 2- or 4-wire sensing (legacy ``set_sense_mode``; ``nwire`` is 2 or 4)."""

    @abstractmethod
    def setup_voltage_output(self, channel: SMUChannel, current_limit: float) -> None:
        """Prepare the channel to source voltage and measure current.

        Legacy ``setup_voltage_output``: applies the current compliance
        limit, enables current autoranging (or sets a fixed range equal to
        the limit when ``autorange`` is False), and switches the channel
        to voltage-source mode.
        """

    @abstractmethod
    def setup_current_output(self, channel: SMUChannel, voltage_limit: float) -> None:
        """Prepare the channel to source current and measure voltage.

        Legacy ``setup_current_output``: applies the voltage compliance
        limit, enables voltage autoranging (or sets a fixed range equal to
        the limit when ``autorange`` is False), and switches the channel
        to current-source mode.
        """

    # --- sourcing ---

    @abstractmethod
    def set_voltage(self, channel: SMUChannel, voltage: float) -> None:
        """Set the source voltage in V (legacy ``set_voltage``)."""

    @abstractmethod
    def set_current(self, channel: SMUChannel, current: float) -> None:
        """Set the source current in A (legacy ``set_current``)."""

    @abstractmethod
    def enable_output(self, channel: SMUChannel) -> None:
        """Enable the channel output (legacy ``enable_output``)."""

    @abstractmethod
    def disable_output(self, channel: SMUChannel) -> None:
        """Disable the channel output (legacy ``disable_output``)."""

    # --- measuring ---

    @abstractmethod
    def measure_voltage(self, channel: SMUChannel) -> float:
        """Measure the voltage in V (legacy ``measure_voltage``)."""

    @abstractmethod
    def measure_current(self, channel: SMUChannel) -> float:
        """Measure the current in A (legacy ``measure_current``)."""

    @abstractmethod
    def measure_both_currents(self) -> tuple[float, float]:
        """Measure cell and reference diode currents as ``(i_cell, i_ref)``.

        Legacy ``measure_current("CHAN_BOTH")``, used when
        ``reference_diode_parallel`` is True to read the cell and the
        reference photodiode in the same measurement cycle.
        """

    @abstractmethod
    def measure_iv_point(self, channel: SMUChannel) -> tuple[float, float]:
        """Measure ``(current, voltage)`` in one cycle.

        Legacy ``measure_current_and_voltage``. Note the legacy 2400
        family returns the *set* voltage instead of a measured value when
        sourcing voltage ("2400 doesn't like to read voltage in voltage
        mode"); drivers must preserve that behavior.
        """

    # --- safety ---

    @abstractmethod
    def turn_off(self) -> None:
        """Disable all outputs, leaving the SMU in a safe state.

        Legacy ``turn_off``. Called at the end of every measurement and
        on error/cancellation; must not switch terminals or otherwise
        disturb the instrument beyond disabling the source.
        """

    # --- composed/optional behavior ---

    def measure_both_iv_points(self) -> tuple[float, float, float, float]:
        """Measure ``(i_cell, v_cell, i_ref, v_ref)`` in one cycle.

        Legacy ``measure_current_and_voltage("CHAN_BOTH")``, used by MPP
        tracking when ``reference_diode_parallel`` is True. Only dual
        channel instruments support it; the default mirrors
        :meth:`measure_both_currents` being unavailable.
        """
        raise HardwareCommandError(
            f"{self.name}: parallel cell/reference IV-point measurement is "
            "not supported by this SMU"
        )

    def setup_reference_diode(self) -> None:
        """Prepare channel B to read the reference photodiode.

        Legacy ``setup_reference_diode``: voltage output at 0 V with the
        diode compliance current, output enabled. The diode current is
        then read with ``measure_current(SMUChannel.REFERENCE)``.
        """
        self.setup_voltage_output(SMUChannel.REFERENCE, self.reference_diode_imax)
        self.set_voltage(SMUChannel.REFERENCE, 0.0)
        self.enable_output(SMUChannel.REFERENCE)

    def set_ttl_level(self, level: int) -> None:
        """Set the digital output lines (legacy ``set_TTL_level``).

        Used by the Keithley-controlled filter wheel lamp. Only the 2400
        series supports this; the default implementation mirrors the
        legacy error for unsupported models.
        """
        raise HardwareCommandError(
            f"{self.name}: set_ttl_level is only available for 2400 series sourcemeters"
        )
