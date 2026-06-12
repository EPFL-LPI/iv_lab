"""Tests for the real Arduino shutter controller driver.

``pyvisa`` is not required: a fake module is injected into
``sys.modules`` before connecting, and the driver only imports pyvisa
inside ``_open()``.
"""

import sys
import types

import pytest

from iv_lab.config import ArduinoSettings
from iv_lab.hardware import HardwareConnectionError
from iv_lab.hardware.arduino import create_arduino, get_arduino_driver

# importing the driver module must not pull in pyvisa (checked below)
from iv_lab.hardware.arduino.drivers.shutter_controller import (
    BAUD_RATE,
    ArduinoShutterController,
)


def make_settings(**overrides) -> ArduinoSettings:
    data = {
        "brand": "Arduino",
        "model": "Uno",
        "visa_address": "ASRL1::INSTR",
        "visa_library": "C:\\Windows\\System32\\visa32.dll",
        "emulate": False,
    }
    data.update(overrides)
    return ArduinoSettings(**data)


class FakeArduinoResource:
    def __init__(self) -> None:
        self.written: list[str] = []
        self.closed = False
        self.idn = "Newport Corporation,LSS-7120,sn42,rev2"
        self.settings_applied: dict = {}

    def __setattr__(self, name, value) -> None:
        if name not in ("written", "closed", "idn", "settings_applied"):
            self.settings_applied[name] = value
        object.__setattr__(self, name, value)

    def write(self, command: str) -> None:
        self.written.append(command)

    def query(self, command: str) -> str:
        assert command == "*IDN?"
        return self.idn

    def close(self) -> None:
        self.closed = True


@pytest.fixture
def fake_pyvisa(monkeypatch):
    resource = FakeArduinoResource()

    class FakeResourceManager:
        def open_resource(self, address):
            resource.settings_applied["address"] = address
            return resource

    module = types.ModuleType("pyvisa")
    module.ResourceManager = FakeResourceManager
    monkeypatch.setitem(sys.modules, "pyvisa", module)
    return resource


def connected_arduino(fake_pyvisa, **overrides) -> ArduinoShutterController:
    arduino = ArduinoShutterController(make_settings(**overrides))
    arduino.cell_stage_settling_time = 0.0  # skip the legacy 5 s wait
    arduino.connect()
    fake_pyvisa.written.clear()
    return arduino


def test_driver_module_import_does_not_import_pyvisa() -> None:
    assert "iv_lab.hardware.arduino.drivers.shutter_controller" in sys.modules
    assert "pyvisa" not in sys.modules


def test_driver_registered_for_arduino_uno() -> None:
    assert get_arduino_driver("Arduino", "Uno") is ArduinoShutterController


def test_factory_creates_driver_without_connecting() -> None:
    arduino = create_arduino(make_settings())

    assert isinstance(arduino, ArduinoShutterController)
    assert not arduino.is_connected()
    assert "pyvisa" not in sys.modules  # only imported on connect


def test_connect_applies_legacy_serial_settings(fake_pyvisa) -> None:
    arduino = ArduinoShutterController(make_settings())
    arduino.connect()

    assert arduino.is_connected()
    applied = fake_pyvisa.settings_applied
    assert applied["address"] == "ASRL1::INSTR"
    assert applied["baud_rate"] == BAUD_RATE == 115200
    assert applied["read_termination"] == r"\n"
    assert applied["write_termination"] == r"\n"
    assert applied["send_end"] is True
    assert applied["query_delay"] == 0.05
    assert applied["timeout"] == 1000


def test_bad_idn_raises_and_stays_disconnected(fake_pyvisa) -> None:
    fake_pyvisa.idn = "Some Other Device,XYZ"
    arduino = ArduinoShutterController(make_settings())

    with pytest.raises(HardwareConnectionError, match="IDN incorrect"):
        arduino.connect()

    assert not arduino.is_connected()


def test_legacy_digital_commands(fake_pyvisa) -> None:
    arduino = connected_arduino(fake_pyvisa)

    arduino.open_shutter()
    arduino.close_shutter()
    arduino.select_reference_cell()
    arduino.select_test_cell()

    # legacy arduino_digital_command format: "6,<pin>,<value>"
    assert fake_pyvisa.written == ["6,2,1", "6,2,0", "6,4,0", "6,4,1"]


def test_turn_off_closes_shutter(fake_pyvisa) -> None:
    arduino = connected_arduino(fake_pyvisa)

    arduino.turn_off()

    assert fake_pyvisa.written == ["6,2,0"]


def test_command_before_connect_raises() -> None:
    arduino = ArduinoShutterController(make_settings())

    with pytest.raises(HardwareConnectionError, match="not connected"):
        arduino.open_shutter()


def test_disconnect_closes_resource(fake_pyvisa) -> None:
    arduino = connected_arduino(fake_pyvisa)

    arduino.disconnect()

    assert not arduino.is_connected()
    assert fake_pyvisa.closed
