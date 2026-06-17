"""Oriel LSS-7120 solar simulator driver (via ``pyvisa``).

Migrated from the Oriel branches of the legacy ``lamp`` class in
``IVLab/IVlab.py``. ``pyvisa`` is imported only at connection time in
``_open()`` (see docs/HARDWARE.md).

The LSS-7120 is controlled with simple ASCII commands: ``AMPL`` sets the
output amplitude, ``OUTP ON``/``OUTP OFF`` switches the lamp, and both
are verified by querying back (legacy behavior, including the legacy
verification tolerances).
"""

from __future__ import annotations

from iv_lab.config import LampSettings
from iv_lab.hardware.errors import HardwareCommandError, HardwareConnectionError
from iv_lab.hardware.smu.base import BaseSMU

from ..base import BaseLamp
from ..registry import register_lamp_driver

#: Expected start of the *IDN? reply (legacy check).
ORIEL_IDN_PREFIX = "Newport Corporation,LSS-7120"


@register_lamp_driver("Oriel", "LSS-7120")
class OrielLSS7120Lamp(BaseLamp):
    """Oriel LSS-7120 driven over VISA."""

    def __init__(self, settings: LampSettings, smu: BaseSMU | None = None) -> None:
        super().__init__(settings, smu=smu)
        if settings.visa_address is None:
            raise ValueError("Oriel LSS-7120 lamp requires a 'visa_address' setting")
        self.visa_address = settings.visa_address
        self.rm = None
        self.lss = None

    def _open(self) -> None:
        # deferred import: must not be loaded at package import time
        import pyvisa

        self.rm = pyvisa.ResourceManager()
        self.lss = self.rm.open_resource(self.visa_address)

        # legacy communication settings
        self.lss.read_termination = r"\n\003"
        self.lss.write_termination = r"\n"
        self.lss.send_end = True
        self.lss.query_delay = 0.05
        self.lss.timeout = 1000

        # verify identifier to be sure we have a good connection
        idn = self.lss.query("*IDN?")
        if idn[0 : len(ORIEL_IDN_PREFIX)] != ORIEL_IDN_PREFIX:
            raise HardwareConnectionError("Oriel lamp IDN incorrect: " + idn)

    def _close(self) -> None:
        self.lss.close()

    def light_on(self, light_int: float = 100.0) -> None:
        self.light_is_on = False

        self.lss.write("AMPL " + str(light_int / 100))

        # query the setpoint to verify that it was properly set; legacy
        # compares the reply to the % sun value with a 0.5 tolerance
        light_setp = float(self.lss.query("AMPL?"))
        if abs(light_setp - light_int) > 0.5:
            raise HardwareCommandError("ERROR: Oriel Light intensity not properly set")

        # enable the output and verify that the lamp truly turned on
        self.lss.write("OUTP ON")
        if self.lss.query("OUTP?") != "ON":
            raise HardwareCommandError("ERROR: Oriel lamp did not turn on when requested")

        self.light_int = light_int
        self.light_is_on = True

    def light_off(self) -> None:
        if self.light_is_on:
            # disable the output and verify that the lamp truly turned off
            self.lss.write("OUTP OFF")
            if self.lss.query("OUTP?") != "OFF":
                raise HardwareCommandError(
                    "ERROR: Oriel lamp did not turn off when requested"
                )

        self.light_is_on = False
