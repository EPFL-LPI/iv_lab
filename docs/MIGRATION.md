# Migration Plan

This document gives the step-by-step migration plan for the IVLab refactor.

The short mandatory instructions are in `CLAUDE.md`.

---

## Overall strategy

Refactor incrementally.

Do not rewrite the whole application at once.

For each migrated component:

1. inspect the relevant legacy code,
2. identify behavior and edge cases,
3. implement the new module,
4. add or update tests,
5. validate in emulation mode,
6. commit,
7. push.

The legacy files remain untouched until the new application works end-to-end.

---

## Branch

All work should happen on:

```bash
git checkout refactor/modular-pyside6
```

Do not commit to `main`.

Recommended start:

```bash
git status
git branch --show-current
git pull
```

If the branch does not exist locally:

```bash
git fetch
git checkout -b refactor/modular-pyside6 origin/refactor/modular-pyside6
```

---

## Commit format

After each validated step:

```bash
git add -A
git commit -m "refactor: <subject>" -m "<body explaining what was done and why>"
git push
```

Examples:

```bash
git commit -m "refactor: add package skeleton" -m "Adds the src/iv_lab package layout, documentation folder, and initial test structure. No legacy behavior is changed."
```

```bash
git commit -m "refactor: migrate settings loader" -m "Adds Pydantic v2 models for legacy-compatible system settings. The JSON format is preserved and extra fields are allowed during migration."
```

Keep commits granular.

Do not squash.

Do not amend unless explicitly requested.

---

## Step 1 — Add documentation and package skeleton

Create:

```text
CLAUDE.md
docs/ARCHITECTURE.md
docs/MIGRATION.md
docs/HARDWARE.md
docs/TESTING.md
pyproject.toml
src/iv_lab/
tests/
```

Add empty `__init__.py` files where needed.

Minimal structure:

```text
src/
└── iv_lab/
    ├── __init__.py
    └── main.py

tests/
└── test_import_package.py
```

Initial test:

```python
def test_import_package() -> None:
    import iv_lab

    assert iv_lab is not None
```

Validate:

```bash
python -m pytest
```

Commit and push.

---

## Step 2 — Migrate settings loader

Create:

```text
src/iv_lab/config/settings.py
```

Use Pydantic v2.

During migration, use permissive models:

```python
from pydantic import BaseModel, ConfigDict


class LegacyCompatibleModel(BaseModel):
    model_config = ConfigDict(extra="allow")
```

Rules:

- preserve JSON key names,
- preserve nesting,
- do not require rewriting `system_settings.json`,
- do not pass raw dictionaries through new code.

Add tests for:

- loading a minimal settings file,
- allowing extra legacy keys,
- missing required fields producing useful errors.

Validate:

```bash
python -m pytest
```

Commit and push.

---

## Step 3 — Add result dataclasses

Create:

```text
src/iv_lab/data/results.py
```

Add dataclasses for:

- IV results,
- MPP results,
- constant-voltage results,
- constant-current results,
- calibration results.

Keep this module dependency-light.

Use type hints.

Prefer:

```python
from dataclasses import dataclass, field
```

Commit and push.

---

## Step 4 — Add hardware base and errors

Create:

```text
src/iv_lab/hardware/base.py
src/iv_lab/hardware/errors.py
```

Define:

- common hardware base interface,
- connection state behavior,
- hardware-specific exceptions.

Commit and push.

---

## Step 5 — Migrate SMU module

Create:

```text
src/iv_lab/hardware/smu/
```

Implement:

- `base.py`,
- `registry.py`,
- `factory.py`,
- `drivers/emulated.py`,
- `drivers/keithley_2400.py`,
- `drivers/keithley_26xx.py`.

Start with emulation.

Required tests:

- factory returns emulated SMU when `emulate=True`,
- package imports without `pymeasure`,
- package imports without local hardware connection,
- emulated SMU returns plausible IV values.

Only after emulation works, migrate real drivers.

Preserve:

- Keithley 2400/2401/2450 behavior,
- Keithley 2600/2602 behavior,
- dual-channel channel A/B behavior,
- reference photodiode channel behavior.

Commit and push.

---

## Step 6 — Migrate lamp module

Create:

```text
src/iv_lab/hardware/lamp/
```

Implement:

- base,
- registry,
- factory,
- emulated lamp,
- manual lamp,
- Wavelabs driver,
- Oriel driver,
- Trinamic driver,
- Keithley-filter driver.

Start with emulation and manual mode.

Preserve:

- light-level behavior,
- filter-wheel behavior,
- calibration interactions,
- deferred imports.

Commit and push.

---

## Step 7 — Migrate Arduino module

Create:

```text
src/iv_lab/hardware/arduino/
```

