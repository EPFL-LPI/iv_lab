"""
_verasol_lib.py — Low-level control library for the Oriel VeraSol LSS-7120 LED Solar Simulator.

Copied verbatim from docs/verasol/verasol.py.  Do not import this module at
package load time — it imports pyvisa at module level.  Only import it inside
``_open()`` or equivalent connection-time methods.

Communication is over USB via the USBTMC (USB Test and Measurement Class) protocol.
Requires a VISA backend: install with `pip install pyvisa pyvisa-py` (or use NI-VISA).
"""

from __future__ import annotations

import struct
import sys
import time
import warnings
from dataclasses import dataclass
from enum import Enum
from typing import Optional

try:
    import pyvisa
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "pyvisa is required: pip install pyvisa pyvisa-py"
    ) from exc

# Windows-only imports for the IVI USBTMC fallback transport
if sys.platform == "win32":
    import ctypes
    import winreg
    from ctypes import windll, create_string_buffer, c_ulong, byref as _byref
    _WIN32_AVAILABLE = True
else:
    _WIN32_AVAILABLE = False

# Device interface GUID assigned by the Windows IVI USBTMC class driver
_WIN32_USBTMC_GUID = "{a9fdbb24-128a-11d5-9961-00108335e361}"
# Substring present in the IDN string of every VeraSol instrument
_VERASOL_IDN_HINT = "LSS-7120"


# ---------------------------------------------------------------------------
# Public data types
# ---------------------------------------------------------------------------

class SpectrumMode(str, Enum):
    """Named spectrum slots understood by the controller."""
    AM15G = "AM1.5G"   # Factory AM1.5G (memory location 0)
    CUSTOM = "CUSTOM"  # Custom / user-defined (memory location 1, front-panel)


class CalibrationMode(str, Enum):
    DEFAULT = "DEFAULT"  # Factory calibration
    USER = "USER"        # User intensity offset


@dataclass
class LampStatus:
    """Decoded STATUS? response (bit-field, see manual p. 30)."""
    output_on: bool
    head_disconnected: bool
    head_warming_up: bool
    head_overtemperature: bool
    raw: int

    def __str__(self) -> str:
        flags = []
        if self.output_on:
            flags.append("OUTPUT=ON")
        if self.head_disconnected:
            flags.append("HEAD_DISCONNECTED")
        if self.head_warming_up:
            flags.append("WARMING_UP")
        if self.head_overtemperature:
            flags.append("OVERTEMP")
        return f"LampStatus({', '.join(flags) or 'OK'})"


@dataclass
class LEDInfo:
    """Power and wavelength information for a single LED channel."""
    index: int           # 1-based LED number (1-24)
    wavelength_nm: float
    power_kw_m2: float
    max_power_kw_m2: float


# ---------------------------------------------------------------------------
# Windows IVI USBTMC fallback transport
# ---------------------------------------------------------------------------

