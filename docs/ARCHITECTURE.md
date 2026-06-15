# Architecture

This document describes the target architecture for the modular IVLab refactor.

The short mandatory rules are in `CLAUDE.md`. This file provides additional architectural context.

---

## Goal

The goal is to move from a monolithic PyQt5 application to a modular PySide6 package while preserving the behavior of the existing IV characterization system.

The refactor should improve:

- maintainability,
- testability,
- hardware abstraction,
- GUI responsiveness,
- safe cancellation,
- emulation support,
- data-format compatibility.

---

## Source of truth during migration

The legacy files remain the behavioral reference:

```text
IVLab/IVlab.py
IVLab/IV_gui.py
IVLab/system_settings.json
```

The new code must not silently change behavior.

When migrating a feature, inspect all relevant legacy call sites before implementing the new version.

---

## Package layout

Use a `src/` layout:

```text
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
```

Rationale:

- avoids accidental imports from the repository root,
- makes package imports cleaner,
- works well with `pyproject.toml`,
- makes tests closer to installed-package behavior.

---

## Main dependency direction

```text
gui → core → measurements → hardware
              ↓
             data
              ↓
           analysis
```

This means:

- GUI code presents state and user controls.
- Core code coordinates application logic.
- Measurement protocols execute experiments.
- Hardware modules talk to instruments.
- Data modules serialize and save results.
- Analysis modules compute photovoltaic metrics.

Forbidden directions:

- `hardware → gui`
- `hardware → core`
- `hardware → measurements`
- `measurements/protocols → gui`
- `data → gui`

---

## `config/`

Purpose:

- load legacy `system_settings.json`,
- validate with Pydantic v2,
- provide typed settings objects to the rest of the application.

Target files:

```text
src/iv_lab/config/
├── __init__.py
└── settings.py
```

Per-machine example configs live under the repository-level `config/` directory:

```text
config/
├── system_settings_example.json   # emulation-ready template (committed)
├── system_settings.json           # machine-specific runtime (gitignored)
├── users_generic.txt              # user table template (committed)
├── users.txt                      # machine-specific live users (gitignored)
└── examples/
    └── *.toml                     # per-system config examples with comments
```

Rules:

- `settings.py` is the only new module that reads `system_settings.json`.
- Preserve legacy key names and nesting.
- Use permissive models during migration with `extra="allow"`.
- Tighten validation only after all legacy fields are mapped.

Example base model:

```python
from pydantic import BaseModel, ConfigDict


class LegacyCompatibleModel(BaseModel):
    model_config = ConfigDict(extra="allow")
```

---

## `hardware/`

Purpose:

- abstract all physical and emulated devices,
- prevent GUI or measurement code from depending on concrete instrument classes,
- allow emulation without optional hardware libraries.

Target files:

```text
hardware/
├── __init__.py
├── base.py
├── errors.py
├── smu/
├── lamp/
└── arduino/
```

Every hardware family should use:

- base interface,
- registry,
- factory,
- drivers,
- emulated driver.

Example pattern:

```text
hardware/smu/
├── __init__.py
├── base.py
├── registry.py
├── factory.py
└── drivers/
    ├── __init__.py
    ├── keithley_2400.py
    ├── keithley_26xx.py
    └── emulated.py
```

Important rule:

Hardware libraries such as `pyvisa`, `pymeasure`, `pytrinamic`, and the bundled `_keithley26xx_lib` module must only be imported inside `connect()` or equivalent hardware-use methods.

The package must import successfully in emulation mode without these libraries installed.

---

## `measurements/`

Purpose:

- implement experiment logic,
- expose Qt-compatible workers for GUI execution,
- keep measurement algorithms testable without Qt when possible.

Target structure:

```text
measurements/
├── protocols/
│   ├── base.py
│   ├── iv_curve.py
│   ├── constant_voltage.py
│   ├── constant_current.py
│   ├── mpp_tracking.py
│   └── calibration.py
└── workers/
    ├── base_worker.py
    ├── iv_curve_worker.py
    ├── constant_voltage_worker.py
    ├── constant_current_worker.py
    ├── mpp_tracking_worker.py
    └── calibration_worker.py
```

