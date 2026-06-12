# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## What this is

PySide6 GUI application for IV (current–voltage) characterization of solar cells in the EPFL LPI optoelectronics lab. It drives a source meter unit (SMU), a lamp/solar simulator, and optionally an Arduino-based shutter, and runs J-V scans, constant-voltage, constant-current, and maximum-power-point (MPP) measurements.

This repository is currently being refactored from a monolithic PyQt5 structure into a modern modular PySide6 architecture. The original files (`IVLab/IVlab.py`, `IVLab/IV_gui.py`) are the source of truth for existing behavior. Do not delete them until the new structure runs end-to-end.

---

## Current state (legacy — do not modify these files)

- `IVLab/IVlab.py` (~3600 lines) — monolithic controller: hardware classes (SMU, lamp, arduino), system orchestrator
- `IVLab/IV_gui.py` (~1600 lines) — monolithic PyQt5 GUI
- `IVLab/system_settings.json` — per-machine hardware config (format must not change)

Note: `README.md` and `setup.py` describe a planned refactored package that does not yet exist. Ignore them.

### Running the legacy app (reference only)

```
cd IVLab
python IVlab.py            # GUI mode
python IVlab.py --nogui    # command-line mode
```

### Legacy architecture (for migration reference)

- `syst_param` — wraps the settings JSON.
- `SMU` — one class for all SMUs, dispatching on brand/model chains. Two families: 2400/2401/2450 via `pymeasure`, and 2600/2602 via local `Keithley26XX.py`. Channel A = cell, channel B = reference photodiode for parallel measurement.
- `lamp` — dispatch over brands: `manual`, `Wavelabs` Sinus70 (TCP), `Oriel` LSS-7120 (pyvisa), `Trinamic` stepper filter wheels (pytrinamic), `keithley filter wheel` (via SMU digital lines).
- `arduino` — shutter and test/reference cell selection (Newport LSS-7120 protocol).
- `system` — top-level orchestrator: composes hardware, user login/logout with logbook, measurement routines, calibration, data saving.

Hardware driver imports (pymeasure, pyvisa, pytrinamic, Keithley26XX) are deferred until `connect()` so the app runs without drivers when emulating.

---

## Target structure (refactoring goal)

```
iv_lab/
├── main.py                        # Entry point only — init QApplication, load settings, launch window
├── system_settings.json           # Unchanged format
│
├── config/
│   └── settings.py                # Load & validate system_settings.json; raise clear errors for missing keys
│
├── hardware/
│   ├── base.py                    # Abstract base class: HardwareDevice (connect, disconnect, emulate flag)
│   ├── smu/
│   │   ├── __init__.py            # Factory: create_smu(settings) → BaseSMU
│   │   ├── base_smu.py            # Abstract SMU interface (ABC)
│   │   ├── keithley_2400.py       # Keithley 2400/2401/2450 via pymeasure
│   │   ├── keithley_26xx.py       # Keithley 2600/2602 via Keithley26XX.py (dual-channel)
│   │   └── emulated_smu.py        # Emulation — no pyvisa/pymeasure required
│   ├── lamp/
│   │   ├── __init__.py            # Factory: create_lamp(settings) → BaseLamp
│   │   ├── base_lamp.py           # Abstract lamp interface (ABC)
│   │   ├── wavelabs.py            # Wavelabs Sinus70 (TCP socket)
│   │   ├── oriel.py               # Oriel LSS-7120 (pyvisa)
│   │   ├── trinamic.py            # Trinamic stepper filter wheel (pytrinamic)
│   │   ├── keithley_filter.py     # Keithley-driven filter wheel (via SMU digital lines)
│   │   ├── manual_lamp.py         # Manual — user sets lamp physically
│   │   └── emulated_lamp.py       # Emulation
│   └── arduino/
│       ├── __init__.py            # Factory: create_arduino(settings) → BaseArduino
│       ├── base_arduino.py        # Abstract interface: shutter_open/close, select_cell
│       └── shutter_controller.py  # Newport LSS-7120 protocol implementation
│
├── measurements/
│   ├── base_measurement.py        # Abstract QThread subclass with signals: data_ready, status_update, finished, error
│   ├── iv_curve.py                # J-V sweep (forward + reverse)
│   ├── constant_voltage.py        # Constant V vs time
│   ├── constant_current.py        # Constant I vs time
│   ├── mpp_tracking.py            # MPP tracking
│   └── calibration.py             # Reference diode calibration
│
├── data/
│   ├── results.py                 # Dataclasses: IVResults, MPPResults, CalibrationResults, etc.
│   ├── file_writer.py             # All disk I/O: CSV/data files, log file, scrambled duplicate copy
│   └── pdf_report.py              # PDF report generation (migrated from system.generate_JV_Results_PDF)
│
├── gui/
│   ├── app.py                     # QApplication setup (PySide6)
│   ├── main_window.py             # Main window — composes all panels
│   ├── panels/
│   │   ├── measurement_panel.py   # IV, MPP, constant V/I controls and parameter inputs
│   │   ├── light_panel.py         # Light level controls
│   │   ├── plot_panel.py          # All pyqtgraph plot widgets
│   │   └── calibration_panel.py   # Calibration controls
│   └── dialogs/
│       └── logoff_dialog.py       # LogOffDialog (and future dialogs)
│
└── core/
    └── system.py                  # Orchestrator: wires hardware + measurements + GUI signals
```

