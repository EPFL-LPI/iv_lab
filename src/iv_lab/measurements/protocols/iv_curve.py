"""J-V scan protocol.

Migrated from the legacy ``system.measure_IVcurve`` and
``SMU.measure_IV_point_by_point`` in ``IVLab/IVlab.py``.

``params`` (legacy keys): ``light_int``, ``start_V`` (may be ``'Voc'``),
``stop_V`` (may be ``'Voc'``), ``dV``, ``sweep_rate``, ``Imax``,
``Vmax``, ``Dwell``, ``Nwire``, ``active_area``, ``cell_name``, and
``Fwd_current_limit`` (used for ``'Voc'`` limits).
"""

from __future__ import annotations

import datetime
import time
from typing import Callable, Optional

from iv_lab.analysis.jv_metrics import JVMetrics, compute_jv_metrics, pce
from iv_lab.data import IVResults
from iv_lab.hardware.smu.base import BaseSMU, SMUChannel

from .base import MeasurementProtocol, VocPolarityError, _nwire_value, linspace

MetricsFunction = Callable[..., JVMetrics]


def scan_iv_points(
    smu: BaseSMU,
    params: dict,
    *,
    status: Callable[[str], None],
    cancelled: Callable[[], bool],
    emit_data: Callable[[dict], None],
) -> tuple[list[float], list[float], list[float]]:
    """Point-by-point J-V scan (legacy ``SMU.measure_IV_point_by_point``).

    Mutates ``params`` like the legacy code did (``'Voc'`` start/stop
    resolution, minimum dwell) — callers pass their own copy. Returns
    ``(v, i, i_ref)``; ``i_ref`` is all zeros without parallel reference
    measurement. The SMU is turned off at the end (legacy).
    """
    p = params

    # flag to abort the scan when it reaches Voc (positive-going scans)
    stop_at_voc = False
    if p["start_V"] == "Voc":
        # resolved on the fly at the start of the scan to avoid
        # polarization effects in the solar cell
        pass
    elif p["stop_V"] == "Voc":
        stop_at_voc = True
        p["stop_V"] = p["Vmax"]
    else:
        if abs(p["start_V"]) > abs(p["Vmax"]):
            raise ValueError(
                "ERROR: measure_IVcurve start voltage outside of compliance range"
            )
        if abs(p["stop_V"]) > abs(p["Vmax"]):
            raise ValueError(
                "ERROR: measure_IVcurve stop voltage outside of compliance range"
            )

    # measurement interval
    interval = abs(p["dV"]) / p["sweep_rate"]

    # apply compliance settings
    smu.set_voltage_limit(SMUChannel.CELL, p["Vmax"])
    smu.set_current_limit(SMUChannel.CELL, p["Imax"])

    status("Running J-V Scan...")

    data_v: list[float] = []
    data_i: list[float] = []
    data_i_ref: list[float] = []
    data_j: list[float] = []

    parallel_reference = smu.use_reference_diode and smu.reference_diode_parallel
    if parallel_reference:
        smu.setup_reference_diode()

    smu.set_sense_mode(SMUChannel.CELL, _nwire_value(p["Nwire"]))

    if p["start_V"] == "Voc":
        smu.setup_current_output(SMUChannel.CELL, p["Vmax"])
        smu.set_current(SMUChannel.CELL, p["Fwd_current_limit"])
        # need a minimum dwell time to measure the starting point
        if p["Dwell"] < 1.0:
            p["Dwell"] = 1.0
    else:
        smu.setup_voltage_output(SMUChannel.CELL, p["Imax"])
        smu.set_voltage(SMUChannel.CELL, p["start_V"])

    # start the scan
    smu.enable_output(SMUChannel.CELL)

    status(
        "Stabilizing at initial operating point for " + str(p["Dwell"]) + " seconds"
    )

    deadline = time.time() + p["Dwell"]
    while time.time() < deadline:
        if p["start_V"] == "Voc":
            smu.measure_voltage(SMUChannel.CELL)
        else:
            smu.measure_current(SMUChannel.CELL)
        if parallel_reference:
            # keeps the value visible on the instrument display (legacy)
            smu.measure_current(SMUChannel.REFERENCE)
        if cancelled():
            break

    # if the start voltage is 'Voc', measure the voltage at the current
    # limit and then switch to voltage mode
    if p["start_V"] == "Voc":
        p["start_V"] = smu.measure_voltage(SMUChannel.CELL)
        smu.set_voltage(SMUChannel.CELL, p["start_V"])
        smu.setup_voltage_output(SMUChannel.CELL, p["Imax"])

    # all scan parameters are now known: generate the voltage list
    num_points = int(abs((p["stop_V"] - p["start_V"]) / abs(p["dV"])) + 1)
    v_points = linspace(p["start_V"], p["stop_V"], num_points)

    status("Running J-V Scan...")

    meas_time = time.time()  # first measurement at time zero
    for v in v_points:
        smu.set_voltage(SMUChannel.CELL, v)

        while time.time() < meas_time:
            if cancelled():
                break
            if parallel_reference:
                smu.measure_both_currents()
            else:
                smu.measure_current(SMUChannel.CELL)

        if parallel_reference:
            i, i_ref = smu.measure_both_currents()
            data_i_ref.append(i_ref)
        else:
            i = smu.measure_current(SMUChannel.CELL)
            data_i_ref.append(0.0)

        data_i.append(i)
        data_j.append(i * 1000.0 / p["active_area"])
        data_v.append(v)

        emit_data({"v": list(data_v), "j": list(data_j)})

        meas_time = meas_time + interval

        # positive scan to the forward current limit: end at Voc
        if stop_at_voc and i > p["Fwd_current_limit"]:
            break

        if cancelled():
            break

    smu.turn_off()

    return (data_v, data_i, data_i_ref)


