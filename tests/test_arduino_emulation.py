import sys

import pytest

from iv_lab.config import ArduinoSettings
from iv_lab.hardware import HardwareDevice
from iv_lab.hardware.arduino import (
    BaseArduino,
    available_arduino_drivers,
    create_arduino,
    get_arduino_driver,
    register_arduino_driver,
)
from iv_lab.hardware.arduino.drivers.emulated import EmulatedArduino


def make_settings(**overrides) -> ArduinoSettings:
    data = {
        "brand": "Arduino",
        "model": "Uno",
        "visa_address": "ASRL1::INSTR",
        "visa_library": "C:\\Windows\\System32\\visa32.dll",
        "emulate": True,
    }
    data.update(overrides)
    return ArduinoSettings(**data)


def test_base_arduino_is_abstract() -> None:
    with pytest.raises(TypeError):
        BaseArduino(make_settings())  # type: ignore[abstract]


def test_factory_returns_emulated_arduino_when_emulate_true() -> None:
    arduino = create_arduino(make_settings(emulate=True))

    assert isinstance(arduino, EmulatedArduino)
    assert isinstance(arduino, BaseArduino)
    assert isinstance(arduino, HardwareDevice)
    assert arduino.name == "Emulated Arduino Uno"


def test_factory_raises_for_unknown_driver() -> None:
    with pytest.raises(ValueError, match="no Arduino driver registered"):
        create_arduino(make_settings(emulate=False, brand="NoSuchBrand", model="X"))


def test_factory_emulation_does_not_import_hardware_libraries() -> None:
    create_arduino(make_settings(emulate=True))

    for module in ("pyvisa", "pymeasure", "pytrinamic"):
        assert module not in sys.modules


def test_registry_register_and_lookup() -> None:
    @register_arduino_driver("TestBrand", "M1")
    class TestArduino(EmulatedArduino):
        pass

    try:
        assert get_arduino_driver("testbrand", "m1") is TestArduino
        assert ("testbrand", "m1") in available_arduino_drivers()

        with pytest.raises(ValueError, match="already registered"):

            @register_arduino_driver("TestBrand", "M1")
            class OtherArduino(EmulatedArduino):
                pass

    finally:
        from iv_lab.hardware.arduino import registry

        registry._registry.pop(("testbrand", "m1"), None)


def test_emulated_arduino_tracks_shutter_state() -> None:
    arduino = create_arduino(make_settings())
    arduino.connect()

    assert arduino.is_connected()
    assert not arduino.shutter_is_open

    arduino.open_shutter()
    assert arduino.shutter_is_open

    arduino.close_shutter()
    assert not arduino.shutter_is_open


def test_emulated_arduino_tracks_selected_cell() -> None:
    arduino = create_arduino(make_settings())
    arduino.connect()

    assert arduino.selected_cell == "test"

    arduino.select_reference_cell()
    assert arduino.selected_cell == "reference"

    arduino.select_test_cell()
    assert arduino.selected_cell == "test"


def test_emulated_arduino_turn_off_closes_shutter() -> None:
    arduino = create_arduino(make_settings())
    arduino.connect()
    arduino.open_shutter()

    arduino.turn_off()

    assert not arduino.shutter_is_open


def test_emulated_arduino_has_no_settling_wait() -> None:
    arduino = create_arduino(make_settings())

    assert arduino.cell_stage_settling_time == 0.0