### Protocols

Protocols contain the experiment logic.

They may depend on:

- hardware interfaces,
- settings,
- result dataclasses,
- analysis functions.

They must not depend on:

- GUI widgets,
- windows,
- panels,
- dialogs.

### Workers

Workers wrap protocols for Qt execution.

Prefer `QObject` workers moved to `QThread`, rather than subclassing `QThread` directly.

Workers should emit:

- `data_ready`,
- `status_update`,
- `progress_update`,
- `finished`,
- `error`.

Workers must support graceful cancellation.

---

## `analysis/`

Purpose:

- isolate photovoltaic metric calculation.

Files:

```text
analysis/
├── jv_metrics.py    # thin public interface (Voc, Jsc, FF, PCE, …)
└── jv_analysis.py   # bundled implementation (ported from bric_analysis_libraries)
```

`jv_metrics.py` is the only module the rest of the codebase imports.
`jv_analysis.py` contains the actual curve-fitting and metric calculations.

Do not reimplement these metrics from scratch. If the calculations need to change, edit `jv_analysis.py` directly.

---

## `data/`

Purpose:

- result containers,
- data serialization,
- file writing,
- PDF report generation.

Target files:

```text
data/
├── results.py
├── file_writer.py
└── pdf_report.py
```

Rules:

- Use dataclasses for result objects.
- Preserve legacy output formats.
- Preserve CSV compatibility.
- Preserve PDF report behavior.
- Preserve `sdPath` scrambled duplicate copy logic.
- Preserve `ivlablog.txt`.
- Do not scatter `open()` calls throughout the application.

---

## `services/`

Purpose:

- handle application services that are not GUI, hardware, or measurement logic.

Target files:

```text
services/
├── auth.py
└── logbook.py
```

Authentication must preserve:

- `users.txt` scrambled JSON behavior,
- lowercase username mapping,
- blank username plus password `123456` login as generic `user`,
- hardcoded calibration permissions.

Logbook must preserve:

- login logging,
- logout logging,
- timestamp behavior,
- legacy log file behavior.

---

## `core/`

Purpose:

- orchestrate the application.

Target file:

```text
core/system.py
```

Responsibilities:

- hold typed settings,
- create hardware through factories,
- connect/disconnect hardware,
- start and stop measurement workers,
- route results to the data layer,
- route status and error messages,
- coordinate authentication and logbook services,
- provide a stable interface to the GUI.

The GUI should not directly create SMUs, lamps, Arduino controllers, or measurement protocols.

---

## `gui/`

Purpose:

- PySide6 user interface.

Target structure:

```text
gui/
├── app.py
├── main_window.py
├── panels/
│   ├── measurement_panel.py
│   ├── light_panel.py
│   ├── plot_panel.py
│   └── calibration_panel.py
└── dialogs/
    └── logoff_dialog.py
```

Rules:

- PySide6 only.
- No PyQt5 imports.
- Use `pyqtgraph` for plotting.
- Do not use `app.processEvents()`.
- GUI updates from measurements must happen via Qt signals and slots.
- GUI classes should not perform hardware creation or file writing directly.

---

## `main.py`

`main.py` should be thin.

Responsibilities:

- parse minimal command-line arguments,
- load settings,
- initialize `QApplication`,
- create the system/core controller,
- create and show the main window,
- start the Qt event loop.

Do not put hardware logic, measurement logic, or file-writing logic in `main.py`.

---

## Import style

Preferred imports:

```python
from iv_lab.hardware.smu.base import BaseSMU
```

or local relative imports:

```python
from .base import BaseSMU
```

Avoid ambiguous root-level imports such as:

```python
from hardware.smu.base import BaseSMU
```

---

## Packaging

Use `pyproject.toml`.

Do not maintain old `setup.py` unless explicitly requested.

The project should eventually support:

```bash
python -m iv_lab.main --emulate
```
