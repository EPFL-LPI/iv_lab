"""The package must import without optional hardware libraries installed.

Per docs/HARDWARE.md, ``pyvisa``, ``pymeasure``, ``pytrinamic``, and the
local ``Keithley26XX`` module may only be imported inside driver
``connect()``-style methods, never at import time.
"""

import importlib
import sys

import pytest

OPTIONAL_HARDWARE_MODULES = ["pyvisa", "pymeasure", "pytrinamic", "Keithley26XX"]

PACKAGE_MODULES = [
    "iv_lab",
    "iv_lab.config",
    "iv_lab.data",
    "iv_lab.hardware",
    "iv_lab.hardware.base",
    "iv_lab.hardware.errors",
    "iv_lab.hardware.smu",
    "iv_lab.hardware.smu.base",
    "iv_lab.hardware.smu.registry",
    "iv_lab.hardware.smu.factory",
    "iv_lab.hardware.smu.drivers",
    "iv_lab.hardware.smu.drivers.emulated",
    "iv_lab.hardware.smu.drivers.keithley_2400",
    "iv_lab.hardware.smu.drivers.keithley_26xx",
    "iv_lab.hardware.lamp",
    "iv_lab.hardware.lamp.base",
    "iv_lab.hardware.lamp.registry",
    "iv_lab.hardware.lamp.factory",
    "iv_lab.hardware.lamp.drivers",
    "iv_lab.hardware.lamp.drivers.emulated",
    "iv_lab.hardware.lamp.drivers.manual",
    "iv_lab.hardware.lamp.drivers.wavelabs",
    "iv_lab.hardware.lamp.drivers.oriel",
    "iv_lab.hardware.lamp.drivers.trinamic",
    "iv_lab.hardware.lamp.drivers.keithley_filter",
    "iv_lab.hardware.arduino",
    "iv_lab.hardware.arduino.base",
    "iv_lab.hardware.arduino.registry",
    "iv_lab.hardware.arduino.factory",
    "iv_lab.hardware.arduino.drivers",
    "iv_lab.hardware.arduino.drivers.emulated",
    "iv_lab.hardware.arduino.drivers.shutter_controller",
]


@pytest.mark.parametrize("module_name", PACKAGE_MODULES)
def test_import_does_not_load_hardware_libraries(module_name: str) -> None:
    importlib.import_module(module_name)

    loaded = [m for m in OPTIONAL_HARDWARE_MODULES if m in sys.modules]
    assert loaded == [], (
        f"importing {module_name} loaded optional hardware libraries: {loaded}"
    )
