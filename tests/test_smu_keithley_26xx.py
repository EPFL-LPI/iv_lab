"""Tests for the Keithley 2600/2602 driver.

The local ``Keithley26XX.py`` module is not required: a fake module is
injected into ``sys.modules`` before connecting, and the driver only
imports it inside ``_open()``.
"""

import sys
import types

import pytest

from iv_lab.config import SMUSettings
from iv_lab.hardware import HardwareCommandError
from iv_lab.hardware.smu import SMUChannel, create_smu, get_smu_driver

# importing the driver module must not pull in Keithley26XX (checked below)
from iv_lab.hardware.smu.drivers.keithley_26xx import Keithley26xxSMU


def make_settings(**overrides) -> SMUSettings:
    data = {
        "brand": "Keithley",
        "model": "2602",
        "visa_address": "GPIB0::24::INSTR",
        "visa_library": "C:\\Windows\\System32\\visa32.dll",
        "emulate": False,
    }
    data.update(overrides)
    return SMUSettings(**data)


class FakeChannel:
    """Records every method call made on a SMU26xx channel object."""

    def __init__(self, channel_id: str) -> None:
        self.channel_id = channel_id
        self.log: list[tuple] = []
        self.voltage_reading = 0.5
        self.current_reading = -0.004

    def _call(self, name, *args):
        self.log.append(("call", name) + args)

    def __getattr__(self, name):
        # any recorded channel method (set_voltage, enable_output, ...)
        def method(*args):
            self._call(name, *args)
            if name == "measure_voltage":
                return self.voltage_reading
            if name == "measure_current":
                return self.current_reading
            if name == "measure_current_and_voltage":
                return [self.current_reading, self.voltage_reading]
            return None

        return method

    def calls(self, name: str) -> list:
        return [entry for entry in self.log if entry[1] == name]


class FakeSMU26xx:
    CHANNEL_A = "a"
    CHANNEL_B = "b"

    instances: list = []
    fail_on_init = False

    def __init__(self, visa_resource_name: str, timeout: int = 1000) -> None:
        if type(self).fail_on_init:
            raise OSError("VISA resource not found")
        self.visa_address = visa_resource_name
        self.channels = {"a": FakeChannel("a"), "b": FakeChannel("b")}
        self.disconnected = False
        self.both_current_readings = [-0.004, 0.0063]
        self.both_voltage_readings = [0.5, 0.0]
        type(self).instances.append(self)

    def get_channel(self, channel: str) -> FakeChannel:
        return self.channels[channel]

    def measure_current(self):
        # CHANNEL_ALL read: [i_channel_a, i_channel_b]
        return list(self.both_current_readings)

    def measure_voltage(self):
        return list(self.both_voltage_readings)

    def measure_current_and_voltage(self):
        return [
            self.both_current_readings[0],
            self.both_voltage_readings[0],
            self.both_current_readings[1],
            self.both_voltage_readings[1],
        ]

    def disconnect(self) -> None:
        self.disconnected = True


@pytest.fixture
def fake_keithley26xx(monkeypatch):
    """Inject a fake Keithley26XX module; returns the fake SMU26xx class."""

    class TestSMU26xx(FakeSMU26xx):
        instances: list = []
        fail_on_init = False

    module = types.ModuleType("Keithley26XX")
    module.SMU26xx = TestSMU26xx
    monkeypatch.setitem(sys.modules, "Keithley26XX", module)
    return TestSMU26xx


def connected_smu(fake_cls, **overrides):
    smu = Keithley26xxSMU(make_settings(**overrides))
    smu.connect()
    fake = fake_cls.instances[-1]
    fake.channels["a"].log.clear()  # only record what the test triggers
    fake.channels["b"].log.clear()
    return smu, fake


# --- imports and registration ---


def test_driver_module_import_does_not_import_keithley26xx() -> None:
    assert "iv_lab.hardware.smu.drivers.keithley_26xx" in sys.modules
    assert "Keithley26XX" not in sys.modules


def test_driver_registered_for_2600_and_2602() -> None:
    for model in ("2600", "2602"):
        assert get_smu_driver("Keithley", model) is Keithley26xxSMU


def test_factory_creates_driver_without_connecting() -> None:
    smu = create_smu(make_settings(model="2602"))

    assert isinstance(smu, Keithley26xxSMU)
    assert not smu.is_connected()
    assert "Keithley26XX" not in sys.modules  # only imported on connect


