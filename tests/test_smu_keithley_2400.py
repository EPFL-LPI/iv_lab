"""Tests for the Keithley 2400-family driver.

``pymeasure`` is not required: a fake ``pymeasure.instruments.keithley``
module is injected into ``sys.modules`` before connecting, and the driver
only imports pymeasure inside ``_open()``.
"""

import sys
import types

import pytest

from iv_lab.config import SMUSettings
from iv_lab.hardware import HardwareCommandError
from iv_lab.hardware.smu import SMUChannel, create_smu, get_smu_driver

# importing the driver module must not pull in pymeasure (checked below)
from iv_lab.hardware.smu.drivers.keithley_2400 import Keithley2400FamilySMU


def make_settings(**overrides) -> SMUSettings:
    data = {
        "brand": "Keithley",
        "model": "2401",
        "visa_address": "GPIB0::24::INSTR",
        "visa_library": "C:\\Windows\\System32\\visa32.dll",
        "emulate": False,
    }
    data.update(overrides)
    return SMUSettings(**data)


class FakeAdapter:
    def __init__(self) -> None:
        self.closed = False

    def close(self) -> None:
        self.closed = True


class FakeKeithley:
    """Records every attribute assignment and method call."""

    instances: list = []
    fail_on_init = False

    def __init__(self, visa_address: str) -> None:
        object.__setattr__(self, "log", [])
        object.__setattr__(self, "visa_address", visa_address)
        object.__setattr__(self, "adapter", FakeAdapter())
        object.__setattr__(self, "voltage_reading", 0.42)
        object.__setattr__(self, "current_reading", -0.0033)
        if type(self).fail_on_init:
            raise OSError("VISA resource not found")
        type(self).instances.append(self)

    def __setattr__(self, name, value) -> None:
        self.log.append(("set", name, value))
        object.__setattr__(self, name, value)

    def __getattr__(self, name):
        # measurement property reads (never assigned, so __getattr__ fires)
        if name == "voltage":
            self.log.append(("read", "voltage"))
            return self.voltage_reading
        if name == "current":
            self.log.append(("read", "current"))
            return self.current_reading
        raise AttributeError(name)

    def _call(self, name, *args) -> None:
        self.log.append(("call", name) + args)

    def reset(self) -> None:
        self._call("reset")

    def use_front_terminals(self) -> None:
        self._call("use_front_terminals")

    def use_rear_terminals(self) -> None:
        self._call("use_rear_terminals")

    def enable_source(self) -> None:
        self._call("enable_source")

    def disable_source(self) -> None:
        self._call("disable_source")

    def measure_voltage(self, *args) -> None:
        self._call("measure_voltage", *args)

    def measure_current(self, *args) -> None:
        self._call("measure_current", *args)

    def write(self, command: str) -> None:
        self._call("write", command)

    # log helpers
    def calls(self, name: str) -> list:
        return [entry for entry in self.log if entry[0] == "call" and entry[1] == name]

    def writes(self) -> list[str]:
        return [entry[2] for entry in self.calls("write")]

    def sets(self, name: str) -> list:
        return [entry[2] for entry in self.log if entry[0] == "set" and entry[1] == name]


@pytest.fixture
def fake_pymeasure(monkeypatch):
    """Inject fake pymeasure modules; returns the fake instrument classes."""

    class FakeKeithley2400(FakeKeithley):
        instances: list = []
        fail_on_init = False

    class FakeKeithley2450(FakeKeithley):
        instances: list = []
        fail_on_init = False

    keithley_mod = types.ModuleType("pymeasure.instruments.keithley")
    keithley_mod.Keithley2400 = FakeKeithley2400
    keithley_mod.Keithley2450 = FakeKeithley2450
    instruments_mod = types.ModuleType("pymeasure.instruments")
    instruments_mod.keithley = keithley_mod
    pymeasure_mod = types.ModuleType("pymeasure")
    pymeasure_mod.instruments = instruments_mod

    monkeypatch.setitem(sys.modules, "pymeasure", pymeasure_mod)
    monkeypatch.setitem(sys.modules, "pymeasure.instruments", instruments_mod)
    monkeypatch.setitem(sys.modules, "pymeasure.instruments.keithley", keithley_mod)

    return types.SimpleNamespace(
        Keithley2400=FakeKeithley2400, Keithley2450=FakeKeithley2450
    )


def connected_smu(fake_pymeasure, **overrides):
    smu = Keithley2400FamilySMU(make_settings(**overrides))
    smu.connect()
    fake = smu.smu
    fake.log.clear()  # only record what the test itself triggers
    return smu, fake


# --- imports and registration ---


