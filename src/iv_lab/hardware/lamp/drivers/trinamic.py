"""Trinamic stepper-motor filter wheel driver (via ``pytrinamic``).

Migrated from the Trinamic branches of the legacy ``lamp`` class in
``IVLab/IVlab.py``. Supports the TMCM-1260, TMCM-1160, and TMCM-3110
modules. ``pytrinamic`` is imported only at connection time (the legacy
code imported it in ``lamp.__init__``; per docs/HARDWARE.md it is now
deferred to ``_open()``).

``lightLevelDict`` maps light level in % sun to a filter wheel angle in
degrees. Connecting homes the wheel (reference search) and moves it to
the dark position; ``light_on`` moves to the angle for the requested
level. Trinamic connections are opened per operation and not kept open
(legacy behavior; note that legacy passes the ``--data-rate 9600``
option for the TMCM-1160 only when homing, not when moving — preserved).
"""

from __future__ import annotations

import time
from typing import Optional

from iv_lab.config import LampSettings
from iv_lab.hardware.errors import HardwareConnectionError, HardwareTimeoutError
from iv_lab.hardware.smu.base import BaseSMU

from ..base import BaseLamp
from ..registry import register_lamp_driver

#: Legacy timeouts in seconds.
TRINAMIC_HOMING_TIMEOUT = 15.0
TRINAMIC_MOVE_TIMEOUT = 12.0


@register_lamp_driver("Trinamic", "TMCM-1260", "TMCM-1160", "TMCM-3110")
class TrinamicFilterWheelLamp(BaseLamp):
    """Filter wheel on a Trinamic stepper motor module."""

    def __init__(self, settings: LampSettings, smu: Optional[BaseSMU] = None) -> None:
        super().__init__(settings, smu=smu)
        self.model = settings.model

        self.trinamic_homing_timeout = TRINAMIC_HOMING_TIMEOUT
        self.trinamic_move_timeout = TRINAMIC_MOVE_TIMEOUT
        #: Poll intervals (legacy: 0.1 s while homing, 0.2 s while moving).
        self.homing_poll_interval = 0.1
        self.move_poll_interval = 0.2

        # motor parameters; microstep resolution is read from the motor
        # enum on connect (legacy stored MicrostepResolution256Microsteps)
        self.steps_per_revolution = 200
        self.microstep_resolution: Optional[int] = None

        self._connection_manager_cls = None
        self._module_cls = None

    # --- pytrinamic plumbing ---

    def _import_pytrinamic(self) -> None:
        # deferred import: must not be loaded at package import time
        from pytrinamic.connections import ConnectionManager

        if self.model == "TMCM-1260":
            from pytrinamic.modules import TMCM1260 as module_cls
        elif self.model == "TMCM-1160":
            from pytrinamic.modules import TMCM1160 as module_cls
        elif self.model == "TMCM-3110":
            from pytrinamic.modules import TMCM3110 as module_cls
        else:
            # unreachable through the registry; legacy raised in __init__
            raise ValueError(f"Trinamic module {self.model} is not supported")

        self._connection_manager_cls = ConnectionManager
        self._module_cls = module_cls

    def convert_angle_to_microsteps(self, angle: float) -> int:
        """Legacy helper: wheel angle in degrees -> motor microsteps."""
        microsteps_per_full_step = 2**self.microstep_resolution
        return int(angle * (self.steps_per_revolution / 360) * microsteps_per_full_step)

    def _wait_for_position(self, motor, timeout: float, poll_interval: float) -> None:
        """Poll ``get_position_reached`` until done or ``timeout`` elapses."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            if motor.get_position_reached():
                break
            time.sleep(poll_interval)

        if not motor.get_position_reached():
            motor.stop()
            raise HardwareTimeoutError("ERROR: Could not move motor to off position")

    def _configure_motor(self, motor) -> None:
        """Legacy drive settings shared by homing and configuration."""
        motor.drive_settings.max_current = 128
        motor.drive_settings.standby_current = 32
        motor.drive_settings.boost_current = 0
        self.microstep_resolution = motor.ENUM.MicrostepResolution256Microsteps
        motor.drive_settings.microstep_resolution = self.microstep_resolution

        if self.model == "TMCM-1260":
            motor.linear_ramp.max_velocity = 5000
            motor.linear_ramp.max_acceleration = 20000
            # reference search mode 7 (home switch in positive direction),
            # switch polarity inverted by or'ing in 128
            motor.set_axis_parameter(193, 135)
            motor.set_axis_parameter(194, 5000)  # rough search speed
            motor.set_axis_parameter(195, 2000)  # fine search speed
        elif self.model in ("TMCM-3110", "TMCM-1160"):
            motor.linear_ramp.max_velocity = 200
            motor.linear_ramp.max_acceleration = 50
            motor.set_axis_parameter(193, 135)
            motor.set_axis_parameter(194, 200)
            motor.set_axis_parameter(195, 50)
        else:
            raise ValueError(f"ERROR: Trinamic model {self.model} is not configured")

    # --- connection: home the wheel and park it dark (legacy connect) ---

    def _open(self) -> None:
        self._import_pytrinamic()

        # legacy: the data-rate option is used for the TMCM-1160 here only
        option_string = "--data-rate 9600" if self.model == "TMCM-1160" else ""

        with self._connection_manager_cls(option_string).connect() as interface:
            module = self._module_cls(interface)
            motor = module.motors[0]
            self._configure_motor(motor)

            # home the motor (reference search); poll until done
            interface.reference_search(0, 0)  # start (type, motor)
            deadline = time.time() + self.trinamic_homing_timeout
            while time.time() < deadline:
                if interface.reference_search(2, 0) == 0:  # status poll
                    break
                time.sleep(self.homing_poll_interval)

            if interface.reference_search(2, 0) != 0:
                interface.reference_search(1, 0)  # stop the search
                raise HardwareConnectionError("ERROR: Unable to reference filter wheel")

            # move the filter wheel to the 'off' (dark) position
            angle = self._light_level_value(0)
            motor.move_to(self.convert_angle_to_microsteps(angle))
            self._wait_for_position(
                motor, self.trinamic_move_timeout, self.homing_poll_interval
            )

    def _close(self) -> None:
        # trinamic connections are not kept open; nothing to close (legacy)
        pass

    # --- moving (legacy trinamic_move_to_position) ---

    def _move_to_angle(self, angle: float) -> None:
        # legacy opens a fresh connection per move, without the data-rate
        # option string (even for the TMCM-1160)
        with self._connection_manager_cls().connect() as interface:
            module = self._module_cls(interface)
            motor = module.motors[0]

            motor.move_to(self.convert_angle_to_microsteps(angle))
            self._wait_for_position(
                motor, self.trinamic_move_timeout, self.move_poll_interval
            )

            interface.close()

    # --- lamp interface ---

    def light_on(self, light_int: float = 100.0) -> None:
        self.light_is_on = False

        angle = self._light_level_value(light_int)
        self._move_to_angle(angle)

        self.light_int = light_int
        self.light_is_on = True

    def light_off(self) -> None:
        # legacy: only moves if the light is considered on
        if self.light_is_on:
            angle = self._light_level_value(0)
            self._move_to_angle(angle)

        self.light_is_on = False
