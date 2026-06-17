"""
Quick connection and output test for the VeraSol LSS-7120.

Works on Windows using the native IVI USBTMC class driver, bypassing
the NI-VISA enumeration issue where NI-VISA doesn't expose the device
as a USB INSTR resource.
"""

import ctypes
import struct
import time
from ctypes import byref, c_ulong, create_string_buffer, windll

DEVICE_PATH = (
    r"\\?\USB#VID_1FDE&PID_000A&MI_00"
    r"#6&109d9d3c&0&0000"
    r"#{a9fdbb24-128a-11d5-9961-00108335e361}"
)

GENERIC_READ  = 0x80000000
GENERIC_WRITE = 0x40000000
OPEN_EXISTING = 3
FILE_SHARE_READ  = 1
FILE_SHARE_WRITE = 2


class RawUSBTMC:
    """Minimal USBTMC transport over the Windows IVI class driver."""

    def __init__(self, path: str):
        self._h = windll.kernel32.CreateFileW(
            path,
            GENERIC_READ | GENERIC_WRITE,
            FILE_SHARE_READ | FILE_SHARE_WRITE,
            None, OPEN_EXISTING, 0, None,
        )
        if self._h == ctypes.c_void_p(-1).value:
            raise OSError(f"Could not open device ({ctypes.GetLastError()}): {path}")
        self._btag = 0

    def close(self):
        if self._h and self._h != -1:
            windll.kernel32.CloseHandle(self._h)
            self._h = None

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def _next_tag(self) -> int:
        self._btag = (self._btag % 255) + 1
        return self._btag

    def write(self, msg: str) -> None:
        data = (msg.rstrip("\n") + "\n").encode()
        tag = self._next_tag()
        header = struct.pack(
            "<BBBBIBxxx",
            0x01, tag, (~tag) & 0xFF, 0,
            len(data), 0x01,  # EOM bit set
        )
        packet = header + data
        packet += b"\x00" * ((4 - len(packet) % 4) % 4)
        buf = create_string_buffer(packet)
        written = c_ulong(0)
        if not windll.kernel32.WriteFile(self._h, buf, len(packet), byref(written), None):
            raise OSError(f"WriteFile failed: {ctypes.GetLastError()}")

    def read(self, max_bytes: int = 4096) -> str:
        tag = self._next_tag()
        req = struct.pack(
            "<BBBBIBxxx",
            0x02, tag, (~tag) & 0xFF, 0,
            max_bytes, 0x00,
        )
        buf_req = create_string_buffer(req)
        written = c_ulong(0)
        windll.kernel32.WriteFile(self._h, buf_req, len(req), byref(written), None)

        buf_resp = create_string_buffer(max_bytes + 12)
        read_bytes = c_ulong(0)
        if not windll.kernel32.ReadFile(self._h, buf_resp, max_bytes + 12, byref(read_bytes), None):
            raise OSError(f"ReadFile failed: {ctypes.GetLastError()}")
        n = read_bytes.value
        if n < 12:
            return ""
        payload_len = struct.unpack_from("<I", buf_resp.raw, 4)[0]
        return buf_resp.raw[12 : 12 + payload_len].decode("ascii", errors="replace").strip()

    def query(self, msg: str) -> str:
        self.write(msg)
        return self.read()


def run_test():
    print("=" * 55)
    print("VeraSol LSS-7120 Connection & Output Test")
    print("=" * 55)

    with RawUSBTMC(DEVICE_PATH) as dev:
        # 1. Identity
        idn = dev.query("*IDN?")
        print(f"IDN : {idn}")

        # 2. Status
        status_raw = dev.query("STATUS?")
        status_val = int(status_raw)
        output_on       = bool(status_val & (1 << 0))
        head_disconnect = bool(status_val & (1 << 2))
        warming_up      = bool(status_val & (1 << 3))
        overtemp        = bool(status_val & (1 << 4))
        print(f"\nStatus (raw={status_val}):")
        print(f"  Output on       : {output_on}")
        print(f"  Head connected  : {not head_disconnect}")
        print(f"  Warming up      : {warming_up}")
        print(f"  Over-temperature: {overtemp}")

        if head_disconnect:
            print("\n[WARN] Head is disconnected — skipping output test.")
            return

        # 3. Current amplitude
        amp = dev.query("AMPLITUDE?")
        print(f"\nAmplitude: {amp} sun(s)")

        # 4. Toggle output
        initial_state = dev.query("OUTPUT?").strip()
        print(f"\nCurrent output state : {initial_state}")

        print("\n--- Turning OUTPUT ON ---")
        dev.write("OUTPUT ON")
        dev.read()                  # consume 'Ready'
        time.sleep(0.5)
        state = dev.query("OUTPUT?")
        print(f"Output after ON cmd  : {state}")
        assert state.strip() == "1", f"Expected '1', got {state!r}"

        print("\n--- Turning OUTPUT OFF ---")
        dev.write("OUTPUT OFF")
        dev.read()                  # consume 'Ready'
        time.sleep(0.5)
        state = dev.query("OUTPUT?")
        print(f"Output after OFF cmd : {state}")
        assert state.strip() == "0", f"Expected '0', got {state!r}"

        # Restore original state
        if initial_state == "1":
            dev.write("OUTPUT ON")
            dev.read()
            print("\n(Restored output to ON)")

        # 5. Error queue
        errors = dev.query("SYSTEM:ERROR?")
        print(f"\nError queue: {errors}")

        print("\n[PASS] All output tests passed.")


if __name__ == "__main__":
    run_test()