# --- connection ---


def test_connect_imports_and_configures_both_channels(fake_keithley26xx) -> None:
    smu = Keithley26xxSMU(make_settings(measSpeed="normal"))
    smu.connect()

    assert smu.is_connected()
    assert len(fake_keithley26xx.instances) == 1
    fake = fake_keithley26xx.instances[0]
    assert fake.visa_address == "GPIB0::24::INSTR"

    for channel_id in ("a", "b"):
        chan = fake.channels[channel_id]
        # initial fixed ranges (legacy connect)
        assert chan.calls("set_voltage_range") == [("call", "set_voltage_range", 2)]
        assert chan.calls("set_current_range") == [("call", "set_current_range", 0.01)]
        # default autorange=True enables both autoranges
        assert chan.calls("enable_voltage_autorange")
        assert chan.calls("enable_current_autorange")
        # default sense modes are 2-wire ('2 wire' / settings '2wire')
        assert chan.calls("set_sense_2wire")
        assert not chan.calls("set_sense_4wire")
        # normal speed: 20 ms integration
        assert chan.calls("set_measurement_speed_normal")

    assert smu.meas_period_min == pytest.approx(1 / 16)


def test_connect_fast_speed_and_4wire_reference(fake_keithley26xx) -> None:
    smu = Keithley26xxSMU(
        make_settings(measSpeed="fast", referenceDiodeSenseMode="4 wire")
    )
    smu.connect()
    fake = fake_keithley26xx.instances[0]

    assert fake.channels["a"].calls("set_measurement_speed_fast")
    assert fake.channels["b"].calls("set_measurement_speed_fast")
    assert smu.meas_period_min == pytest.approx(1 / 65)
    # channel B sense mode from referenceDiodeSenseMode
    assert fake.channels["b"].calls("set_sense_4wire")
    assert fake.channels["a"].calls("set_sense_2wire")


def test_no_autorange_calls_when_autorange_off(fake_keithley26xx) -> None:
    smu = Keithley26xxSMU(make_settings(autorange=False))
    smu.connect()
    fake = fake_keithley26xx.instances[0]

    for channel_id in ("a", "b"):
        assert not fake.channels[channel_id].calls("enable_voltage_autorange")
        assert not fake.channels[channel_id].calls("enable_current_autorange")


def test_failed_connection_leaves_device_disconnected(fake_keithley26xx) -> None:
    fake_keithley26xx.fail_on_init = True
    smu = Keithley26xxSMU(make_settings())

    with pytest.raises(OSError):
        smu.connect()

    assert not smu.is_connected()


def test_disconnect_calls_smu26xx_disconnect(fake_keithley26xx) -> None:
    smu, fake = connected_smu(fake_keithley26xx)

    smu.disconnect()

    assert not smu.is_connected()
    assert fake.disconnected


# --- channel mapping ---


def test_cell_operations_target_channel_a(fake_keithley26xx) -> None:
    smu, fake = connected_smu(fake_keithley26xx)

    smu.set_voltage(SMUChannel.CELL, 0.35)
    smu.set_current_limit(SMUChannel.CELL, 0.02)
    smu.enable_output(SMUChannel.CELL)

    chan_a, chan_b = fake.channels["a"], fake.channels["b"]
    assert chan_a.calls("set_voltage") == [("call", "set_voltage", 0.35)]
    assert chan_a.calls("set_current_limit") == [("call", "set_current_limit", 0.02)]
    assert chan_a.calls("enable_output")
    assert chan_b.log == []


def test_reference_operations_target_channel_b(fake_keithley26xx) -> None:
    smu, fake = connected_smu(fake_keithley26xx)

    smu.set_voltage(SMUChannel.REFERENCE, 0.0)
    smu.disable_output(SMUChannel.REFERENCE)

    chan_a, chan_b = fake.channels["a"], fake.channels["b"]
    assert chan_b.calls("set_voltage") == [("call", "set_voltage", 0.0)]
    assert chan_b.calls("disable_output")
    assert chan_a.log == []