def test_driver_module_import_does_not_import_pymeasure() -> None:
    # the import at the top of this file already imported the driver module
    assert "iv_lab.hardware.smu.drivers.keithley_2400" in sys.modules
    assert "pymeasure" not in sys.modules


def test_driver_registered_for_all_three_models() -> None:
    for model in ("2400", "2401", "2450"):
        assert get_smu_driver("Keithley", model) is Keithley2400FamilySMU


def test_factory_creates_driver_without_pymeasure() -> None:
    smu = create_smu(make_settings(model="2400"))

    assert isinstance(smu, Keithley2400FamilySMU)
    assert not smu.is_connected()
    assert "pymeasure" not in sys.modules  # only imported on connect


# --- connection ---


def test_connect_imports_pymeasure_and_configures_instrument(fake_pymeasure) -> None:
    smu = Keithley2400FamilySMU(make_settings(model="2401", measSpeed="normal"))
    smu.connect()

    assert smu.is_connected()
    assert len(fake_pymeasure.Keithley2400.instances) == 1
    fake = fake_pymeasure.Keithley2400.instances[0]
    assert fake.visa_address == "GPIB0::24::INSTR"

    # legacy connect sequence
    assert fake.calls("reset")
    assert fake.calls("use_front_terminals")
    assert fake.sets("wires") == [2]
    assert fake.sets("voltage_nplc") == [1]
    assert fake.sets("current_nplc") == [1]
    assert fake.sets("source_current_range") == [0.01]
    assert fake.sets("compliance_current") == [0.01]
    assert fake.sets("source_voltage_range") == [2.0]
    assert fake.sets("compliance_voltage") == [2.0]
    assert fake.sets("trigger_delay") == [0.0]
    assert fake.sets("source_delay") == [0.0]
    assert ":SYST:BEEP:STAT OFF" in fake.writes()

    # GPIB interface: legacy measured 1/8.5 minimum period
    assert smu.meas_period_min == pytest.approx(1 / 8.5)


def test_connect_uses_2450_class_and_skips_beep_off(fake_pymeasure) -> None:
    smu = Keithley2400FamilySMU(make_settings(model="2450"))
    smu.connect()

    assert len(fake_pymeasure.Keithley2450.instances) == 1
    assert len(fake_pymeasure.Keithley2400.instances) == 0
    assert ":SYST:BEEP:STAT OFF" not in smu.smu.writes()


def test_serial_interface_measurement_period(fake_pymeasure) -> None:
    smu = Keithley2400FamilySMU(make_settings(visa_address="ASRL2"))
    smu.connect()

    assert smu.meas_period_min == pytest.approx(1 / 6)


def test_fast_meas_speed_sets_nplc(fake_pymeasure) -> None:
    smu = Keithley2400FamilySMU(make_settings(measSpeed="fast"))
    smu.connect()

    assert smu.smu.sets("voltage_nplc") == [0.01]
    assert smu.smu.sets("current_nplc") == [0.01]


def test_failed_connection_leaves_device_disconnected(fake_pymeasure) -> None:
    fake_pymeasure.Keithley2400.fail_on_init = True
    smu = Keithley2400FamilySMU(make_settings())

    with pytest.raises(OSError):
        smu.connect()

    assert not smu.is_connected()


def test_disconnect_disables_source_and_closes_adapter(fake_pymeasure) -> None:
    smu, fake = connected_smu(fake_pymeasure)

    smu.disconnect()

    assert not smu.is_connected()
    assert fake.calls("disable_source")
    assert fake.adapter.closed


# --- sourcing, compliance, measurement ---


def test_setup_voltage_output_replicates_legacy_sequence(fake_pymeasure) -> None:
    smu, fake = connected_smu(fake_pymeasure)

    smu.setup_voltage_output(SMUChannel.CELL, 0.02)

    # compliance and source range (legacy set_current_limit)
    assert fake.sets("source_current_range") == [0.02]
    assert fake.sets("compliance_current") == [0.02]
    # autorange on (settings default autorange=True)
    assert ":CURR:RANG:AUTO ON" in fake.writes()
    # voltage source mode with measure_current configured (nplc=1, autorange)
    assert fake.sets("source_mode") == ["voltage"]
    assert fake.calls("measure_current")[0][2] == 1
    # current display (legacy SYST:KEY 22, non-2450 only)
    assert "SYST:KEY 22" in fake.writes()


def test_setup_voltage_output_fixed_range_when_autorange_off(fake_pymeasure) -> None:
    smu, fake = connected_smu(fake_pymeasure, autorange=False)

    smu.setup_voltage_output(SMUChannel.CELL, 0.02)

    assert ":CURR:RANG:AUTO OFF" in fake.writes()
    assert ":CURR:RANG:AUTO ON" not in fake.writes()
    assert fake.sets("current_range") == [0.02]