class _WinUSBTMC:
    """
    Minimal USBTMC transport that talks to the Windows IVI USBTMC class driver
    directly via Win32 file handles, bypassing NI-VISA's device enumeration.

    Implements the write / read / query / close / timeout interface that
    VeraSol expects from a pyvisa Resource object.
    """

    _GENERIC_RW    = 0x80000000 | 0x40000000   # GENERIC_READ | GENERIC_WRITE
    _FILE_SHARE_RW = 0x01 | 0x02               # FILE_SHARE_READ | FILE_SHARE_WRITE
    _OPEN_EXISTING = 3

    def __init__(self, path: str, timeout_ms: int = 10_000) -> None:
        if not _WIN32_AVAILABLE:
            raise OSError("_WinUSBTMC is only supported on Windows.")
        self.timeout           = timeout_ms   # stored; used by run_led_test()
        self.read_termination  = "\n"
        self.write_termination = "\n"
        self._btag = 0
        self._h = windll.kernel32.CreateFileW(
            path, self._GENERIC_RW, self._FILE_SHARE_RW,
            None, self._OPEN_EXISTING, 0, None,
        )
        if self._h == -1:
            raise OSError(
                f"Cannot open USBTMC device (err={ctypes.GetLastError()}): {path}"
            )

    def close(self) -> None:
        if self._h not in (None, -1):
            windll.kernel32.CloseHandle(self._h)
            self._h = None

    def _next_tag(self) -> int:
        self._btag = (self._btag % 255) + 1
        return self._btag

    def write(self, msg: str) -> None:
        data = (msg.rstrip("\n") + self.write_termination).encode()
        tag  = self._next_tag()
        header = struct.pack(
            "<BBBBIBxxx",
            0x01, tag, (~tag) & 0xFF, 0,   # DEV_DEP_MSG_OUT, bTag, ~bTag, reserved
            len(data), 0x01,               # TransferSize, bmTransferAttributes (EOM)
        )
        packet = header + data
        packet += b"\x00" * ((4 - len(packet) % 4) % 4)   # 4-byte alignment padding
        buf     = create_string_buffer(packet)
        written = c_ulong(0)
        if not windll.kernel32.WriteFile(self._h, buf, len(packet), _byref(written), None):
            raise OSError(f"USBTMC WriteFile failed: {ctypes.GetLastError()}")

    def read(self) -> str:
        tag = self._next_tag()
        req = struct.pack(
            "<BBBBIBxxx",
            0x02, tag, (~tag) & 0xFF, 0,   # REQUEST_DEV_DEP_MSG_IN
            4096, 0x00,                    # TransferSize, bmTransferAttributes
        )
        buf_req = create_string_buffer(req)
        written = c_ulong(0)
        windll.kernel32.WriteFile(self._h, buf_req, len(req), _byref(written), None)
        buf_resp  = create_string_buffer(4096 + 12)
        read_bytes = c_ulong(0)
        if not windll.kernel32.ReadFile(
            self._h, buf_resp, 4096 + 12, _byref(read_bytes), None
        ):
            raise OSError(f"USBTMC ReadFile failed: {ctypes.GetLastError()}")
        n = read_bytes.value
        if n < 12:
            return ""
        payload_len = struct.unpack_from("<I", buf_resp.raw, 4)[0]
        # A 0-byte payload with EOM set is the device's command acknowledgement.
        # NI-VISA translates this to the string "Ready"; we do the same so that
        # VeraSol._write() can check for it without knowing which transport is used.
        if payload_len == 0 and (buf_resp.raw[8] & 0x01):
            return "Ready"
        raw = buf_resp.raw[12 : 12 + payload_len].decode("ascii", errors="replace")
        return raw.rstrip(self.read_termination or "\n")

    def query(self, msg: str) -> str:
        self.write(msg)
        return self.read()


def _find_win_usbtmc_device(idn_hint: str = _VERASOL_IDN_HINT) -> Optional[str]:
    """
    Search the Windows device-interface registry for a USBTMC instrument whose
    ``*IDN?`` response contains *idn_hint*.  Returns the Win32 device path on
    success, or *None* if no matching instrument is found.
    """
    if not _WIN32_AVAILABLE:
        return None
    key_path = (
        r"SYSTEM\CurrentControlSet\Control\DeviceClasses"
        rf"\{_WIN32_USBTMC_GUID}"
    )
    try:
        root = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path)
    except FileNotFoundError:
        return None
    i = 0
    while True:
        try:
            dev_key_name = winreg.EnumKey(root, i)
        except OSError:
            break
        i += 1
        # Registry key names use ##?# prefix; Win32 paths use \\?\
        device_path = "\\\\?\\" + dev_key_name[4:]
        try:
            instr = _WinUSBTMC(device_path)
            idn   = instr.query("*IDN?")
            instr.close()
            if idn_hint in idn:
                return device_path
        except Exception:
            pass
    return None


# ---------------------------------------------------------------------------
# Main driver class
# ---------------------------------------------------------------------------