---

## Rules Claude Code must always follow

### 1. Hardware abstraction
- Every hardware type (SMU, lamp, arduino) has an abstract base class (ABC) defining the full interface.
- Concrete implementations are selected at runtime by a factory function in each `hardware/<type>/__init__.py`.
- The factory reads `system_settings.json`: `brand` + `model` + `emulate` flag determine which class to instantiate.
- **Adding new hardware = add one new file + one `elif` in the factory. No other files change.**
- Emulation mode must work with zero physical hardware and without pyvisa/pymeasure/pytrinamic installed.
- All hardware driver imports (pyvisa, pymeasure, pytrinamic, Keithley26XX) stay deferred inside `connect()`.

### 2. GUI framework
- **PySide6 only** — no PyQt5 anywhere in new code.
- pyqtgraph is used for all plots (compatible with PySide6).
- **No `app.processEvents()` anywhere** — replace all such patterns with proper QThread workers.
- All GUI updates from measurement threads must go through Qt signals/slots.
- Panels are self-contained QWidget subclasses composed in `main_window.py`.

### 3. Measurements
- Each measurement is a `QThread` subclass defined in its own file.
- Required signals on every measurement: `data_ready`, `status_update`, `finished`, `error`.
- Measurements receive hardware objects (SMU, lamp, arduino) via constructor — no hardware creation inside measurements.
- **No GUI imports in `measurements/` or `hardware/`** — direction of dependency is always: gui → core → measurements → hardware.

### 4. Data
- Use Python `dataclasses` for all result objects (IVResults, MPPResults, etc.).
- All disk I/O goes through `data/file_writer.py` — no open() calls scattered elsewhere.
- Existing data file format must be preserved for backward compatibility.
- Scrambled duplicate copy logic (sdPath) and log file (ivlablog.txt) must be preserved.

### 5. Configuration
- `system_settings.json` format is frozen — do not change key names or structure.
- `config/settings.py` validates on load and raises `ValueError` with a clear message for any missing required key.
- Per-machine settings are gitignored; template files (`system_settings_*.json`) are committed.

### 6. General coding rules
- Type hints on all function signatures.
- Docstrings on all classes and public methods.
- No wildcard imports (`from x import *`).
- Each file has a single clear responsibility — if a file is doing two things, split it.

---

## Migration strategy — work in this order

Migrate one module at a time. Keep original files untouched until the new structure runs end-to-end. Commit after each working module.

1. **`config/settings.py`** — load and validate system_settings.json
2. **`hardware/smu/`** — most complex; validate with emulation before moving on
3. **`hardware/lamp/`**
4. **`hardware/arduino/`**
5. **`data/results.py`** — dataclasses first, no dependencies
6. **`data/file_writer.py`** and **`data/pdf_report.py`**
7. **`measurements/`** — one measurement class at a time, starting with `iv_curve.py`
8. **`gui/`** — last, after all logic works headlessly
9. **`core/system.py`** — wire everything together
10. **`main.py`** — thin entry point

### How to validate each step
- Hardware modules: run with `emulate: true` in settings, confirm no import errors and correct method calls
- Measurements: run headlessly (`python -m iv_lab.measurements.iv_curve --emulate`) before connecting GUI
- GUI: test against emulated hardware before connecting real instruments

---

## Hardware emulation

Every hardware section in `system_settings.json` has an `"emulate": true/false` flag. When `true`:
- The factory returns the `Emulated*` class instead of the real driver.
- No pyvisa/pymeasure/pytrinamic imports occur.
- Emulated classes return realistic dummy data (sine-shaped IV curves, random noise on currents).

---

## Users and authentication

- `users.txt` — scrambled JSON: lowercase username → password, created via `system.scramble_string`.
- Blank username with password `123456` logs in as generic `user`.
- Calibration is only enabled for specific hardcoded usernames (preserve this behavior exactly).

---

## External dependencies to preserve

- `bric_analysis_libraries.jv.jv_analysis` — used for Voc, Jsc, FF, PCE calculation. Do not reimplement.
- `pyqtgraph` — all plots.
- `pymeasure` — Keithley 2400 family.
- `Keithley26XX.py` (local) — Keithley 2600 family.
- `pytrinamic` — Trinamic stepper motor filter wheels.
- `pyvisa` — Oriel lamp and arduino communication.
