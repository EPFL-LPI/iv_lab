# Testing Guide

This document defines the minimum testing expectations for the IVLab refactor.

---

## Test framework

Use `pytest`.

Tests belong in:

```text
tests/
```

Run tests with:

```bash
python -m pytest
```

When the application entry point exists, also run:

```bash
python -m iv_lab.main --emulate
```

---

## Minimum test files

Create these tests during the migration:

```text
tests/test_settings.py
tests/test_import_without_hardware_drivers.py
tests/test_smu_emulation.py
tests/test_lamp_emulation.py
tests/test_arduino_emulation.py
tests/test_iv_curve_emulated.py
tests/test_file_writer_legacy_format.py
tests/test_auth_legacy_behavior.py
```

Additional tests are encouraged when migrating complex legacy behavior.

---

## Package import test

Add an initial test as soon as the package skeleton exists:

```python
def test_import_package() -> None:
    import iv_lab

    assert iv_lab is not None
```

This ensures the package is importable from the `src/` layout.

---

## Import without hardware drivers

The package must import without optional hardware libraries installed.

The test should verify that importing `iv_lab` and core non-hardware modules does not require:

- `pyvisa`,
- `pymeasure`,
- `pytrinamic`,
- physical instruments.

The purpose is to prevent accidental top-level hardware imports.

---

## Settings tests

Test:

- loading a minimal legacy-compatible settings file,
- preserving legacy key names,
- allowing extra fields during migration,
- useful validation errors for missing required fields.

Settings tests should not require real hardware.

---

## Hardware emulation tests

For each hardware family, test that:

- factory returns emulated driver when `emulate=True`,
- emulated driver connects and disconnects,
- emulated driver exposes required methods,
- optional hardware libraries are not imported,
- outputs are plausible.

Suggested files:

```text
tests/test_smu_emulation.py
tests/test_lamp_emulation.py
tests/test_arduino_emulation.py
```

---

## Measurement tests

Start with an emulated J-V scan.

Test that:

- the protocol runs headlessly,
- it returns an IV result object,
- the voltage/current arrays have expected length,
- values are plausible,
- cancellation works,
- hardware is left safe after completion,
- hardware is left safe after an exception.

Suggested file:

```text
tests/test_iv_curve_emulated.py
```

MPP and long-duration measurements should also get tests once migrated.

---

## File-format compatibility tests

Legacy data compatibility is critical.

Tests should verify:

- output filenames,
- required metadata fields,
- delimiter/column behavior,
- numeric formatting where important,
- compatibility with existing analysis workflows,
- `sdPath` duplicate-copy behavior where applicable.

Suggested file:

```text
tests/test_file_writer_legacy_format.py
```

Use small synthetic result objects.

Do not require real measurements for file-writing tests.

---

## Authentication tests

Preserve legacy behavior.

Test:

- `users.txt` scrambled JSON decoding,
- lowercase username behavior,
- blank username plus password `123456` logs in as generic `user`,
- invalid password fails,
- calibration permissions match legacy hardcoded behavior.

Suggested file:

```text
tests/test_auth_legacy_behavior.py
```

---

## GUI smoke tests

GUI tests can be added later.

At minimum, once the GUI exists, verify:

- application starts in emulation mode,
- main window can be constructed,
- no real hardware connection is attempted,
- no PyQt5 imports are used.

Qt GUI tests may require additional tooling such as `pytest-qt`.

Do not make GUI tests block early migration.

---

## Validation before commit

Before each commit, run the relevant subset of tests.

Default:

```bash
python -m pytest
```

Once the entry point exists:

```bash
python -m iv_lab.main --emulate
```

When linting is configured:

```bash
ruff check .
```

Optional later:

```bash
mypy src
```

Do not require `mypy` until type annotations are mature enough.

---

## What a test should not do

Tests should not:

- require real hardware,
- require lab network access,
- depend on machine-specific `system_settings.json`,
- write permanent files outside a temporary directory,
- assume optional hardware drivers are installed,
- modify legacy source files.

Use temporary directories for file-writing tests.