class VeraSol:
    """
    Driver for the Oriel VeraSol LSS-7120 LED Solar Simulator Controller.

    Parameters
    ----------
    resource_name:
        VISA resource string, e.g. ``"USB0::0x1028::0x0001::71201234::INSTR"``.
        When *None* (default) the driver opens the first matching USB instrument.
    timeout_ms:
        VISA read/write timeout in milliseconds (default 10 000 ms).

    Can be used as a context manager::

        with VeraSol() as lamp:
            lamp.set_amplitude(0.5)
    """

    # Default VISA identifier substring used for auto-discovery
    _ID_QUERY_HINT = "LSS-7120"
    # Number of individually addressable LED channels
    NUM_LEDS = 19

    def __init__(
        self,
        resource_name: Optional[str] = None,
        timeout_ms: int = 10_000,
    ) -> None:
        self._rm = None

        # Direct Windows IVI USBTMC path — bypass pyvisa entirely
        if resource_name and resource_name.startswith("\\\\?\\"):
            self._resource_name = resource_name
            self._instr = _WinUSBTMC(resource_name, timeout_ms)
            return

        # Primary path: use pyvisa (NI-VISA or pyvisa-py)
        try:
            self._rm = pyvisa.ResourceManager()
            self._resource_name = resource_name or self._find_resource()
            self._instr = self._rm.open_resource(self._resource_name)
            self._instr.timeout = timeout_ms
            # The VeraSol acknowledges write commands with a 0-byte USB END
            # (EOM) message, not a text character.  Setting read_termination=""
            # disables NI-VISA's VI_ATTR_TERMCHAR_EN so reads terminate on the
            # USB END bit rather than waiting for "\n" (which never arrives).
            self._instr.read_termination  = ""
            self._instr.write_termination = "\n"
            return
        except (RuntimeError, pyvisa.errors.VisaIOError):
            if self._rm is not None:
                try:
                    self._rm.close()
                except Exception:
                    pass
                self._rm = None

        # Fallback: Windows IVI USBTMC class driver (auto-discover)
        win_path = _find_win_usbtmc_device()
        if win_path is None:
            raise RuntimeError(
                "No VeraSol instrument found via VISA or the Windows IVI USBTMC "
                "driver.  Check the USB cable and VISA driver installation."
            )
        self._resource_name = win_path
        self._instr = _WinUSBTMC(win_path, timeout_ms)

    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------

    def __enter__(self) -> "VeraSol":
        return self

    def __exit__(self, *_) -> None:
        self.close()

    def close(self) -> None:
        """Release the VISA resource."""
        try:
            self._instr.close()
        finally:
            if self._rm is not None:
                self._rm.close()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _find_resource(self) -> str:
        """Return the first USB resource that identifies as an LSS-7120."""
        resources = self._rm.list_resources("USB?*INSTR")
        if not resources:
            raise RuntimeError(
                "No USB INSTR resources found. Check the USB cable and VISA drivers."
            )
        for name in resources:
            try:
                instr = self._rm.open_resource(name)
                idn = instr.query("*IDN?").strip()
                instr.close()
                if self._ID_QUERY_HINT in idn:
                    return name
            except Exception:
                pass
        # Fall back to the first resource and let the user sort it out
        return resources[0]

    def _write(self, cmd: str) -> None:
        """Send a command and consume the mandatory 'Ready' acknowledgement.

        The VeraSol sends a 0-byte USB message with the EOM bit as its
        acknowledgement.  _WinUSBTMC translates that to the string "Ready";
        NI-VISA (via pyvisa) returns it as an empty string.  Both are valid.
        """
        self._instr.write(cmd)
        # Suppress pyvisa UserWarning: response arrives via USB END bit, not \n.
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            ack = self._instr.read().strip()
        # "" = NI-VISA encoding of 0-byte EOM ack; "ready" = _WinUSBTMC encoding.
        if ack and ack.lower() != "ready":
            raise RuntimeError(
                f"Unexpected acknowledgement for command '{cmd!r}': {ack!r}"
            )

    def _query(self, cmd: str) -> str:
        """Send a query and return the stripped response string."""
        return self._instr.query(cmd).strip()

    # ------------------------------------------------------------------
    # Identification
    # ------------------------------------------------------------------

    def identify(self) -> str:
        """Return the instrument identification string.

        Example: ``"Newport Corporation,LSS-7120,71201234,1.01"``
        """
        return self._query("*IDN?")

    # ------------------------------------------------------------------
    # Output control
    # ------------------------------------------------------------------

    def set_output(self, on: bool) -> None:
        """Turn the LED output on (``True``) or off (``False``)."""
        self._write(f"OUTPUT {'ON' if on else 'OFF'}")

    def get_output(self) -> bool:
        """Return *True* if the LED output is currently on."""
        response = self._query("OUTPUT?")
        return response.strip().upper() in ("ON", "1")

    # ------------------------------------------------------------------
    # Amplitude / intensity
    # ------------------------------------------------------------------

    def set_amplitude(self, suns: float) -> None:
        """Set the output intensity.

        Parameters
        ----------
        suns:
            Target irradiance in suns (0.1 – 1.0).  1.0 sun = 1 kW m⁻².
        """
        if suns < 0.1:
            raise ValueError(f"Amplitude must be ≥ 0.1 suns, got {suns}.")
        self._write(f"AMPLITUDE {suns:.3f}")

    def get_amplitude(self) -> float:
        """Return the current output amplitude in suns."""
        return float(self._query("AMPLITUDE?"))

    # ------------------------------------------------------------------
    # Individual LED power
    # ------------------------------------------------------------------

    def set_led_power(self, led: int, power_kw_m2: float) -> None:
        """Set the output power of a single LED channel."""
        self._validate_led_index(led)
        self._write(f"LEDPOWER {led},{power_kw_m2:.4f}")

    def get_led_power(self, led: int) -> float:
        """Return the current power set-point of *led* in kW m⁻²."""
        self._validate_led_index(led)
        return float(self._query(f"LEDPOWER? {led}"))

    def get_led_max_power(self, led: int) -> float:
        """Return the maximum allowed power of *led* in kW m⁻²."""
        self._validate_led_index(led)
        return float(self._query(f"LEDMAXPOWER? {led}"))

    def get_led_wavelength(self, led: int) -> float:
        """Return the peak wavelength of *led* in nm."""
        self._validate_led_index(led)
        return float(self._query(f"LEDWAVELENGTH? {led}"))

    def get_led_info(self, led: int) -> LEDInfo:
        """Return a :class:`LEDInfo` summary for *led*."""
        return LEDInfo(
            index=led,
            wavelength_nm=self.get_led_wavelength(led),
            power_kw_m2=self.get_led_power(led),
            max_power_kw_m2=self.get_led_max_power(led),
        )

    def get_all_led_info(self) -> list[LEDInfo]:
        """Return :class:`LEDInfo` for every LED channel (1 – NUM_LEDS)."""
        return [self.get_led_info(i) for i in range(1, self.NUM_LEDS + 1)]

    @staticmethod
    def _validate_led_index(led: int) -> None:
        if not (1 <= led <= 24):
            raise ValueError(f"LED index must be 1-24, got {led}.")

    # ------------------------------------------------------------------
    # Spectrum management
    # ------------------------------------------------------------------

    def store_spectrum(self, location: int) -> None:
        """Store the current LED spectrum to a memory slot (1–10)."""
        if not (1 <= location <= 10):
            raise ValueError(f"Storage location must be 1-10, got {location}.")
        self._write(f"SPECTRUM:STORE {location}")

    def recall_spectrum(self, location: int) -> None:
        """Recall a previously stored spectrum (0=AM1.5G, 1=custom, 2–10=user)."""
        if not (0 <= location <= 10):
            raise ValueError(f"Storage location must be 0-10, got {location}.")
        self._write(f"SPECTRUM:RECALL {location}")

    def get_active_spectrum_location(self) -> int:
        """Return the memory-location number of the currently active spectrum."""
        return int(self._query("SPECTRUM:ACTIVE?"))

    # ------------------------------------------------------------------
    # Calibration
    # ------------------------------------------------------------------

    def set_calibration_mode(self, mode: CalibrationMode) -> None:
        """Select factory (*DEFAULT*) or user-offset (*USER*) intensity calibration."""
        value = 0 if mode == CalibrationMode.DEFAULT else 1
        self._write(f"USERCAL:SELECT {value}")

    def get_calibration_mode(self) -> CalibrationMode:
        """Return the current calibration mode."""
        raw = int(self._query("USERCAL:SELECT?"))
        return CalibrationMode.USER if raw else CalibrationMode.DEFAULT

    def perform_user_calibration(self) -> None:
        """Execute the user-intensity calibration (rescales to 1.00 sun)."""
        self._write("USERCAL:PERFORM")

    # ------------------------------------------------------------------
    # Status and diagnostics
    # ------------------------------------------------------------------

    def get_status(self) -> LampStatus:
        """Return a decoded :class:`LampStatus` from the ``STATUS?`` query.

        Bit definitions (manual p. 30):
        - bit 0: output on
        - bit 2: head disconnected
        - bit 3: head warming up
        - bit 4: head over-temperature
        """
        raw = int(self._query("STATUS?"))
        return LampStatus(
            output_on=bool(raw & (1 << 0)),
            head_disconnected=bool(raw & (1 << 2)),
            head_warming_up=bool(raw & (1 << 3)),
            head_overtemperature=bool(raw & (1 << 4)),
            raw=raw,
        )

    def get_errors(self) -> list[str]:
        """Drain and return all queued error strings from the instrument."""
        errors: list[str] = []
        while True:
            response = self._query("ERROR?")
            if response.startswith("0"):
                break
            errors.append(response)
        return errors

    # ------------------------------------------------------------------
    # LED self-test
    # ------------------------------------------------------------------

    def run_led_test(self, timeout_s: float = 60.0) -> bool:
        """Trigger the LED self-test sequence (``LEDTEST:POWER?``)."""
        original_timeout = self._instr.timeout
        self._instr.timeout = int(timeout_s * 1000)
        try:
            result = self._query("LEDTEST:POWER?")
        finally:
            self._instr.timeout = original_timeout
        return result.strip() == "1"

    def get_led_test_result(self, led: int) -> tuple[float, float]:
        """Return ``(user_power, factory_power)`` in kW m⁻² for *led*."""
        self._validate_led_index(led)
        response = self._query(f"LEDTEST:RESULT? {led}")
        parts = [p.strip() for p in response.split(",")]
        return float(parts[0]), float(parts[1])

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------

    def wait_for_warmup(self, poll_interval_s: float = 5.0, timeout_s: float = 900.0) -> None:
        """Block until the LED head reaches operating temperature (~15 min)."""
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            status = self.get_status()
            if status.head_disconnected:
                raise RuntimeError("LED head is disconnected — check the CC720 cable.")
            if not status.head_warming_up:
                return
            time.sleep(poll_interval_s)
        raise TimeoutError(
            f"LED head did not reach operating temperature within {timeout_s:.0f} s."
        )

    def set_spectrum_am15g(self) -> None:
        """Convenience: recall the factory AM1.5G spectrum (location 0)."""
        self.recall_spectrum(0)

    def set_spectrum_custom(self) -> None:
        """Convenience: recall the front-panel 'custom' spectrum (location 1)."""
        self.recall_spectrum(1)


# ---------------------------------------------------------------------------
# Module-level convenience function
# ---------------------------------------------------------------------------

def list_instruments() -> list[str]:
    """Return resource strings for all connected USB INSTR / USBTMC devices."""
    rm = pyvisa.ResourceManager()
    try:
        resources: list[str] = list(rm.list_resources("USB?*INSTR"))
    except Exception:
        resources = []
    finally:
        rm.close()

    # Windows fallback: find any VeraSol reachable via the IVI USBTMC driver
    # that is not already listed as a VISA USB resource.
    win_path = _find_win_usbtmc_device()
    if win_path is not None and win_path not in resources:
        resources.append(win_path)

    return resources
