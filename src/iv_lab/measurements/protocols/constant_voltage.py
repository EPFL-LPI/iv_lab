"""Constant-voltage (measure current vs. time) protocol.

Migrated from the legacy ``system.measure_I_time_dependent`` and
``SMU.measure_I_time_dependent`` in ``IVLab/IVlab.py`` (the legacy GUI
calls this "Constant Voltage, Measure J").

``params`` (legacy keys): ``light_int``, ``set_voltage``, ``interval``,
``duration``, ``Imax``, ``Vmax``, ``Dwell``, ``Nwire``,
``active_area``, ``cell_name``.
"""

from __future__ import annotations

import datetime
import time
from collections.abc import Callable

from iv_lab.data import ConstantVoltageResults
from iv_lab.hardware.smu.base import BaseSMU, SMUChannel

from .base import MeasurementProtocol, _nwire_value


def measure_current_vs_time(
    smu: BaseSMU,
    params: dict,
    *,
    status: Callable[[str], None],
    cancelled: Callable[[], bool],
    emit_data: Callable[[dict], None],
) -> tuple[list[float], list[float], list[float]]:
    """Timed current measurement at a fixed voltage (legacy
    ``SMU.measure_I_time_dependent``).

    Returns ``(t, i, i_ref)``; ``i_ref`` is all zeros without parallel
    reference measurement. The SMU is turned off at the end (legacy).
    This loop is also reused by the reference diode calibration on the
    IV_Old system.
    """
    p = params
    data_t: list[float] = []
    data_i: list[float] = []
    data_i_ref: list[float] = []
    data_j: list[float] = []

    if abs(p["set_voltage"]) > abs(p["Vmax"]):
        raise ValueError(
            "ERROR: measure_I_time_dependent set voltage outside of compliance range"
        )

    parallel_reference = smu.use_reference_diode and smu.reference_diode_parallel
    if parallel_reference:
        smu.setup_reference_diode()

    # apply compliance settings
    smu.set_voltage_limit(SMUChannel.CELL, p["Vmax"])
    smu.set_current_limit(SMUChannel.CELL, p["Imax"])

    smu.set_sense_mode(SMUChannel.CELL, _nwire_value(p["Nwire"]))
    smu.setup_voltage_output(SMUChannel.CELL, p["Imax"])
    smu.set_voltage(SMUChannel.CELL, p["set_voltage"])
    smu.enable_output(SMUChannel.CELL)

    status(
        "Stabilizing at initial operating point for " + str(p["Dwell"]) + " seconds"
    )

    deadline = time.time() + p["Dwell"]
    while time.time() < deadline:
        if parallel_reference:
            smu.measure_both_currents()
        else:
            smu.measure_current(SMUChannel.CELL)
        if cancelled():
            break

    status("Running Constant Voltage Measurement...")

    active_area = p.get("active_area", 1.0)
    start_time = time.time()
    meas_time = start_time  # first measurement at time zero
    while (time.time() - start_time) < p["duration"]:
        now = time.time()
        if now >= meas_time:
            if parallel_reference:
                i, i_ref = smu.measure_both_currents()
                data_i_ref.append(i_ref)
            else:
                i = smu.measure_current(SMUChannel.CELL)
                data_i_ref.append(0.0)

            data_i.append(i)
            data_j.append(i * 1000.0 / active_area)
            data_t.append(now - start_time)

            emit_data({"t": list(data_t), "j": list(data_j)})

            # Skip any already-elapsed intervals so burst catch-up doesn't
            # produce duplicate timestamps when the SMU returns instantly.
            meas_time += p["interval"]
            while meas_time <= now:
                meas_time += p["interval"]
        else:
            # dummy measurement to keep the instrument display alive (legacy)
            if parallel_reference:
                smu.measure_both_currents()
            else:
                smu.measure_current(SMUChannel.CELL)

        if cancelled():
            break

    smu.turn_off()

    return (data_t, data_i, data_i_ref)


class ConstantVoltageProtocol(MeasurementProtocol):
    """Constant voltage, measure current (legacy
    ``system.measure_I_time_dependent``)."""

    def run(self, params: dict) -> ConstantVoltageResults:
        p = dict(params)
        start_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

        if abs(p["set_voltage"]) > abs(p["Vmax"]):
            raise ValueError(
                "ERROR: measure_I_time_dependent set voltage outside of compliance range"
            )

        # check that the SMU can handle the requested measurement interval
        if p["interval"] < self.smu.meas_period_min:
            p["interval"] = self.smu.meas_period_min
            self.warn(
                "WARNING: the SMU is unable to provide the requested measurement rate.\n"
                "The measurement interval has been set to the maximum allowed by the SMU."
            )

        result = ConstantVoltageResults(
            start_time=start_time,
            active_area=p["active_area"],
            cell_name=p["cell_name"],
            light_int=p["light_int"],
            set_voltage=p["set_voltage"],
            Nwire=p["Nwire"],
            interval=p["interval"],
            duration=p["duration"],
        )

        self.status("Turning lamp on...")
        self.turn_lamp_on(p["light_int"])
        light_intensity: float | None = None
        try:
            if self.smu.use_reference_diode:
                light_intensity = self.check_light_level(p["light_int"])
                if self.cancelled():
                    self.status("Run Aborted")
                    return result

            self.status("Running Constant Voltage Measurement...")
            t, i_smu, i_ref = measure_current_vs_time(
                self.smu,
                p,
                status=self.status,
                cancelled=self.cancelled,
                emit_data=self.emit_data,
            )

            # average light level (legacy)
            if self.smu.use_reference_diode:
                if self.smu.reference_diode_parallel and i_ref:
                    avg_ref_current = sum(i_ref) / len(i_ref)
                    avg_light_level = abs(
                        100.0 * avg_ref_current / self.smu.full_sun_reference_current
                    )
                else:  # measured once at the beginning
                    avg_light_level = light_intensity
                result.light_int_meas = avg_light_level

            result.time = t
            result.voltage = [p["set_voltage"]] * len(i_smu)
            result.current = i_smu
            result.current_reference = i_ref

            if self.cancelled():
                self.status("Run Aborted")
            else:
                self.status("Run finished")
            return result
        finally:
            self.smu.turn_off()
            self.status("Turning lamp off...")
            self.turn_lamp_off()
