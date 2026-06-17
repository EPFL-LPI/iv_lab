"""Wavelabs Sinus70 solar simulator driver (TCP socket protocol).

Migrated from the Wavelabs branches of the legacy ``lamp`` class in
``IVLab/IVlab.py``. The Wavelabs control software connects *to us*: for
every command the driver opens a listening socket on 127.0.0.1:55555,
accepts the connection from the Wavelabs software, exchanges one or two
WLRC XML messages, and closes the socket again (legacy
``wavelabs_connect`` / ``wavelabs_disconnect``).

``lightLevelDict`` maps light level in % sun to a Wavelabs recipe name.
Turning the light on activates and starts the recipe; turning it off
cancels it. Level 0 is special-cased like in legacy: the recipe lookup
must succeed, but no hardware action is taken (and ``light_is_on`` still
becomes True — legacy behavior).

Only the standard library ``socket`` module is used; there is no
optional hardware dependency.
"""

from __future__ import annotations

import socket

from iv_lab.config import LampSettings
from iv_lab.hardware.errors import HardwareCommandError
from iv_lab.hardware.smu.base import BaseSMU

from ..base import BaseLamp
from ..registry import register_lamp_driver

#: Legacy server address the Wavelabs software connects to.
WAVELABS_ADDRESS = ("127.0.0.1", 55555)


@register_lamp_driver("Wavelabs", "Sinus70")
class WavelabsLamp(BaseLamp):
    """Wavelabs Sinus70 driven through its WLRC TCP protocol."""

    def __init__(self, settings: LampSettings, smu: BaseSMU | None = None) -> None:
        super().__init__(settings, smu=smu)
        self.connection_open = False
        self.seq_num = 0
        self.sock = None
        self.connection = None

    # the lamp itself needs no persistent connection (legacy connect had
    # no Wavelabs branch); sockets are opened per command
    def _open(self) -> None:
        pass

    def _close(self) -> None:
        pass

    # --- WLRC socket protocol (legacy wavelabs_* helpers) ---

    def _wavelabs_connect(self) -> None:
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind(WAVELABS_ADDRESS)
        self.sock.settimeout(5)
        self.sock.listen(1)
        # wait for the Wavelabs software to connect
        self.connection, _client_address = self.sock.accept()
        self.connection.settimeout(1)
        self.connection_open = True
        self.seq_num = 0

    def _wavelabs_disconnect(self) -> None:
        self.connection.close()
        self.sock.close()
        self.connection_open = False

    def _send_command(self, message: str) -> str:
        """Send one WLRC message and collect the reply (legacy recv loop)."""
        self.connection.sendall(bytes(message, "utf-8"))
        self.seq_num += 1

        reply = ""
        while True:
            try:
                data = self.connection.recv(16)
                reply += str(data, "utf-8")
                if len(data) < 16:
                    break
            except Exception:
                break
        return reply

    @staticmethod
    def _extract_error_string(reply: str) -> tuple[bool, str]:
        """Legacy ``wavelabs_extract_error_string``: (is_error, message)."""
        if reply.find("iEC='0'") != -1:
            return (False, "No Error")

        start_index = reply.find("sError=")
        end_index = reply.find(r"\>")
        if start_index == -1 or end_index == -1:
            return (True, "Did not receive proper reply from Wavelabs")
        return (True, reply[start_index + 8 : end_index - 1])

    # --- lamp interface ---

    def light_on(self, light_int: float = 100.0) -> None:
        self.light_is_on = False

        # legacy: the level must be defined even if it is 0
        recipe_name = self._light_level_value(light_int)

        if light_int == 0:
            pass  # do nothing - light is not turned on
        else:
            self._wavelabs_connect()

            reply = self._send_command(
                f"<WLRC><ActivateRecipe iSeq='{self.seq_num}' "
                f"sRecipe='{recipe_name}'/></WLRC>"
            )
            err, err_string = self._extract_error_string(reply)
            if err:
                self._wavelabs_disconnect()
                raise HardwareCommandError(
                    "Error from Wavelabs Activate Recipe:\n" + err_string
                )

            reply = self._send_command(f"<WLRC><StartRecipe iSeq='{self.seq_num}'/></WLRC>")
            self._wavelabs_disconnect()
            err, err_string = self._extract_error_string(reply)
            if err:
                raise HardwareCommandError(
                    "Error from Wavelabs Start Recipe:\n" + err_string
                )

        self.light_int = light_int
        # legacy: if we get here without error the light counts as on,
        # including the 0 % sun case
        self.light_is_on = True

    def light_off(self) -> None:
        if self.light_is_on:
            self._wavelabs_connect()
            reply = self._send_command(f"<WLRC><CancelRecipe iSeq='{self.seq_num}'/></WLRC>")
            self._wavelabs_disconnect()

            # legacy: checked last because the raise aborts everything after
            # it — on error light_is_on stays True, so light_off can be retried
            err, err_string = self._extract_error_string(reply)
            if err:
                raise HardwareCommandError(
                    "Error from Wavelabs Cancel Recipe:\n" + err_string
                )

        self.light_is_on = False

    def turn_off(self) -> None:
        # legacy turn_off: close the socket if a command left it open
        if self.connection_open:
            self._wavelabs_disconnect()