Implement:

- base,
- registry,
- factory,
- emulated Arduino,
- shutter controller.

Preserve:

- Newport LSS-7120-style protocol,
- shutter open/close behavior,
- cell selection behavior,
- safety behavior.

Commit and push.

---

## Step 8 — Add analysis wrapper

Create:

```text
src/iv_lab/analysis/jv_metrics.py
```

Wrap:

```text
bric_analysis_libraries.jv.jv_analysis
```

Do not reimplement Voc, Jsc, FF, or PCE unless explicitly requested.

The rest of the code should call the internal wrapper rather than importing the external analysis package everywhere.

Commit and push.

---

## Step 9 — Migrate measurement protocols

Create:

```text
src/iv_lab/measurements/protocols/
```

Start with:

```text
iv_curve.py
```

Then migrate:

- constant-voltage,
- constant-current,
- MPP tracking,
- calibration.

Rules:

- protocols should be pure Python where possible,
- no GUI imports,
- no direct widget manipulation,
- use hardware interfaces,
- return result dataclasses,
- support cancellation hooks.

Add headless emulation tests.

Commit and push after each protocol.

---

## Step 10 — Add Qt measurement workers

Create:

```text
src/iv_lab/measurements/workers/
```

Workers wrap protocols for Qt execution.

Prefer:

```python
from PySide6.QtCore import QObject, Signal, Slot
```

over direct `QThread` subclassing.

Workers should emit:

- `data_ready`,
- `status_update`,
- `progress_update`,
- `finished`,
- `error`.

Workers should implement:

```python
def request_stop(self) -> None:
    ...

def is_stop_requested(self) -> bool:
    ...
```

Commit and push.

---

## Step 11 — Migrate services

Create:

```text
src/iv_lab/services/auth.py
src/iv_lab/services/logbook.py
```

Preserve:

- `users.txt` scrambled JSON behavior,
- blank username plus password `123456` login as generic `user`,
- hardcoded calibration permissions,
- login/logout logging.

Add tests.

Commit and push.

---

## Step 12 — Migrate data writing and PDF reports

Create:

```text
src/iv_lab/data/file_writer.py
src/iv_lab/data/pdf_report.py
```

Preserve:

- legacy file format,
- CSV/data compatibility,
- metadata,
- `sdPath` scrambled duplicate copy,
- PDF report layout and calculations where possible.

Add file-format compatibility tests.

Commit and push.

---

## Step 13 — Add core system orchestration

Create:

```text
src/iv_lab/core/system.py
```

Responsibilities:

- load and hold settings,
- create hardware through factories,
- manage connection state,
- start measurements,
- stop measurements,
- route data to file writer,
- expose status/errors to GUI,
- coordinate services.

The GUI should use this layer rather than constructing hardware directly.

Commit and push.

---

## Step 14 — Add PySide6 GUI

Create:

```text
src/iv_lab/gui/
```

Start with a minimal GUI that can launch in emulation mode.

Then add panels gradually:

1. main window skeleton,
2. plot panel,
3. measurement panel,
4. light panel,
5. calibration panel,
6. dialogs.

Rules:

- PySide6 only,
- no PyQt5,
- no `app.processEvents()`,
- GUI updates via signals/slots,
- no hardware creation directly in GUI classes.

Commit and push after each meaningful GUI step.

---

## Step 15 — Add thin main entry point

Create:

```text
src/iv_lab/main.py
```

Support:

```bash
python -m iv_lab.main --emulate
```

Responsibilities:

- parse CLI args,
- load settings,
- create application,
- create core system,
- create main window,
- start event loop.

Commit and push.

---

## Step 16 — End-to-end validation

Validate:

```bash
python -m pytest
python -m iv_lab.main --emulate
```

Check:

- package import,
- settings loading,
- hardware emulation,
- emulated J-V scan,
- MPP tracking,
- data saving,
- PDF report generation,
- login/logout behavior,
- calibration permissions.

Only after this should real hardware be tested.

---

## Recommended first Claude Code prompt

Use this as the first concrete task:

```text
Read CLAUDE.md and the files in docs/. Do not modify legacy files. Create only the initial package skeleton using a src/ layout, add pyproject.toml, add empty package __init__.py files, and add a minimal import test. Do not migrate hardware, GUI, or measurement logic yet. Run pytest. If tests pass, commit and push with a granular conventional commit message.
```

Second task:

```text
Now migrate only config/settings.py using Pydantic v2. Preserve the legacy system_settings.json structure, allow extra fields during migration, and add tests for loading a minimal legacy-compatible settings file. Do not modify hardware, GUI, or measurement code. Run pytest, commit, and push.
```

Proceed one task at a time.
