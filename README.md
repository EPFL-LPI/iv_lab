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
