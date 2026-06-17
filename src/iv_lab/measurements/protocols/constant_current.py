"""Constant-current (measure voltage vs. time) protocol.

Migrated from the legacy ``system.measure_V_time_dependent`` and
``SMU.measure_V_time_dependent`` in ``IVLab/IVlab.py`` (the legacy GUI
calls this "Constant Current, Measure V").

``params`` (legacy keys): ``light_int``, ``set_current``, ``interval``,
``duration``, ``Imax``, ``Vmax``, ``Dwell``, ``Nwire``,
``active_area``, ``cell_name``.
"""

from __future__ import annotations

import datetime
import time
from collections.abc import Callable

from iv_lab.data import ConstantCurrentResults
from iv_lab.hardware.smu.base import BaseSMU, SMUChannel

from .base import MeasurementProtocol, _nwire_value


def measure_voltage_vs_time(
    smu: BaseSMU,
    params: dict,
    *,
    status: Callable[[str], None],
    cancelled: Callable[[], bool],
    emit_data: Callable[[dict], None],
) -> tuple[list[float], list[float]]:
    """Timed voltage measurement at a fixed current (legacy
    ``SMU.measure_V_time_dependent``).

    Returns ``(t, v)``. The legacy loop records no reference diode data.
    The SMU is turned off at the end (legacy).
    """
    p = params
    data_t: list[float] = []
    data_v: list[float] = []

    if abs(p["set_current"]) > abs(p["Imax"]):
        raise ValueError(
            "ERROR: measure_V_time_dependent set current outside of compliance range"
        )

    if smu.use_reference_diode and smu.reference_diode_parallel:
        smu.setup_reference_diode()

    # apply compliance settings
    smu.set_voltage_limit(SMUChannel.CELL, p["Vmax"])
    smu.set_current_limit(SMUChannel.CELL, p["Imax"])

    smu.set_sense_mode(SMUChannel.CELL, _nwire_value(p["Nwire"]))
    smu.setup_current_output(SMUChannel.CELL, p["Vmax"])
    smu.set_current(SMUChannel.CELL, p["set_current"])
    smu.enable_output(SMUChannel.CELL)

    status(
        "Stabilizing at initial operating point for " + str(p["Dwell"]) + " seconds"
    )

    deadline = time.time() + p["Dwell"]
    while time.time() < deadline:
        smu.measure_voltage(SMUChannel.CELL)
        if cancelled():
            break

    status("Running Constant Current Measurement...")

    start_time = time.time()
    meas_time = start_time  # first measurement at time zero
    while (time.time() - start_time) < p["duration"]:
        now = time.time()
        if now >= meas_time:
            v = smu.measure_voltage(SMUChannel.CELL)
            data_v.append(v)
            data_t.append(now - start_time)

            emit_data({"t": list(data_t), "v": list(data_v)})

            meas_time = meas_time + p["interval"]
        else:
            # dummy measurement to keep the instrument display alive (legacy)
            smu.measure_voltage(SMUChannel.CELL)

        if cancelled():
            break

    smu.turn_off()

    return (data_t, data_v)


class ConstantCurrentProtocol(MeasurementProtocol):
    """Constant current, measure voltage (legacy
    ``system.measure_V_time_dependent``)."""

    def run(self, params: dict) -> ConstantCurrentResults:
        p = dict(params)
        start_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

        if abs(p["set_current"]) > abs(p["Imax"]):
            raise ValueError(
                "ERROR: measure_V_time_dependent set current outside of compliance range"
            )

        # check that the SMU can handle the requested measurement interval
        if p["interval"] < self.smu.meas_period_min:
            p["interval"] = self.smu.meas_period_min
            self.warn(
                "WARNING: the SMU is unable to provide the requested measurement rate.\n"
                "The measurement interval has been set to the maximum allowed by the SMU."
            )

        result = ConstantCurrentResults(
            start_time=start_time,
            active_area=p["active_area"],
            cell_name=p["cell_name"],
            light_int=p["light_int"],
            set_current=p["set_current"],
            Nwire=p["Nwire"],
            interval=p["interval"],
            duration=p["duration"],
        )

        self.status("Turning lamp on...")
        self.turn_lamp_on(p["light_int"])
        try:
            if self.smu.use_reference_diode:
                light_intensity = self.check_light_level(p["light_int"])
                if self.cancelled():
                    self.status("Run Aborted")
                    return result
                result.light_int_meas = light_intensity

            self.status("Running Constant Current Measurement...")
            t, v_smu = measure_voltage_vs_time(
                self.smu,
                p,
                status=self.status,
                cancelled=self.cancelled,
                emit_data=self.emit_data,
            )

            result.time = t
            result.voltage = v_smu
            # legacy fills the current column with the setpoint
            result.current = [p["set_current"]] * len(v_smu)

            if self.cancelled():
                self.status("Run Aborted")
            else:
                self.status("Run finished")
            return result
        finally:
            self.smu.turn_off()
            self.status("Turning lamp off...")
            self.turn_lamp_off()
