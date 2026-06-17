# verasol

Python control software for the **Newport/Oriel VeraSol LSS-7120 LED Solar Simulator** — a 19-channel LED source covering 400–1100 nm, calibrated to the AM1.5G solar spectrum.

---

## Hardware connection

1. Power on the VeraSol controller (front-panel switch).
2. Connect the controller to the PC with a standard USB-B cable (same connector used by many lab instruments and printers).
3. Wait for Windows to finish installing the device driver. The instrument uses the built-in Windows **IVI USBTMC** class driver — no third-party driver installation is needed.

> **NI-VISA note:** If you have NI-VISA installed, the software will try it first. If NI-VISA does not enumerate the instrument (common when the device is bound to the Windows IVI driver instead of the NI driver), the software falls back automatically to direct USB access. No manual configuration is required either way.

---

## Installation

Requires Python 3.9 or newer.

```bash
pip install PySide6 pyvisa pyvisa-py
```

Place both `verasol.py` and `verasol_gui.py` in the same folder.

---

## Running the GUI

```bash
py verasol_gui.py
```

The GUI opens immediately. If no instrument is connected it runs in **stub mode** (UI is fully functional but no hardware commands are sent) — useful for exploring the interface without the lamp.

### Connecting to the instrument

The **Connection** bar runs across the top of the window.

| Control | Purpose |
|---|---|
| **Scan** | Detect available USB instruments and populate the resource drop-down |
| Resource drop-down | Shows the detected device path; leave blank for auto-detect |
| **Connect** | Open the connection (auto-detects the instrument if the field is empty) |
| **Disconnect** | Close the connection cleanly |
| ID field | Displays the instrument identification string once connected |

On a typical Windows system, clicking **Connect** with an empty resource field is all that is needed — the software scans for the VeraSol automatically.

### Status indicators

Below the connection bar, four coloured dots show the current instrument state:

| Indicator | Green | Red/Amber |
|---|---|---|
| **Output ON** | Output is active | Output is off |
| **Head OK** | LED head connected | Head disconnected |
| **Warm** | Operating temperature reached | Still warming up (amber) |
| **Temp OK** | Temperature normal | Over-temperature fault |

---

## GUI tabs

### Output

Controls global output and intensity.

- **OUTPUT ON / OFF button** — toggles the LED output. The button turns green when the output is active.
- **Intensity slider** — sets the irradiance from 0.1 to 1.0 sun (1 sun = 1 kW/m²). Drag the slider or use the fine spinbox below it.
- **Fine spinbox** — type or click the arrows for 0.010-sun steps; press **Apply** to send the value to the instrument.

### LED Spectrum

Shows and adjusts the power of all 19 individual LED channels (400–1100 nm).

Each channel is displayed as a vertical bar coloured by its wavelength. The bar fills from bottom to top as power increases.

**Adjusting a channel:**

- **Click anywhere on the bar** — sets the channel power proportionally to the click height (top = maximum, bottom = zero). Click and drag to sweep smoothly.
- **Spinbox (below each bar)** — shows the current power in kW/m². Use the arrow buttons or type a value directly; the bar updates in real time.

Changes are sent to the instrument immediately as you interact with each channel.

The x-axis runs from 400 nm (left) to 1100 nm (right / NIR).

### Spectrum Memory

Stores and recalls complete LED spectra.

The instrument has 11 memory slots:

| Slot | Contents |
|---|---|
| 0 | Factory AM1.5G spectrum (read-only) |
| 1 | "Custom" spectrum, also accessible from the front panel |
| 2–10 | User storage slots |

- **Recall** — loads a stored spectrum into the active output.
- **Store** — saves the current LED settings to a slot (slots 1–10 only).
- **Quick Access** buttons recall the factory AM1.5G or the front-panel custom spectrum in one click.

The active spectrum location is shown at the top of the tab.

### Calibration

Controls intensity calibration.

**Calibration mode:**

- **Factory Default** — uses the original factory intensity reference.
- **User Offset** — applies a user-defined intensity offset on top of the factory calibration.

**Performing a user calibration:**

1. Place your reference irradiance meter under the head.
2. Set the output to the desired level and let the lamp reach operating temperature.
3. Adjust the amplitude until your meter reads exactly 1.00 sun.
4. Press **Execute User Calibration**. The controller rescales its internal reference to 1.00 sun at the current set point and stores the offset.

### Diagnostics

Tools for checking instrument health.

- **Fetch Errors** — queries the instrument error queue and displays any reported errors. An empty result means no errors.
- **Run LED Self-Test** — triggers the built-in LED power self-test. The instrument cycles through all channels, measuring each LED's actual output power. This takes approximately 60 seconds. Results are shown in a table (measured vs expected power per channel). Do not change settings during the test.

### Log

A scrolling event log showing all commands sent to the instrument, responses received, errors, and connection events. Useful for debugging.

---

## Warmup

The VeraSol requires approximately **15 minutes** to reach operating temperature after power-on. The **Warm** indicator turns green once the head is at temperature. Irradiance calibration is only accurate after warmup is complete.

---

## Library usage (Python API)

`verasol.py` can be used directly as a Python library without the GUI:

```python
from verasol import VeraSol

with VeraSol() as lamp:
    print(lamp.identify())          # instrument ID string
    lamp.set_amplitude(1.0)         # 1.0 sun
    lamp.set_output(True)           # output ON
    print(lamp.get_status())        # LampStatus(OUTPUT=ON, ...)
    lamp.set_output(False)          # output OFF
```

**Key methods:**

| Method | Description |
|---|---|
| `set_output(on)` | Turn output on/off |
| `get_output()` | Return current output state |
| `set_amplitude(suns)` | Set intensity (≥ 0.1 sun) |
| `get_amplitude()` | Return current amplitude in suns |
| `set_led_power(led, kw_m2)` | Set power of one LED channel (index 1–24) |
| `get_led_info(led)` | Return wavelength, power, and max power for one channel |
| `get_all_led_info()` | Return info for all 19 channels |
| `recall_spectrum(location)` | Load a stored spectrum (0–10) |
| `store_spectrum(location)` | Save current spectrum (1–10) |
| `get_status()` | Return decoded `LampStatus` |
| `get_errors()` | Drain and return the instrument error queue |
| `perform_user_calibration()` | Execute user intensity calibration |
| `list_instruments()` | Discover available USB VISA resources |

```python
# Discover what instruments are visible
from verasol import list_instruments
print(list_instruments())
```

---

## Files

| File | Purpose |
|---|---|
| `verasol.py` | Low-level instrument driver (use standalone or with the GUI) |
| `verasol_gui.py` | PySide6 desktop control panel |
| `test_connection.py` | Minimal raw USB connection test (no GUI, no VISA) |
