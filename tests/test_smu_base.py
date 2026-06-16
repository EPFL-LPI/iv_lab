import pytest

from iv_lab.hardware import HardwareCommandError, HardwareDevice
from iv_lab.hardware.smu import BaseSMU, SMUChannel


class DummySMU(BaseSMU):
    """Minimal in-memory implementation recording calls."""

    def __init__(self) -> None:
        super().__init__("Dummy SMU")
        self.calls: list[tuple] = []

    def _open(self) -> None:
        self.calls.append(("open",))

    def _close(self) -> None:
        self.calls.append(("close",))

    def set_voltage_limit(self, channel: SMUChannel, voltage: float) -> None:
        self.calls.append(("set_voltage_limit", channel, voltage))

    def set_current_limit(self, channel: SMUChannel, current: float) -> None:
        self.calls.append(("set_current_limit", channel, current))

    def set_sense_mode(self, channel: SMUChannel, nwire: int) -> None:
        self.calls.append(("set_sense_mode", channel, nwire))

    def setup_voltage_output(self, channel: SMUChannel, current_limit: float) -> None:
        self.calls.append(("setup_voltage_output", channel, current_limit))

    def setup_current_output(self, channel: SMUChannel, voltage_limit: float) -> None:
        self.calls.append(("setup_current_output", channel, voltage_limit))

    def set_voltage(self, channel: SMUChannel, voltage: float) -> None:
        self.calls.append(("set_voltage", channel, voltage))

    def set_current(self, channel: SMUChannel, current: float) -> None:
        self.calls.append(("set_current", channel, current))

    def enable_output(self, channel: SMUChannel) -> None:
        self.calls.append(("enable_output", channel))

    def disable_output(self, channel: SMUChannel) -> None:
        self.calls.append(("disable_output", channel))

    def measure_voltage(self, channel: SMUChannel) -> float:
        return 0.55

    def measure_current(self, channel: SMUChannel) -> float:
        return -0.005

    def measure_both_currents(self) -> tuple[float, float]:
        return (-0.005, 0.0063)

    def measure_iv_point(self, channel: SMUChannel) -> tuple[float, float]:
        return (-0.005, 0.55)

    def turn_off(self) -> None:
        self.calls.append(("turn_off",))


def test_base_smu_is_abstract() -> None:
    with pytest.raises(TypeError):
        BaseSMU()  # type: ignore[abstract]


def test_partial_implementation_is_still_abstract() -> None:
    class PartialSMU(BaseSMU):
        def _open(self) -> None: ...

        def _close(self) -> None: ...

    with pytest.raises(TypeError):
        PartialSMU()  # type: ignore[abstract]


def test_dummy_smu_implements_interface() -> None:
    smu = DummySMU()

    assert isinstance(smu, BaseSMU)
    assert isinstance(smu, HardwareDevice)

    smu.connect()
    assert smu.is_connected()

    smu.set_voltage(SMUChannel.CELL, 0.1)
    assert smu.measure_current(SMUChannel.CELL) == pytest.approx(-0.005)
    assert smu.measure_both_currents() == pytest.approx((-0.005, 0.0063))
    assert smu.measure_iv_point(SMUChannel.CELL) == pytest.approx((-0.005, 0.55))

    smu.disconnect()
    assert not smu.is_connected()


def test_legacy_configuration_defaults() -> None:
    smu = DummySMU()

    # defaults from legacy SMU.__init__
    assert smu.autorange is True
    assert smu.meas_speed == "normal"
    assert smu.use_reference_diode is True
    assert smu.reference_diode_parallel is False
    assert smu.full_sun_reference_current == 1.0
    assert smu.reference_diode_imax == 0.005
    assert smu.calibration_datetime == "Mon, Jan 01 00:00:00 1900"
    assert smu.meas_period_min == pytest.approx(1 / 16)


def test_smu_channel_keeps_legacy_values() -> None:
    assert SMUChannel.CELL.value == "CHAN_A"
    assert SMUChannel.REFERENCE.value == "CHAN_B"


def test_setup_reference_diode_replicates_legacy_sequence() -> None:
    smu = DummySMU()
    smu.reference_diode_imax = 0.01

    smu.setup_reference_diode()

    # legacy: setup_voltage_output(B, Imax) -> set_voltage(B, 0) -> enable_output(B)
    assert smu.calls == [
        ("setup_voltage_output", SMUChannel.REFERENCE, 0.01),
        ("set_voltage", SMUChannel.REFERENCE, 0.0),
        ("enable_output", SMUChannel.REFERENCE),
    ]


def test_set_ttl_level_unsupported_by_default() -> None:
    # legacy set_TTL_level raises for anything but the 2400 series
    with pytest.raises(HardwareCommandError):
        DummySMU().set_ttl_level(3)