def test_setup_reference_diode_uses_channel_b(fake_keithley26xx) -> None:
    smu, fake = connected_smu(fake_keithley26xx)
    smu.reference_diode_imax = 0.01

    smu.setup_reference_diode()

    chan_b = fake.channels["b"]
    # legacy: setup_voltage_output(B, Imax) -> set_voltage(B, 0) -> enable_output(B)
    assert chan_b.calls("set_current_limit") == [("call", "set_current_limit", 0.01)]
    assert chan_b.calls("set_mode_voltage_source")
    assert chan_b.calls("set_voltage") == [("call", "set_voltage", 0.0)]
    assert chan_b.calls("enable_output")
    assert fake.channels["a"].log == []


# --- sourcing and measuring ---


def test_setup_voltage_output_replicates_legacy_sequence(fake_keithley26xx) -> None:
    smu, fake = connected_smu(fake_keithley26xx)

    smu.setup_voltage_output(SMUChannel.CELL, 0.02)

    chan_a = fake.channels["a"]
    assert chan_a.calls("set_current_limit") == [("call", "set_current_limit", 0.02)]
    assert chan_a.calls("enable_current_autorange")
    assert chan_a.calls("set_mode_voltage_source")
    # legacy set_mode_voltage_source tail switches the display to current
    assert chan_a.calls("display_current")


def test_measure_voltage_and_current_per_channel(fake_keithley26xx) -> None:
    smu, fake = connected_smu(fake_keithley26xx)
    fake.channels["b"].current_reading = 0.0063

    assert smu.measure_voltage(SMUChannel.CELL) == pytest.approx(0.5)
    assert smu.measure_current(SMUChannel.CELL) == pytest.approx(-0.004)
    assert smu.measure_current(SMUChannel.REFERENCE) == pytest.approx(0.0063)


def test_measure_both_currents_reads_both_channels_in_parallel(
    fake_keithley26xx,
) -> None:
    smu, fake = connected_smu(fake_keithley26xx)
    fake.both_current_readings = [-0.0041, 0.00635]

    i_cell, i_ref = smu.measure_both_currents()

    # legacy CHAN_BOTH: one read through the parent SMU26xx object
    assert i_cell == pytest.approx(-0.0041)
    assert i_ref == pytest.approx(0.00635)
    # the per-channel objects were not used
    assert not fake.channels["a"].calls("measure_current")
    assert not fake.channels["b"].calls("measure_current")


def test_measure_both_iv_points_reads_parent_object(fake_keithley26xx) -> None:
    smu, fake = connected_smu(fake_keithley26xx)
    fake.both_current_readings = [-0.0041, 0.00635]
    fake.both_voltage_readings = [0.51, 0.0]

    i_cell, v_cell, i_ref, v_ref = smu.measure_both_iv_points()

    assert (i_cell, v_cell) == pytest.approx((-0.0041, 0.51))
    assert (i_ref, v_ref) == pytest.approx((0.00635, 0.0))


def test_measure_iv_point_reads_current_and_voltage(fake_keithley26xx) -> None:
    smu, fake = connected_smu(fake_keithley26xx)

    i, v = smu.measure_iv_point(SMUChannel.CELL)

    assert i == pytest.approx(-0.004)
    assert v == pytest.approx(0.5)
    assert fake.channels["a"].calls("measure_current_and_voltage")


def test_set_sense_mode(fake_keithley26xx) -> None:
    smu, fake = connected_smu(fake_keithley26xx)

    smu.set_sense_mode(SMUChannel.CELL, 4)
    assert fake.channels["a"].calls("set_sense_4wire")

    smu.set_sense_mode(SMUChannel.REFERENCE, 2)
    assert fake.channels["b"].calls("set_sense_2wire")

    with pytest.raises(HardwareCommandError):
        smu.set_sense_mode(SMUChannel.CELL, 3)


def test_set_ttl_level_not_supported(fake_keithley26xx) -> None:
    # legacy set_TTL_level raises for anything but the 2400 series
    smu, fake = connected_smu(fake_keithley26xx)

    with pytest.raises(HardwareCommandError):
        smu.set_ttl_level(3)


# --- safety ---


def test_turn_off_disables_both_channels(fake_keithley26xx) -> None:
    smu, fake = connected_smu(fake_keithley26xx)

    smu.turn_off()

    assert fake.channels["a"].calls("disable_output")
    assert fake.channels["b"].calls("disable_output")
