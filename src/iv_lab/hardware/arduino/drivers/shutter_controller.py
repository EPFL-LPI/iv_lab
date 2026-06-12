"""Real Arduino shutter / cell-selection controller (via ``pyvisa``).

Migrated from the legacy ``arduino`` class in ``IVLab/IVlab.py``
(``IV_Old`` system). Despite the name, the device speaks a Newport
LSS-7120-style protocol: the connection is verified with a
``*IDN?`` query expected to start with
``Newport Corporation,LSS-7120``, and commands are plain ASCII writes
of the form ``"6,<pin>,<value>"`` (legacy ``arduino_digital_command``;
6 selects the digital-command opcode):

- pin 2: shutter, 1 = open / 0 = closed,
- pin 4: cell stage, 1 = test cell / 0 = reference cell (followed by
  the legacy 5 s settling wait).

``pyvisa`` is imported only at connection time in ``_open()``.
"""

from __future__ import annotations

import time

from iv_lab.config import ArduinoSettings
from iv_lab.hardware.errors import HardwareConnectionError

from ..base import BaseArduino
from ..registry import register_arduino_driver

#: Expected start of the *IDN? reply (legacy check).
ARDUINO_IDN_PREFIX = "Newport Corporation,LSS-7120"
#: Legacy serial settings.
BAUD_RATE = 115200


@register_arduino_driver("Arduino", "Uno")
class ArduinoShutterController(BaseArduino):
    """Shutter / cell-stage controller driven over VISA."""

    def __init__(self, settings: ArduinoSettings) -> None:
        super().__init__(settings)
        self.visa_address = settings.visa_address
        self.rm = None
        self.ard = None

    def _open(self) -> None:
        # deferred import: must not be loaded at package import time
        import pyvisa

        self.rm = pyvisa.ResourceManager()
        self.ard = self.rm.open_resource(self.visa_address)

        # legacy communication settings
        self.ard.baud_rate = BAUD_RATE
        self.ard.read_termination = r"\n"
        self.ard.write_termination = r"\n"
        self.ard.send_end = True
        self.ard.query_delay = 0.05
        self.ard.timeout = 1000

        # verify identifier to be sure we have a good connection (the
        # legacy message said "Oriel lamp" here by copy-paste accident)
        idn = self.ard.query("*IDN?")
        if idn[0 : len(ARDUINO_IDN_PREFIX)] != ARDUINO_IDN_PREFIX:
            raise HardwareConnectionError("Arduino controller IDN incorrect: " + idn)

    def _close(self) -> None:
        self.ard.close()

    def _digital_command(self, pin: int, value: int) -> None:
        """Send a digital command (legacy ``arduino_digital_command``)."""
        if self.ard is None:
            raise HardwareConnectionError(f"{self.name}: not connected")
        self.ard.write("6," + str(int(pin)) + "," + str(int(value)))

    def open_shutter(self) -> None:
        self._digital_command(2, 1)

    def close_shutter(self) -> None:
        self._digital_command(2, 0)

    def select_reference_cell(self) -> None:
        self._digital_command(4, 0)
        time.sleep(self.cell_stage_settling_time)

    def select_test_cell(self) -> None:
        self._digital_command(4, 1)
        time.sleep(self.cell_stage_settling_time)