class IVCurveProtocol(MeasurementProtocol):
    """J-V scan (legacy ``system.measure_IVcurve``).

    ``metrics_function`` defaults to the analysis wrapper and is
    injectable for headless tests without pandas/bric installed.
    """

    def __init__(self, *args, metrics_function: Optional[MetricsFunction] = None, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._metrics_function = metrics_function or compute_jv_metrics

    def run(self, params: dict) -> IVResults:
        p = dict(params)
        start_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

        # check that start and stop voltages are within the compliance range
        if p["start_V"] != "Voc" and abs(p["start_V"]) > abs(p["Vmax"]):
            raise ValueError(
                "ERROR: measure_IVcurve start voltage outside of compliance range"
            )
        if p["stop_V"] != "Voc" and abs(p["stop_V"]) > abs(p["Vmax"]):
            raise ValueError(
                "ERROR: measure_IVcurve stop voltage outside of compliance range"
            )

        # check that the SMU can handle the requested measurement interval
        if abs(p["dV"]) / p["sweep_rate"] < self.smu.meas_period_min:
            p["dV"] = self.smu.meas_period_min * p["sweep_rate"] + 0.01
            self.warn(
                "WARNING: the SMU is unable to provide the requested measurement rate.\n"
                "The voltage step size has been adjusted to assure the requested "
                "sweep rate is respected."
            )

        result = IVResults(
            start_time=start_time,
            active_area=p["active_area"],
            cell_name=p["cell_name"],
            light_int=p["light_int"],
            start_V=p["start_V"],
            stop_V=p["stop_V"],
            dV=p["dV"],
            sweep_rate=p["sweep_rate"],
            Imax=p["Imax"],
            Nwire=p["Nwire"],
            Dwell=p["Dwell"],
        )

        self.status("Turning lamp on...")
        self.turn_lamp_on(p["light_int"])
        light_intensity: Optional[float] = None
        try:
            # measure light intensity on the reference diode if configured
            if self.smu.use_reference_diode:
                light_intensity = self.check_light_level(p["light_int"])
                if self.cancelled():
                    self.status("Run Aborted")
                    return result

            # check Voc polarity only when the light is on
            if self.check_voc_before_scan and p["light_int"] > 0:
                self.status("Checking Voc Polarity...")
                polarity_ok = self.check_voc_polarity(p)
                if self.cancelled():
                    self.status("Run Aborted")
                    return result
                if not polarity_ok:
                    self.status("ERROR: Wrong Voc Polarity...")
                    raise VocPolarityError(
                        "Error: Incorrect polarity detected for Voc.  This could "
                        "be due to wires plugged incorrectly or light source not "
                        "turning on.  Aborting Scan"
                    )

            self.status("Running J-V Scan...")
            v_smu, i_smu, i_ref = scan_iv_points(
                self.smu,
                p,
                status=self.status,
                cancelled=self.cancelled,
                emit_data=self.emit_data,
            )

            # average light level for the single-point correction (legacy)
            if self.smu.use_reference_diode:
                if self.smu.reference_diode_parallel and i_ref:
                    avg_ref_current = sum(i_ref) / len(i_ref)
                    avg_light_level = abs(
                        100.0 * avg_ref_current / self.smu.full_sun_reference_current
                    )
                else:  # measured once at the beginning
                    avg_light_level = light_intensity
                result.light_int_meas = avg_light_level
            else:
                avg_light_level = p["light_int"]

            result.voltage = v_smu
            result.current = i_smu
            result.current_reference = i_ref
            # actual endpoints (important for Voc scans and aborts)
            if v_smu:
                result.start_V = v_smu[0]
                result.stop_V = v_smu[-1]
            result.dV = p["dV"]
            result.Dwell = p["Dwell"]

            # don't analyze dark or aborted runs (legacy)
            if len(v_smu) > 1 and p["light_int"] > 0 and not self.cancelled():
                metrics = self._metrics_function(
                    v_smu, i_smu, p["active_area"], cell_name=p["cell_name"]
                )
                result.Voc = metrics.Voc
                result.Jsc = metrics.Jsc
                result.Vmpp = metrics.Vmpp
                result.Jmpp = metrics.Jmpp
                result.Pmpp = metrics.Pmpp
                result.PCE = pce(metrics.Pmpp, avg_light_level)
                result.FF = metrics.FF

            if self.cancelled():
                self.status("Run Aborted")
            else:
                self.status("Run finished")
            return result
        finally:
            # always leave the hardware safe, even on errors (stricter
            # than legacy, per docs/HARDWARE.md)
            self.smu.turn_off()
            self.status("Turning lamp off...")
            self.turn_lamp_off()
