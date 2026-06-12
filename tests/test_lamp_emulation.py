import sys

import pytest

from iv_lab.config import LampSettings
from iv_lab.hardware import HardwareCommandError, HardwareDevice
from iv_lab.hardware.lamp import (
    BaseLamp,
    available_lamp_drivers,
    create_lamp,
    get_lamp_driver,
    register_lamp_driver,
)
from iv_lab.hardware.lamp.drivers.emulated import EmulatedLamp
from iv_lab.hardware.lamp.drivers.manual import ManualLamp


def make_settings(**overrides) -> LampSettings:
    data = {
        "brand": "Trinamic",
        "model": "TMCM-1260",
        "emulate": True,
        "lightLevelDict": {"100": 17, "55": 77, "12": 137, "0": 257},
    }
    data.update(overrides)
    return LampSettings(**data)


def manual_settings(**overrides) -> LampSettings:
    data = {"brand": "manual", "model": "manual", "emulate": False}
    data.update(overrides)
    return LampSettings(**data)


# --- factory and registry ---


def test_factory_returns_emulated_lamp_when_emulate_true() -> None:
    lamp = create_lamp(make_settings(emulate=True))

    assert isinstance(lamp, EmulatedLamp)
    assert isinstance(lamp, BaseLamp)
    assert isinstance(lamp, HardwareDevice)
    assert lamp.name == "Emulated Trinamic TMCM-1260"


def test_factory_returns_manual_lamp() -> None:
    lamp = create_lamp(manual_settings())

    assert isinstance(lamp, ManualLamp)
    # legacy syst_param generates the display name from brand and model
    assert lamp.name == "manual manual"


def test_factory_is_case_insensitive_for_manual_brand() -> None:
    # legacy code mixed 'manual' and 'Manual'; note that only lowercase
    # 'manual' is exempt from the lightLevelDict requirement (the settings
    # validator replicates the legacy case-sensitive check)
    lamp = create_lamp(
        manual_settings(
            brand="Manual", model="Manual", lightLevelDict={"100": 100, "0": 0}
        )
    )

    assert isinstance(lamp, ManualLamp)


def test_factory_raises_for_unknown_driver() -> None:
    with pytest.raises(ValueError, match="no lamp driver registered"):
        create_lamp(make_settings(emulate=False, brand="NoSuchBrand", model="X"))


def test_factory_does_not_import_hardware_libraries() -> None:
    create_lamp(make_settings(emulate=True))
    create_lamp(manual_settings())

    for module in ("pyvisa", "pymeasure", "pytrinamic", "Keithley26XX"):
        assert module not in sys.modules


def test_registry_register_and_lookup() -> None:
    @register_lamp_driver("TestBrand", "M1")
    class TestLamp(EmulatedLamp):
        pass

    try:
        assert get_lamp_driver("testbrand", "m1") is TestLamp
        assert ("testbrand", "m1") in available_lamp_drivers()

        with pytest.raises(ValueError, match="already registered"):

            @register_lamp_driver("TestBrand", "M1")
            class OtherLamp(EmulatedLamp):
                pass

    finally:
        from iv_lab.hardware.lamp import registry

        registry._registry.pop(("testbrand", "m1"), None)


# --- emulated lamp ---


def test_emulated_lamp_light_on_off_state() -> None:
    lamp = create_lamp(make_settings())
    lamp.connect()

    assert lamp.is_connected()
    assert not lamp.light_is_on

    lamp.light_on(55.0)
    assert lamp.light_is_on
    assert lamp.light_int == 55.0

    lamp.light_off()
    assert not lamp.light_is_on


def test_emulated_lamp_zero_level_still_counts_as_on() -> None:
    # legacy light_on sets light_is_on True even at 0 % sun
    lamp = create_lamp(make_settings())
    lamp.connect()

    lamp.light_on(0.0)

    assert lamp.light_is_on


def test_emulated_lamp_rejects_undefined_light_level() -> None:
    lamp = create_lamp(make_settings())
    lamp.connect()

    with pytest.raises(HardwareCommandError, match="is not defined"):
        lamp.light_on(33.0)

    assert not lamp.light_is_on


def test_emulated_manual_lamp_accepts_any_level() -> None:
    # the manual lamp has no lightLevelDict; nothing to validate against
    lamp = create_lamp(manual_settings(emulate=True))
    lamp.connect()

    lamp.light_on(42.0)

    assert lamp.light_is_on
    assert lamp.light_level_dict is None


def test_emulated_lamp_settings_light_levels_have_float_keys() -> None:
    lamp = create_lamp(make_settings())

    # settings coerced the JSON string keys; lookups use float levels
    assert lamp.light_level_dict == {100.0: 17, 55.0: 77, 12.0: 137, 0.0: 257}


# --- manual lamp ---


def test_manual_lamp_is_a_no_op_with_state() -> None:
    lamp = create_lamp(manual_settings())
    lamp.connect()

    lamp.light_on(100.0)
    assert lamp.light_is_on

    lamp.light_off()
    assert not lamp.light_is_on

    lamp.turn_off()  # no-op, must not raise
    lamp.disconnect()
    assert not lamp.is_connected()
