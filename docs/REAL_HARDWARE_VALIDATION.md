# Real Hardware Validation Checklist

Bench procedure for validating the refactored PySide6 `iv_lab`
application against real instruments, system by system. Work through it
top to bottom on each lab setup; do not skip the safety sections.

Companion documents: `docs/VALIDATION.md` (what is already validated in
emulation), `docs/HARDWARE.md` (safety rules and driver behavior).

Conventions:

- `[ ]` check and tick on paper or in a copy of this file; record the
  date, operator, and system name at the top of each session.
- "Legacy app" = `IVLab/IVlab.py` run the legacy way (unchanged, the
  fallback during the entire validation).
- Stop at the first unexplained failure: close the shutter, turn the
  lamp off, disable SMU outputs from the front panel, and record what
  happened before continuing.

Session record:

```text
Date: ____________  Operator: ____________
System name (IVsys.sysName): ____________
SMU model: ____________  Lamp: ____________  Arduino: yes / no
Branch: refactor/modular-pyside6  Commit: ____________
```

---

## 1. Pre-test preparation

- [ ] `git status -sb` — on `refactor/modular-pyside6`, working tree
      clean, in sync with origin. Record the commit:
      `git log --oneline -1`.
- [ ] `python -m pytest` passes on this machine (357+ tests).
- [ ] Legacy fallback works: launch the legacy app the usual way
      (`cd IVLab && python IVlab.py`), log in, initialize hardware,
      and close it again. If the legacy app does not work, fix that
      first — it is the rollback target.
- [ ] Identify the exact settings file the new app will use and record
      its path; review every section (`computer`, `IVsys`, `lamp`,
      `SMU`, `arduino`) against the physical setup.
- [ ] Back up the settings file:
      `copy system_settings.json system_settings.backup-<date>.json`
      (the calibration save rewrites this file).
- [ ] `users.txt` is present in the working directory and is **not**
      committed (`git status` must not list it; it is gitignored).
- [ ] Confirm `computer.basePath` exists (or its parent is writable)
      and note where data files will appear:
      `<basePath>/<username>/data/`.
- [ ] Confirm `computer.sdPath`: either a writable folder (duplicate
      copies and `ivlablog.txt` expected there) or the empty string
      (no duplicates, no logbook).
- [ ] Know the emergency shutdown: instrument front-panel OUTPUT
      OFF, lamp main switch, shutter manual control (IV_Old), and where
      the power switches are. Confirm you can reach them from the
      operator position.

## 2. General safety checks

- [ ] All SMU outputs are off (front panel) before launching anything.
- [ ] The lamp is off / the filter wheel is in the dark position.
- [ ] IV_Old: the shutter is closed.
- [ ] The compliance limits in the GUI defaults are conservative for
      the device under test (defaults: 2 V / 5 mA). Lower them if the
      first test device requires it.
- [ ] For the first connection test, **no sample is connected** (open
      terminals) unless the system requires a load; an open circuit is
      safe for voltage-source checks at compliance.
- [ ] Plan to test abort/cancel on a harmless measurement (dark scan,
      open terminals) before any real sample is involved.

## 3. Software launch checks

- [ ] Emulated launch against the real settings file first:
      `python -m iv_lab.main --settings <real settings> --emulate`
      — window appears, light levels match the settings file, no
      errors. Close it.
- [ ] Real launch (only after sections 1–2):
      `python -m iv_lab.main --settings <real settings>`
- [ ] Log in with a known user; status bar shows `User set to: <name>`;
      a wrong password shows the legacy "Sciper not valid" message.
- [ ] Click "Initialize Hardware". Expect instrument activity (relay
      clicks, display changes) and the measurement panels to enable.
      Failures must show "Error initializing keithley sourcemeter" /
      "Error initializing lamp" / "Error initializing arduino" with a
      detail message — record any.
- [ ] Verify the SMU output indicator is **off** after init.
- [ ] Log out (logbook dialog appears); verify the instruments
      disconnect (legacy behavior) and, if `sdPath` is set, that
      `ivlablog.txt` gained the logged on/comment/logged off lines.
- [ ] Close the window; verify outputs off and lamp off (the shutdown
      runs shutter → lamp → SMU, then disconnects).

## 4. SMU validation

### Keithley 2400 / 2401 / 2450

- [ ] Connection succeeds; beep is disabled (2400/2401), display active.
- [ ] After init: output OFF, front terminals selected.
- [ ] Dark J-V (section 7) exercises voltage-source mode; verify on the
      instrument display that voltage steps and current readings move.
- [ ] Voc-start scan (automatic limits, Reverse) exercises
      current-source mode; verify the source-mode change toggles the
      output only briefly.
- [ ] Switch 2-wire ↔ 4-wire in the GUI and verify the REM/4W indicator
      follows on the next run.
- [ ] Reference diode systems: verify the front→rear terminal switch
      when the light level is measured (rear = reference diode), and
      the switch back; cached settings must be re-applied (check
      compliance values on the display after the switch).
- [ ] Filter-wheel systems (2400/2401 only): each configured light
      level moves the wheel (TTL code); verify the wheel reaches the
      position within the settle time and that the dark level works.
- [ ] `turn_off`: after every run below, output is OFF.
- [ ] Abort mid-scan (harmless dark scan): output OFF afterwards.

### Keithley 2600 / 2602

- [ ] Connection succeeds; both channel displays active.
- [ ] Channel A drives the cell; channel B reads the reference diode
      (visible on the B display during the light-level check).
- [ ] Parallel reference read: during a lit J-V scan both channels
      update simultaneously; the measured light intensity in the GUI is
      plausible.
- [ ] After every run and after an abort: **both** channel outputs OFF.

## 5. Lamp validation

Test only the lamp type configured on this system.

