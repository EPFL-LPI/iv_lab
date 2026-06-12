# CLAUDE.md

This file gives Claude Code the mandatory instructions for refactoring this repository.

For details, read the supporting documents:

- `docs/ARCHITECTURE.md`
- `docs/MIGRATION.md`
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

The current goal is to refactor the monolithic PyQt5 application into a modern, modular PySide6 package while preserving legacy behavior.

---

## Legacy source of truth

The legacy source of truth is:

- `IVLab/IVlab.py`
- `IVLab/IV_gui.py`
- `IVLab/system_settings.json`

Do not delete these files during migration.

Do not rewrite these files during the initial refactor.

Use them as the behavioral reference.

---

## Golden rules

1. Preserve legacy behavior unless explicitly asked to change it.
2. Do not modify `IVLab/IVlab.py` or `IVLab/IV_gui.py` during migration.
3. Do not change the structure or key names of `system_settings.json`.
4. New GUI code must use PySide6 only. No PyQt5 in new code.
5. Emulation mode must work without physical hardware.
6. Emulation mode must work without `pyvisa`, `pymeasure`, or `pytrinamic` installed.
7. Hardware-specific imports must be deferred until `connect()` or equivalent hardware-use methods.
8. Do not use `app.processEvents()` in new code.
9. GUI updates from running measurements must go through Qt signals and slots.
10. Hardware must be left in a safe state after completion, error, or cancellation.
11. Refactor incrementally. Do not perform a large all-at-once rewrite.
12. Add or update tests for every migrated component.
13. Commit and push after each validated migration step.

---

## Target package structure

Use a modern `src/` layout:

```text
pyproject.toml
CLAUDE.md
README.md

src/
└── iv_lab/
    ├── __init__.py
    ├── main.py
    ├── config/
    ├── hardware/
    ├── measurements/
    ├── analysis/
    ├── data/
    ├── services/
    ├── core/
    └── gui/

tests/
docs/
```

Do not place the new package directly at repository root.

The package should be importable as:

```python
import iv_lab
```

---

## Dependency direction

Keep dependencies clean:

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

Use Pydantic v2 in:

```text
src/iv_lab/config/settings.py
```

Rules:

- `config/settings.py` is the only new module that reads `system_settings.json`.
- Other modules receive typed settings objects.
- Preserve the legacy JSON structure.
- During migration, allow extra fields so existing machine configs do not break prematurely.
- Per-machine `system_settings.json` files must be gitignored.
- Example/template settings files may be committed.

---

## Hardware

Hardware modules must use:

- an abstract base class,
- a registry,
- a factory,
- real drivers,
- an emulated driver.

Target hardware modules:

```text
src/iv_lab/hardware/
├── base.py
├── errors.py
├── smu/
├── lamp/
└── arduino/
```

Supported legacy behavior must be preserved:

- Keithley 2400 / 2401 / 2450 via `pymeasure`
- Keithley 2600 / 2602 via local `Keithley26XX.py`
- dual-channel Keithley behavior, including reference photodiode measurement on channel B
- Wavelabs Sinus70
- Oriel LSS-7120
- Trinamic filter wheels
- Keithley-controlled filter wheel
- manual lamp mode
- Arduino shutter / cell-selection controller

All optional hardware libraries must be imported only inside driver connection/use methods.

---

## Measurements

Do not put measurement logic directly into `QThread` subclasses.

Use:

```text
src/iv_lab/measurements/
├── protocols/   # pure measurement logic
└── workers/     # QObject workers with Qt signals
```

Workers should support:

- `data_ready`
- `status_update`
- `progress_update`
- `finished`
- `error`
- cancellation via `request_stop()`

Measurement routines must use `try/finally` to leave hardware safe.

---

## Data

Use dataclasses for result objects in:

```text
src/iv_lab/data/results.py
```

All file writing must go through:

```text
src/iv_lab/data/file_writer.py
```

Preserve:

- legacy data file format,
- CSV compatibility,
- PDF report behavior,
- `sdPath` scrambled duplicate copy logic,
- `ivlablog.txt`.

Do not scatter `open()` calls across the application.

---

## Services

Move authentication and logbook behavior into:

```text
src/iv_lab/services/auth.py
src/iv_lab/services/logbook.py
```

Preserve:

- `users.txt` scrambled JSON behavior,
- blank username plus password `123456` login as generic `user`,
- hardcoded calibration permissions,
- legacy login/logout logging.

---

## Migration order

Refactor in this order:

1. package skeleton with `src/iv_lab`
2. `config/settings.py`
3. `data/results.py`
4. `hardware/base.py` and `hardware/errors.py`
5. `hardware/smu/`
6. `hardware/lamp/`
7. `hardware/arduino/`
8. `analysis/jv_metrics.py`
9. `measurements/protocols/`
10. `measurements/workers/`
11. `services/auth.py` and `services/logbook.py`
12. `data/file_writer.py` and `data/pdf_report.py`
13. `core/system.py`
14. `gui/`
15. `main.py`

Commit and push after each validated step.

---

## Tests

Use `pytest`.

At minimum, add tests for:

- settings loading,
- importing without hardware drivers installed,
- SMU emulation,
- lamp emulation,
- Arduino emulation,
- emulated IV curve measurement,
- legacy file-writing format,
- legacy authentication behavior.

Before committing, run:

```bash
python -m pytest
```

When available, also run:

```bash
python -m iv_lab.main --emulate
```

---

## Git workflow

Work only on:

```text
refactor/modular-pyside6
```

Do not commit to `main`.

After each working step:

```bash
git add -A
git commit -m "refactor: <subject>" -m "<body explaining what was done and why>"
git push
```

Use granular commits.

Do not squash or amend unless explicitly requested.

---

## Definition of done

The refactor is complete only when:

- the new PySide6 GUI starts,
- emulation mode works without hardware libraries,
- an emulated J-V scan works,
- MPP tracking works in emulation,
- data files are legacy-compatible,
- PDF generation works,
- login/logout behavior is preserved,
- calibration permissions are preserved,
- tests pass,
- real hardware has been validated carefully.
