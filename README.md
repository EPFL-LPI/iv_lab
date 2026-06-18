# EPFL LPI | IV Lab

GUI application for J-V characterisation of solar cells. Controls source meter units (SMUs), solar simulators, filter wheels, and optional Arduino-based accessories.

For architecture and developer documentation see [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

---

## Quick start

### Emulation (no hardware required)

```bash
python -m iv_lab.main --settings config/system_settings_example.json --emulate
```

### Real hardware

```bash
# 1. Copy the example that matches your setup and edit it:
copy config\examples\oriel_iv.toml config\system_settings.toml

# 2. Run (auto-discovers config/system_settings.toml):
python -m iv_lab.main
```

---

## Installing as a package (pip)

The Quick start above runs the app from a checkout of this repository. You can
also install `iv_lab` as a normal Python package and launch it from anywhere
with the `iv-lab` command. Because the package ships **no** machine-specific
files (settings, users, logo), there are a few one-time setup steps.

### 1. Install

```powershell
# From a clone of this repository:
pip install .

# …or straight from GitHub (no clone needed):
pip install "git+https://github.com/EPFL-LPI/iv_lab.git"

# Add the instrument-control libraries for real hardware (omit for emulation):
pip install ".[hardware]"
```

This puts an **`iv-lab`** command on your PATH — equivalent to
`python -m iv_lab.main`, with the same options.

### 2. Scaffold your config (recommended)

```powershell
iv-lab --init
```

This creates the per-user config directory and seeds it with:

- an **emulation-ready** `system_settings.toml` (so `iv-lab` runs immediately
  without instruments — edit it for your hardware),
- a starter `users.txt` with the generic `user` / `123456` login.

It never overwrites existing files, so re-running it is safe. It prints the
exact directory it used; you can then jump to step 6 to run the app, and edit
the settings file when you connect real hardware. The manual steps 2–4 below
explain what `--init` sets up if you prefer to do it by hand or start from one
of the per-system examples.

### 2b. (Manual alternative) Pick where your config lives

When you run `iv-lab` **without** `--settings`, it looks for the settings file
in this order:

1. the `IV_LAB_SETTINGS` environment variable (a full path to the file),
2. `./config/system_settings.toml` in the current working directory,
3. the per-user config directory:
   - **Windows:** `%APPDATA%\iv_lab\system_settings.toml`
   - **Linux/macOS:** `~/.config/iv_lab/system_settings.toml` (honours `$XDG_CONFIG_HOME`).

The **per-user directory is recommended** for an installed app: it survives
package upgrades and works no matter which folder you launch from. Create it:

```powershell
# Windows
mkdir "$env:APPDATA\iv_lab"
```

### 3. Add your settings file

Copy the example that matches your hardware (from this repo's
[`config/examples/`](config/examples/)) into that directory as
`system_settings.toml`, then edit it:

```powershell
copy config\examples\oriel_iv.toml "$env:APPDATA\iv_lab\system_settings.toml"
notepad "$env:APPDATA\iv_lab\system_settings.toml"
```

Edit at least `basePath`, `sdPath`, and the SMU `visa_address` — see
[System settings](#system-settings) for the key fields. If you installed
without cloning, download an example from
[`config/examples/`](config/examples/) on GitHub first.

### 4. Add a users file

Login requires a users table, and the package ships none — without one the app
reports *"User table corrupted or absent."* Create a `users.txt` in the **same
per-user directory** with at least the generic account, using the
[`write_users` snippet](#adding-named-users) but pointing the path at, e.g.,
`%APPDATA%\iv_lab\users.txt` and including `"user": "123456"`. `iv-lab` finds
`users.txt` there automatically (same search order as the settings file).

The generic login (blank username, or `user` / `123456`) then works out of the
box; add named accounts as described under [User management](#user-management).

### 5. (Optional) report logo

PDF reports look for `EPFL_Logo.png` in the directory you launch from, or use
`--logo PATH`. Reports render fine without it.

### 6. Run it

```powershell
# Emulation (no instruments; still uses the settings file from step 3):
iv-lab --emulate

# Real hardware:
iv-lab
```

To pin the settings file regardless of the working directory, set the
environment variable once (then `iv-lab` needs no flags from any folder):

```powershell
setx IV_LAB_SETTINGS "%APPDATA%\iv_lab\system_settings.toml"
```

Calibration values you set in the app are written back into this same
`system_settings.toml` automatically.

---

## System settings

Machine-specific configuration lives in `config/system_settings.toml` (gitignored).  
Annotated templates for every physical setup are in `config/examples/`:

| File | Hardware |
|------|----------|
| `oriel_iv.toml` | Trinamic TMCM-1260 + Newport SOL3A + Keithley 2400 |
| `sinus70_1.toml` | Wavelabs Sinus70 + Keithley 2602 |
| `ivlab_wavelabs.toml` | Wavelabs Sinus70 + Keithley 2602 (older IVLab station) |
| `ivlab_indoor.toml` | Manual lamp + Keithley 2602 (indoor) |
| `bcl.toml` | Trinamic TMCM-1260 + Newport SOL3A + Keithley 2602 (BCL) |
| `bcl_old_iv.toml` | Trinamic TMCM-3110 + Keithley 2602 + Arduino (BCL historical) |
| `gmf.toml` | Trinamic TMCM-1160 + Newport SOL3A + Keithley 2400 (macOS) |
| `dell.toml` | Manual lamp + Keithley 2401, no reference diode (laptop) |
| `fte.toml` | Manual lamp + Keithley 2401, RS-232 (field setup) |
| `old_iv.toml` | Manual lamp + Keithley 2400 + Arduino (original macOS station) |

**Setting up a new machine:**

1. Copy the closest example to `config/system_settings.toml`.
2. Edit the paths (`basePath`, `sdPath`) and the VISA address of the SMU.
3. Run the app and use the **Calibration** panel to set `fullSunReferenceCurrent`.  
   The app writes the calibrated value back into `config/system_settings.toml` automatically.

Key fields to check:

```toml
[computer]
basePath = "C:\\Data"   # where measurement files are saved
sdPath   = "C:\\sd"     # scrambled backup copy; set "" to disable

[SMU]
visa_address = "GPIB0::24::INSTR"   # adjust to your instrument
visa_library = "C:\\Windows\\SysWOW64\\visa32.dll"

[lamp]
brand = "Trinamic"      # or "Wavelabs", "Manual", …
model = "TMCM-1260"
```

> TOML is used instead of JSON because it supports comments, making the
> example files self-documenting.  The app also accepts `.json` files if
> you have an existing JSON config.

---

## User management

User accounts are stored in `config/users.txt` (gitignored, machine-specific).  
The committed file `config/users_generic.txt` provides a ready-to-use generic account and is the fallback when `users.txt` does not exist.

### Generic / guest login

Leave the username blank (or enter `user` / `123456`) to log in with the generic account. This works out of the box with `users_generic.txt` and is sufficient for day-to-day measurements.

### Adding named users

`users.txt` stores a JSON dictionary `{"username": "password"}` in a legacy scrambled format — it cannot be edited as plain text. Use this one-liner to create or update the file:

```python
python - <<'EOF'
from iv_lab.services.auth import write_users
write_users("config/users.txt", {
    "user":   "123456",   # generic account — keep this
    "alice":  "12345",    # SCIPER or chosen password
    "bob":    "67890",
})
EOF
```

Run it from the repository root. The file is overwritten each time, so include all accounts you want to keep.

**Calibration access** is granted only to the generic `user/123456` login and to the hardcoded usernames `felix` and `legeyt`. All other named accounts can run measurements but cannot access the calibration panel.

### Passing custom paths on the command line

```bash
python -m iv_lab.main --settings path/to/my_settings.toml --users path/to/my_users.txt
```

---

## Dependencies

```bash
pip install -e .
```

Optional hardware libraries (only needed when not using `--emulate`):

- `pyvisa` + a VISA back-end (NI-VISA or pyvisa-py) — SMU and Wavelabs communication
- `pymeasure` — Keithley 2400/2401/2450 drivers
- `pytrinamic` — Trinamic filter wheel driver

---

## Running tests

```bash
python -m pytest
```
