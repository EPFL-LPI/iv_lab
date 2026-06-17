# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

**verasol** is a Python control library and desktop GUI for the **Oriel VeraSol LSS-7120 LED Solar Simulator** — a laboratory instrument for photovoltaic research. It controls 19 individually addressable LED channels (400–1100 nm) via USB using the USBTMC protocol.

## Tech Stack

- Python 3.9+, PySide6 (Qt 6), PyVISA / PyVISA-py
- No build step; no formal test suite (hardware required for testing)

## Running

```bash
# Install dependencies
pip install pyvisa pyvisa-py PySide6

# Launch GUI
python verasol_gui.py

# Use as library
python -c "from verasol import VeraSol; print(VeraSol().identify())"
```

The GUI falls back to a stub mode (UI-only, no hardware) if the instrument is unavailable.

## Architecture

Two files:

**`verasol.py`** — Low-level USBTMC driver. Key classes:
- `VeraSol` — Main instrument class; use as a context manager (`with VeraSol() as lamp`)
- `LampStatus` — Dataclass with decoded status flags (output_on, head_warming_up, head_overtemperature, etc.)
- `LEDInfo` — Per-LED metadata (index, wavelength_nm, power_kw_m2, max_power_kw_m2)
- `CalibrationMode`, `SpectrumMode` — Enums for mode selection
- `list_instruments()` — Module-level function to discover USB VISA resources

**`verasol_gui.py`** — PySide6 desktop control panel (~1357 lines). Key design:
- `InstrumentWorker` runs in a separate `QThread`; all blocking hardware calls go through it
- Worker communicates with GUI exclusively via Qt signals/slots (no direct cross-thread calls)
- Tabs: Output, Spectrum (LED bar chart), Spectrum Memory, Calibration, Diagnostics, Log

## Key Domain Details

- **Amplitude**: 0.1–1.0 suns (1 sun = 1 kW/m²); enforced in `set_amplitude()`
- **LED indices**: 1–24 (only 19 active); validated in `_validate_led_index()`
- **Spectrum memory slots**: 0–10; slot 0 = factory AM1.5G (read-only)
- **Protocol**: Every write command echoes `"Ready"` which `_write()` consumes; queries return stripped strings
- **Warmup**: ~15 min to operating temperature; `wait_for_warmup()` blocks with polling
- **LED self-test**: ~60-second cycle; call `run_led_test()` then `get_led_test_result(led)` per channel
- **User calibration**: `perform_user_calibration()` rescales internal reference to 1.00 sun at the current setpoint
