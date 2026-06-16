# Validation Report (Step 16)

End-to-end validation of the migrated `iv_lab` package in emulation
mode, per docs/MIGRATION.md step 16 and the definition of done in
CLAUDE.md. Performed 2026-06-12 on Windows 11, Python 3.14.4
(PySide6 6.11.1, pyqtgraph 0.14.0, pydantic 2.13.4, numpy 2.4.6,
pandas 3.0.3, matplotlib 3.11.0, bric-analysis-libraries 0.1.x).

---

## Validated in emulation

| Check | How | Result |
| --- | --- | --- |
| Package import without hardware libraries | `tests/test_import_without_hardware_drivers.py` (all modules) | pass |
| Settings loading | `tests/test_settings.py` incl. committed per-system templates | pass |
| Hardware emulation (SMU, lamp, Arduino) | emulation test suites | pass |
| Emulated J-V scan with **real** metrics | `tests/test_end_to_end_emulation.py`: Voc = 0.55 V, Jsc ≈ −25 mA/cm² from the emulated diode through the real `bric` pipeline | pass |
| MPP tracking | protocol tests + e2e session | pass |
| Data saving (legacy format) | `tests/test_file_writer_legacy_format.py` + e2e CSV checks (nHeader, headers, columns) | pass |
| `sdPath` scrambled duplicate | e2e: duplicate unscrambles to the exact CSV content | pass |
| PDF report generation | `tests/test_pdf_report.py` + e2e (`%PDF-`, beside the CSV) | pass |
| Login/logout incl. logbook | e2e: logbook lines, hardware disconnected, UI reset | pass |
| Calibration permissions | e2e: felix yes, alice no, blank-username generic login yes | pass |
| Calibration run + save | e2e: derived current ≈ certified value, settings file rewritten intact | pass |
| GUI starts (`python -m iv_lab.main --emulate`) | live run on the offscreen platform; event loop alive, log clean | pass |
| Packaging (`pip install -e .`) | editable install + installed-package import + live launch | pass (after fix below) |
| Full test suite | `python -m pytest` | 357 passed |

Cancellation, hardware-safe error paths, threaded runs with abort, and
the legacy behavioral quirks are covered continuously by the suite (see
the per-step tests).

## Issues found and fixed during validation

1. **`bric_analysis_libraries` cannot import on modern SciPy** — it
   uses `scipy.integrate.trapz`, which SciPy removed (now
   `trapezoid`). Fixed with a compatibility shim in
   `iv_lab/analysis/jv_metrics.py`; the real pipeline then produces
   correct metrics on current numpy/pandas/scipy.
2. **`pip install` of the package was impossible** — the stale root
   `setup.py` (referencing a nonexistent `iv_lab/_version.py`,
   broken since before the refactor) overrode the pyproject build.
   Removed per docs/ARCHITECTURE.md ("do not maintain old setup.py").

## Known gaps (deliberate)

- Live measured-light-intensity GUI updates during a running scan are
  not re-emitted by the protocols (legacy updated the label from inside
  the SMU loops); the value is shown from the finished result instead.
- The legacy per-user GUI config is preserved, but the legacy
  cursor-position hacks and placeholder-clearing workarounds were not
  ported (modern placeholders cover them).

---

## Outstanding: real hardware validation

Emulation cannot validate instrument behavior. Before routine use,
follow docs/HARDWARE.md on each lab system, with the legacy
`IVLab/IVlab.py` application untouched as the fallback:

1. Verify `system_settings.json`, voltage/current limits, and
   compliance settings; confirm manual access to the instrument and an
   emergency stop.
2. Keithley 2400/2401 and 2450: short, low-limit J-V scans; verify the
   front/rear terminal switching for the reference diode, output-off
   after completion/cancel/error, and `set_ttl_level` on the filter
   wheel system.
3. Keithley 2602: verify dual-channel parallel reference measurement
   (`CHAN_BOTH` reads) and both outputs off on `turn_off`.
4. Lamps: Wavelabs recipe activate/start/cancel; Oriel AMPL/OUTP
   verification replies; Trinamic homing, moves, and timeouts; Keithley
   filter wheel settle times.
5. IV_Old: Arduino shutter open/close, stage settle time, calibration
   stage sequence (note: the legacy IV_Old calibration averaged an
   all-zero array — the migrated computation is corrected; verify the
   derived value against a known diode).
6. Test cancellation mid-scan and pulling a cable mid-scan: hardware
   must end dark with outputs off.
7. Compare a real J-V data file and PDF against ones produced by the
   legacy application on the same cell.