- [ ] Manual lamp: the GUI shows the manual % sun field; runs proceed
      with the lamp operated by hand.
- [ ] Wavelabs Sinus70: a run activates and starts the configured
      recipe; light off cancels it; an undefined level shows the legacy
      'Light intensity "X % sun" is not defined.' error without
      touching the lamp; a 0 % level takes no lamp action.
- [ ] Oriel LSS-7120: amplitude is set and verified (a deliberate
      mismatch should error), OUTP ON/OFF verified by query.
- [ ] Trinamic filter wheel: connect homes the wheel and parks it dark;
      each configured level moves to the right angle; moves complete
      within the timeout; a blocked wheel raises the timeout error and
      stops the motor.
- [ ] Keithley filter wheel: levels move via the SMU TTL lines with the
      legacy settle waits.
- [ ] After every measurement: lamp off / wheel in the dark position.
- [ ] Light off when already off does nothing harmful.

## 6. Arduino / IV_Old validation

- [ ] Connection succeeds (LSS-7120-style IDN accepted).
- [ ] Shutter opens when a lit measurement starts and closes when it
      ends.
- [ ] Light-level measurement moves the reference diode into the beam
      and the test cell back (watch the stage; settle time ~5 s each).
- [ ] Calibration runs the two stage positions in the legacy order
      (reference diode first, then control diode). **Note:** the legacy
      IV_Old calibration computed its result from a zeroed array (a
      variable mix-up); the migrated computation is corrected — verify
      the derived current against a known calibrated diode.
- [ ] Closing the app closes the shutter (shutter is closed before the
      lamp and SMU in the shutdown order).
- [ ] Abort during a lit scan: shutter closed afterwards.

## 7. Measurement validation

Use a sacrificial or dummy device first; conservative limits throughout.

- [ ] **Dark J-V, no sample (open terminals)**: 0 → 0.5 V, 50 mV steps,
      low current limit. Expect ~0 current. Abort it once; re-run to
      completion. Output OFF after both.
- [ ] **Dark J-V, test device**: sensible diode curve, no compliance
      hits.
- [ ] **Illuminated J-V (short)**: low intensity if available, 0 → Voc
      region. Verify the live plot, the metrics (Voc/Jsc/FF/PCE)
      against expectations, and the measured light intensity.
- [ ] **Constant voltage** (30 s, small bias): stable current trace;
      abort once mid-run — partial data retained, output OFF.
- [ ] **Constant current** (30 s, 0 mA): voltage floats to ~Voc under
      light / ~0 dark.
- [ ] **MPP tracking** (60 s, manual start near the expected Vmpp):
      power stabilizes near the maximum; then once with automatic start
      (reverse Voc→0 pre-scan visible on the J-V plot).
- [ ] **Reference diode calibration dry run** (calibration-permitted
      user): derived current appears in mA; **do not** click "Save
      Calibration" unless a certified diode is mounted; if saved,
      verify `system_settings.json` afterwards (all sections intact,
      including `arduino`) and restore the backup if it was a dry run.
- [ ] Abort each long-running type at least once: GUI returns to ready,
      hardware dark and output off every time.

## 8. Data validation

- [ ] CSV files appear in `<basePath>/<username>/data/` named
      `<cell>_<scanType>_<timestamp>.csv`.
- [ ] The J-V save also produced the PDF; open it: plot, parameters,
      metrics, logo (if `EPFL_Logo.png` is available), footer.
- [ ] `sdPath` set: a scrambled duplicate appeared per save.
- [ ] Decode one duplicate and compare to the CSV
      (`python -c "from iv_lab.services import unscramble_string; ..."`,
      or any equivalent check that the decoded text equals the CSV).
- [ ] **Legacy comparison**: measure the same sample with the same
      settings in the legacy app; compare the two CSVs line-by-line —
      header order and names, `nHeader` count, column counts, number
      formatting. Differences must be explainable (timestamps, noise).
- [ ] `ivlablog.txt` contains the session's login/logout lines.
- [ ] No unexpected files outside `<basePath>` and `<sdPath>` (check
      the working directory and home directory for strays).

## 9. Acceptance criteria

The new application is bench-ready on a given system only when all of
the following hold:

1. Every applicable checkbox above passes, with deviations written up.
2. Hardware always ends safe: across all runs, aborts, errors, logout,
   and app close, the SMU output(s) ended OFF, the lamp ended off/dark,
   and (IV_Old) the shutter ended closed — zero exceptions observed.
3. Data files from the same sample match the legacy format
   (section 8), and the analysis workflow that consumes them accepts
   the new files unchanged.
4. Measured metrics agree with the legacy app on the same sample within
   normal measurement repeatability.
5. Cancellation works on every measurement type without instrument
   error states or required power cycles.
6. No GUI freeze during any measurement (the UI stays responsive while
   scans run — this is the key behavioral change vs. legacy).
7. The calibration flow produces a plausible derived current, and a
   saved calibration leaves `system_settings.json` loadable by **both**
   the new and the legacy application.

## 10. Rollback plan

If validation fails or the lab needs to measure immediately:

1. Close the new application (window close runs the safe shutdown). If
   it is unresponsive, put the hardware in a safe state from the front
   panels first, then kill the process.
2. Verify outputs off, lamp off, shutter closed.
3. Restore the settings backup if the file was rewritten:
   `copy system_settings.backup-<date>.json system_settings.json`.
4. Resume work with the legacy app: `cd IVLab && python IVlab.py`
   (unchanged throughout the migration).
5. Record every deviation, bug, and surprise as a GitHub issue on
   `EPFL-LPI/iv_lab` (one issue per problem: system, commit, steps,
   expected vs. observed, photos of instrument state if relevant).
   Do not fix-and-retest on the bench without committing the fix and
   re-running `python -m pytest` first.
