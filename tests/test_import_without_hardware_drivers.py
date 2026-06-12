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
]


@pytest.mark.parametrize("module_name", PACKAGE_MODULES)
def test_import_does_not_load_hardware_libraries(module_name: str) -> None:
    importlib.import_module(module_name)

    loaded = [m for m in OPTIONAL_HARDWARE_MODULES if m in sys.modules]
    assert loaded == [], (
        f"importing {module_name} loaded optional hardware libraries: {loaded}"
    )
