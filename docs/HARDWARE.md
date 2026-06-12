# Hardware Refactor Guide

This document describes the hardware architecture and safety rules for the IVLab refactor.

---

## Core principle

The application must be able to run in emulation mode without physical hardware and without optional hardware libraries installed.

Therefore:

- do not import hardware libraries at package import time,
- defer optional imports until `connect()` or equivalent methods,
- keep emulated drivers independent of physical hardware packages.

Optional hardware libraries include:

- `pyvisa`,
- `pymeasure`,
- `pytrinamic`,
- local `Keithley26XX.py`.

---

## Hardware package structure

```text
src/iv_lab/hardware/
├── __init__.py
├── base.py
├── errors.py
├── smu/
├── lamp/
└── arduino/
```

Each hardware family should use:

```text
base.py
registry.py
factory.py
drivers/
```

Example:

```text
hardware/smu/
├── base.py
├── registry.py
├── factory.py
└── drivers/
    ├── keithley_2400.py
    ├── keithley_26xx.py
    └── emulated.py
```

---

## Base interface

All hardware devices should implement at least:

```python
class HardwareDevice:
    def connect(self) -> None:
        ...

    def disconnect(self) -> None:
        ...

    def is_connected(self) -> bool:
        ...
```

Device-specific base classes should define the full interface required by measurements.

Do not let measurement protocols depend on concrete driver classes.

---

## Errors

Use hardware-specific exceptions:

```python
class HardwareError(Exception):
    """Base exception for hardware-related errors."""


class HardwareConnectionError(HardwareError):
    """Raised when a device cannot be connected."""


class HardwareCommandError(HardwareError):
    """Raised when a command fails."""
```

Do not hide hardware errors silently.

Errors should be:

- logged,
- propagated to workers,
- emitted to GUI through error signals,
- handled safely with `finally` blocks.

---

## Registry and factory pattern

A hardware driver should register itself with a registry.

A factory should create the correct driver from typed settings.

Adding a new driver should normally require only:

- creating a new driver file,
- registering the driver.

Factory example:

```python
def create_smu(settings: SMUSettings) -> BaseSMU:
    if settings.emulate:
        from iv_lab.hardware.smu.drivers.emulated import EmulatedSMU
        return EmulatedSMU(settings)

    driver_cls = get_smu_driver(settings.brand, settings.model)
    return driver_cls(settings)
```

Important:

The factory may import local driver modules so decorators run, but real hardware libraries must still be deferred inside the drivers.

---

## Deferred imports

Correct:

```python
class Keithley2400SMU(BaseSMU):
    def connect(self) -> None:
        from pymeasure.instruments.keithley import Keithley2400
        self.instrument = Keithley2400(self.settings.visa_address)
```

Incorrect:

```python
from pymeasure.instruments.keithley import Keithley2400


class Keithley2400SMU(BaseSMU):
    ...
```

The incorrect version breaks emulation mode on machines without `pymeasure`.

---

## SMU behavior to preserve

Legacy supported SMUs:

- Keithley 2400,
- Keithley 2401,
- Keithley 2450,
- Keithley 2600,
- Keithley 2602.

Driver families:

- 2400/2401/2450 via `pymeasure`,
- 2600/2602 via local `Keithley26XX.py`.

Important legacy behavior:

- Channel A is the solar cell channel.
- Channel B is the reference photodiode channel for parallel measurement.
- Existing current/voltage ranges and compliance behavior must be preserved.
- Existing autorange behavior must be preserved.
- Output state must be safe after measurements and errors.

The SMU base interface should include methods needed by measurements, for example:

```python
connect()
disconnect()
is_connected()
set_voltage()
set_current()
measure_current()
measure_voltage()
measure_iv_point()
enable_output()
disable_output()
```

The exact interface should be based on the legacy code and measurement needs.

---

## Lamp behavior to preserve

Legacy supported lamp/filter systems:

- manual lamp,
- Wavelabs Sinus70 via TCP socket,
- Oriel LSS-7120 via `pyvisa`,
- Trinamic stepper filter wheel via `pytrinamic`,
- Keithley-controlled filter wheel via SMU digital lines.

Preserve:

- light-level setting behavior,
- filter-wheel behavior,
- calibration-related behavior,
- manual lamp mode,
- behavior when hardware is unavailable,
- legacy timing and settling delays where relevant.

The lamp base interface should include methods such as:

```python
connect()
disconnect()
is_connected()
set_light_level()
get_light_level()
lamp_on()
lamp_off()
```

Only include methods that are actually supported or needed by the application.

---

## Arduino behavior to preserve

Legacy Arduino responsibilities:

- shutter control,
- test/reference cell selection,
- Newport LSS-7120-style protocol.

The Arduino base interface should include methods such as:

```python
connect()
disconnect()
is_connected()
open_shutter()
close_shutter()
select_test_cell()
select_reference_cell()
```

Shutter safety is critical.

If a measurement fails or is cancelled, the shutter should be closed unless the legacy behavior explicitly requires otherwise.

---

## Emulation requirements

Emulated hardware must be realistic enough for development and tests.

Emulated SMU should provide:

- plausible diode-shaped IV data,
- small current noise,
- deterministic mode for tests,
- no dependency on hardware libraries.

Emulated lamp should provide:

- settable light level,
- on/off state,
- plausible status behavior.

Emulated Arduino should provide:

- shutter state,
- selected cell state,
- no serial dependency.

Emulation must support:

- GUI startup,
- J-V scan,
- MPP tracking,
- data saving,
- automated tests.

---

## Hardware safety

All measurement routines touching hardware must use `try/finally`.

Required safety behavior:

- SMU output off after measurements unless explicitly required otherwise.
- Shutter closed after measurements unless explicitly required otherwise.
- Temporary voltage/current states reset safely.
- Connections closed cleanly on shutdown.
- Exceptions must not leave hardware sourcing current or voltage unintentionally.
- Cancellation must leave hardware safe.

Example:

```python
try:
    smu.enable_output()
    arduino.open_shutter()
    run_measurement()
finally:
    arduino.close_shutter()
    smu.disable_output()
```

Real drivers should be conservative. Prefer safe shutdown over convenience.

---

## Real hardware validation

Do not test real hardware until emulation works.

Before real hardware tests:

- verify `system_settings.json`,
- verify voltage/current limits,
- verify compliance settings,
- verify shutter behavior,
- verify lamp state,
- confirm manual access to emergency stop or instrument controls.

During first real hardware tests:

- use short scans,
- use low-risk current/voltage limits,
- monitor instrument state,
- test cancellation,
- test error handling,
- verify output-off behavior.

---

## What not to do

Do not:

- import hardware libraries globally,
- create instruments in GUI classes,
- leave output enabled after errors,
- silently ignore hardware exceptions,
- change the settings JSON format,
- remove emulation support,
- assume all machines have all drivers installed.
