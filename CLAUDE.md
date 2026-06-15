# CLAUDE.md

This file gives Claude Code mandatory instructions for working on this repository.

For architecture details, see:

- `docs/ARCHITECTURE.md`
- `docs/HARDWARE.md`
- `docs/TESTING.md`

---

## Project

This repository contains a GUI application for IV (current-voltage) characterization of solar cells in the EPFL LPI optoelectronics lab.

The application controls:

- source meter units (SMUs),
- lamps / solar simulators / filter wheels,
- optionally an Arduino-based shutter or cell-selection controller,

and supports:

- J-V scans,
- constant-voltage measurements,
- constant-current measurements,
- maximum-power-point tracking,
- calibration routines,
- data saving,
- PDF report generation,
- user login/logout and logbook behavior.

The refactor from the monolithic PyQt5 application to a modular PySide6 package is **complete**. The new package is `src/iv_lab/` and is the primary codebase going forward.

---

## Legacy files

The legacy application lives in `IVLab/`:

- `IVLab/IVlab.py` — legacy backend
- `IVLab/IV_gui.py` — legacy GUI

Do not delete or modify these files. They remain as behavioral reference and as a working fallback.

---

## Package structure

```text
pyproject.toml

config/
├── system_settings_example.json   # emulation-ready template (committed)
├── system_settings.json           # machine-specific runtime file (gitignored)
├── users_generic.txt              # user table template (committed)
└── users.txt                      # machine-specific live users (gitignored)

src/
└── iv_lab/
    ├── __init__.py
    ├── main.py
    ├── config/       # settings.py — Pydantic v2 models for system_settings.json
    ├── hardware/     # SMU, lamp, Arduino — base, registry, factory, drivers
    ├── measurements/ # protocols/ (pure logic) + workers/ (Qt wrappers)
    ├── analysis/     # jv_metrics.py + bundled jv_analysis.py
    ├── data/         # results.py, file_writer.py, pdf_report.py
    ├── services/     # auth.py, logbook.py
    ├── core/         # system.py — application orchestration
    └── gui/          # app.py, main_window.py, panels/, dialogs/

tests/
docs/
```

---

## Golden rules

1. Preserve legacy behavior unless explicitly asked to change it.
2. Do not modify `IVLab/IVlab.py` or `IVLab/IV_gui.py`.
3. Do not change the structure or key names of `system_settings.json`.
4. New GUI code must use PySide6 only. No PyQt5 in new code.
5. Emulation mode must work without physical hardware.
6. Emulation mode must work without `pyvisa`, `pymeasure`, or `pytrinamic` installed.
7. Hardware-specific imports must be deferred until `connect()` or equivalent hardware-use methods.
8. Do not use `app.processEvents()` in new code.
9. GUI updates from running measurements must go through Qt signals and slots.
10. Hardware must be left in a safe state after completion, error, or cancellation.
11. Add or update tests for every changed component.
12. Run `python -m pytest` before every commit.

---

## Dependency direction

```text
gui → core → measurements → hardware
              ↓
             data
              ↓
           analysis
```

Rules:

- `hardware/` must not import GUI, core, or measurement code.
- `measurements/protocols/` should be pure Python where possible.
- Qt threading belongs in `measurements/workers/`.
- The GUI should interact mainly with `core/system.py`.
- The GUI must not directly create hardware drivers.
- Data writing belongs in `data/file_writer.py`.
- User authentication and logbook behavior belong in `services/`.

---

## Configuration

`src/iv_lab/config/settings.py` is the only module that reads `system_settings.json`.

Rules:

- Other modules receive typed Pydantic settings objects, never raw dicts.
- Preserve the legacy JSON key names and nesting.
- Models use `extra="allow"` to tolerate unknown legacy fields.

Runtime configuration files (machine-specific, gitignored):

- `config/system_settings.json` — auto-discovered by `main.py` if `--settings` is omitted
- `config/users.txt` — auto-discovered if `--users` is omitted; falls back to `config/users_generic.txt`

Committed templates (copy and edit for a new machine):

- `config/system_settings_example.json`
- `config/users_generic.txt`

Per-machine example configs for each physical system live under `config/examples/` as TOML files with comments.

---

## Hardware

All hardware families follow: abstract base class → registry → factory → real drivers + emulated driver.

```text
src/iv_lab/hardware/
├── base.py
├── errors.py
├── smu/     # Keithley 2400/2401/2450 (pymeasure),
│            # Keithley 2600/2602 (bundled drivers/_keithley26xx_lib.py)
├── lamp/    # Wavelabs Sinus70, Oriel LSS-7120, Trinamic filter wheels,
│            # Keithley-controlled filter wheel, manual lamp
└── arduino/ # shutter / cell-selection controller
```

All optional hardware libraries (`pyvisa`, `pymeasure`, `pytrinamic`) must be imported only inside driver `connect()`-style methods, never at package import time.

---

## Measurements

```text
src/iv_lab/measurements/
├── protocols/   # pure measurement logic — no GUI imports
└── workers/     # QObject workers with Qt signals, run on QThread
```

Workers emit: `data_ready`, `status_update`, `progress_update`, `finished`, `error`.

Workers support cancellation via `request_stop()`.

Measurement routines must use `try/finally` to leave hardware safe.

---

## Data

Result objects: `src/iv_lab/data/results.py` (dataclasses).
All file writing: `src/iv_lab/data/file_writer.py`.
PDF reports: `src/iv_lab/data/pdf_report.py`.

Preserve: legacy data file format, CSV compatibility, PDF report behavior, `sdPath` scrambled duplicate copy, `ivlablog.txt`.

---

## Services

```text
src/iv_lab/services/
├── auth.py     # users.txt scrambled JSON, login, calibration permissions
└── logbook.py  # login/logout logging
```

Preserve: scrambled JSON format, blank-username generic login (`user` / `123456`), hardcoded calibration permissions.

---

## Running the application

```bash
# Emulation (no hardware needed):
python -m iv_lab.main --settings config/system_settings_example.json --emulate

# Real hardware (copy and customise system_settings_example.json first):
python -m iv_lab.main --settings config/system_settings.json
```

`--users` is optional: falls back to `config/users.txt`, then `config/users_generic.txt`.

---

## Tests

Use `pytest`. Run before every commit:

```bash
python -m pytest
```

Add or update tests for every changed component. At minimum cover:

- settings loading and Pydantic validation,
- importing without hardware libraries installed,
- SMU / lamp / Arduino emulation,
- emulated IV curve and MPP tracking,
- legacy file-writing format,
- legacy authentication behavior.

---

## Git workflow

Work on `refactor/modular-pyside6`. Do not commit directly to `main`.

```bash
git add <files>
git commit -m "refactor: <subject>" -m "<body>"
git push
```

Use granular commits. Do not squash or amend unless explicitly requested.