def test_set_voltage_and_measure_current(fake_pymeasure) -> None:
    smu, fake = connected_smu(fake_pymeasure)

    smu.set_voltage(SMUChannel.CELL, 0.35)
    assert fake.sets("source_voltage") == [0.35]

    current = smu.measure_current(SMUChannel.CELL)
    assert current == pytest.approx(-0.0033)
    assert ("read", "current") in fake.log


def test_measure_iv_point_returns_set_voltage(fake_pymeasure) -> None:
    # legacy quirk: measured current, but the *set* voltage
    smu, fake = connected_smu(fake_pymeasure)

    smu.set_voltage(SMUChannel.CELL, 0.35)
    i, v = smu.measure_iv_point(SMUChannel.CELL)

    assert i == pytest.approx(-0.0033)
    assert v == pytest.approx(0.35)
    assert ("read", "voltage") not in fake.log


def test_measure_voltage_reads_instrument(fake_pymeasure) -> None:
    smu, fake = connected_smu(fake_pymeasure)

    assert smu.measure_voltage(SMUChannel.CELL) == pytest.approx(0.42)
    assert ("read", "voltage") in fake.log


def test_enable_and_disable_output(fake_pymeasure) -> None:
    smu, fake = connected_smu(fake_pymeasure)

    smu.enable_output(SMUChannel.CELL)
    assert fake.calls("enable_source")

    smu.disable_output(SMUChannel.CELL)
    assert fake.calls("disable_source")


def test_turn_off_disables_source(fake_pymeasure) -> None:
    smu, fake = connected_smu(fake_pymeasure)
    smu.enable_output(SMUChannel.CELL)

    smu.turn_off()

    assert fake.calls("disable_source")


def test_set_sense_mode(fake_pymeasure) -> None:
    smu, fake = connected_smu(fake_pymeasure)

    smu.set_sense_mode(SMUChannel.CELL, 4)
    assert fake.sets("wires") == [4]

    with pytest.raises(HardwareCommandError):
        smu.set_sense_mode(SMUChannel.CELL, 3)


def test_measure_both_currents_not_supported(fake_pymeasure) -> None:
    smu, fake = connected_smu(fake_pymeasure)

    with pytest.raises(HardwareCommandError, match="not supported"):
        smu.measure_both_currents()

    with pytest.raises(HardwareCommandError, match="not supported"):
        smu.measure_both_iv_points()


# --- channel switching (legacy toggle_output_2400) ---


def test_reference_channel_switches_to_rear_terminals(fake_pymeasure) -> None:
    smu, fake = connected_smu(fake_pymeasure)

    smu.set_voltage(SMUChannel.REFERENCE, 0.0)

    # output disabled first, then rear terminals selected
    assert fake.log[0] == ("call", "disable_source")
    assert fake.calls("use_rear_terminals")
    # reference diode sense mode (settings default "2wire" -> 2)
    assert 2 in fake.sets("wires")


def test_same_channel_operations_do_not_toggle(fake_pymeasure) -> None:
    smu, fake = connected_smu(fake_pymeasure)

    smu.set_voltage(SMUChannel.CELL, 0.1)
    smu.set_voltage(SMUChannel.CELL, 0.2)

    assert not fake.calls("use_rear_terminals")
    assert not fake.calls("use_front_terminals")


def test_switching_back_restores_cell_channel_state(fake_pymeasure) -> None:
    smu, fake = connected_smu(fake_pymeasure)

    smu.set_voltage(SMUChannel.CELL, 0.6)
    smu.set_voltage(SMUChannel.REFERENCE, 0.0)
    fake.log.clear()

    smu.set_voltage(SMUChannel.CELL, 0.6)  # triggers toggle back to front

    assert fake.calls("use_front_terminals")
    # the cached cell set-voltage is replayed during the toggle
    assert 0.6 in fake.sets("source_voltage")


# --- TTL / filter wheel ---


def test_set_ttl_level_on_2401(fake_pymeasure) -> None:
    smu, fake = connected_smu(fake_pymeasure, model="2401")

    smu.set_ttl_level(5)

    assert ":SOUR2:TTL:LEV 5" in fake.writes()


def test_set_ttl_level_raises_on_2450(fake_pymeasure) -> None:
    smu, fake = connected_smu(fake_pymeasure, model="2450")

    with pytest.raises(HardwareCommandError):
        smu.set_ttl_level(5)

    assert not fake.writes()
