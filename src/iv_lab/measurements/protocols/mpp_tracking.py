"""Maximum-power-point tracking protocol.

Migrated from the legacy ``system.measure_MPP_time_dependent`` and
``SMU.measure_MPP_time_dependent`` in ``IVLab/IVlab.py``.

The MPP algorithm is the legacy perturb-and-observe with adaptive
voltage stepping: the voltage moves by a step each sample; if the power
decreased, the direction flips. The step size adapts to the trend of
the last 8 steps — a strong trend (|sum| >= 3) doubles the step (up to
``voltage_step_max``), no trend halves it (down to
``voltage_step_min``).

``params`` (legacy keys): ``light_int``, ``start_voltage`` (may be
``'auto'`` to find the MPP from a reverse J-V scan first),
``interval``, ``duration``, ``Imax``, ``Vmax``, ``Dwell``, ``Nwire``,
``active_area``, ``cell_name``; the voltage step sizes come from the
system settings (legacy ``MPPVoltageStep*`` preferences) unless present
in ``params``.
"""

from __future__ import annotations

import datetime
import time

from iv_lab.data import MPPResults
from iv_lab.hardware.smu.base import SMUChannel

from .base import MeasurementProtocol, VocPolarityError, _nwire_value
from .iv_curve import scan_iv_points

#: Legacy IVsys preference defaults (system.__init__).
MPP_VOLTAGE_STEP_INITIAL = 0.002
MPP_VOLTAGE_STEP_MAX = 0.002
MPP_VOLTAGE_STEP_MIN = 0.001

#: Legacy parameters of the automatic Voc->0 scan used to find the
#: starting voltage (class attributes so tests can speed them up).
AUTO_SCAN_DV = 0.005
AUTO_SCAN_SWEEP_RATE = 0.02


class MPPTrackingProtocol(MeasurementProtocol):
    """MPP tracking (legacy ``system.measure_MPP_time_dependent``)."""

    def __init__(
        self,
        *args,
        voltage_step_initial: float = MPP_VOLTAGE_STEP_INITIAL,
        voltage_step_max: float = MPP_VOLTAGE_STEP_MAX,
        voltage_step_min: float = MPP_VOLTAGE_STEP_MIN,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        #: Legacy ``MPPVoltageStep*`` system preferences.
        self.voltage_step_initial = voltage_step_initial
        self.voltage_step_max = voltage_step_max
        self.voltage_step_min = voltage_step_min
        #: Parameters of the automatic start-voltage J-V scan (legacy
        #: hardcoded 5 mV at 0.02 V/s).
        self.auto_scan_dv = AUTO_SCAN_DV
        self.auto_scan_sweep_rate = AUTO_SCAN_SWEEP_RATE

    # --- automatic start voltage (legacy auto branch) ---

    def _find_start_voltage(self, p: dict) -> float:
        """Run a reverse J-V scan (Voc -> 0) and return the MPP voltage."""
        self.status("Running reverse JV to find MPP starting voltage...")
        time.sleep(1)  # legacy settle

        iv_params = {
            "light_int": p["light_int"],
            "start_V": "Voc",
            "Fwd_current_limit": p["Imax"] / 10.0,
            "stop_V": 0,
            "dV": self.auto_scan_dv,
            "sweep_rate": self.auto_scan_sweep_rate,
            "Dwell": p["Dwell"],
            "Nwire": p["Nwire"],
            "Imax": p["Imax"],
            "Vmax": p["Vmax"],
            "active_area": p["active_area"],
            "cell_name": p["cell_name"],
        }

        v_smu, i_smu, _i_ref = scan_iv_points(
            self.smu,
            iv_params,
            status=self.status,
            cancelled=self.cancelled,
            emit_data=self.emit_data,
        )

        # cell voltage is positive, current negative: maximize -v*i (legacy)
        p_smu = [v * i * -1 for v, i in zip(v_smu, i_smu, strict=False)]
        max_power = max(p_smu)
        return v_smu[p_smu.index(max_power)]

    # --- tracking loop (legacy SMU.measure_MPP_time_dependent) ---

    def _track(self, p: dict, v_mpp: float) -> tuple[list, list, list, list]:
        smu = self.smu
        parallel_reference = smu.use_reference_diode and smu.reference_diode_parallel

        data_t: list[float] = []
        data_w: list[float] = []
        data_i: list[float] = []
        data_i_ref: list[float] = []
        data_j: list[float] = []
        data_v: list[float] = []

        v_step = p.get("voltage_step", self.voltage_step_initial)
        v_step_max = p.get("voltage_step_max", self.voltage_step_max)
        v_step_min = p.get("voltage_step_min", self.voltage_step_min)
        step_direction = 1
        steps: list[int] = []
        last_power = 0.0

        # apply compliance settings (redundant if a JV scan just ran)
        smu.set_voltage_limit(SMUChannel.CELL, p["Vmax"])
        smu.set_current_limit(SMUChannel.CELL, p["Imax"])

        smu.set_sense_mode(SMUChannel.CELL, _nwire_value(p["Nwire"]))
        smu.setup_voltage_output(SMUChannel.CELL, p["Imax"])
        smu.set_voltage(SMUChannel.CELL, v_mpp)
        smu.enable_output(SMUChannel.CELL)

        self.status(
            "Stabilizing at initial operating point for " + str(p["Dwell"]) + " seconds"
        )

        deadline = time.time() + p["Dwell"]
        while time.time() < deadline:
            smu.measure_current(SMUChannel.CELL)
            if self.cancelled():
                break

        start_time = time.time()
        meas_time = start_time  # first measurement at time zero
        while (time.time() - start_time) < p["duration"]:
            now = time.time()
            if now >= meas_time:
                # measure power (legacy makes this redundant first read)
                i, v = smu.measure_iv_point(SMUChannel.CELL)
                if parallel_reference:
                    i, v, i_ref, _v_ref = smu.measure_both_iv_points()
                    data_i_ref.append(i_ref)
                else:
                    i, v = smu.measure_iv_point(SMUChannel.CELL)
                    data_i_ref.append(0)

                # cell voltage is positive, current is negative
                w = i * v * -1000.0 / p["active_area"]

                data_w.append(w)
                data_t.append(now - start_time)
                data_i.append(i)
                data_j.append(i * 1000.0 / p["active_area"])
                data_v.append(v)

                self.emit_data(
                    {
                        "t": list(data_t),
                        "w": list(data_w),
                        "v": list(data_v),
                        "j": list(data_j),
                    }
                )

                meas_time = meas_time + p["interval"]

                # perturb-and-observe with adaptive step size (legacy)
                if w < last_power:
                    # the power went down: we're going the wrong way
                    step_direction *= -1

                steps.append(step_direction)
                if len(steps) >= 8:
                    trend = sum(steps[len(steps) - 8 :])
                    if abs(trend) >= 3:
                        # noticeable trend: increase the step to get there faster
                        v_step *= 2
                        steps = []  # reset history when changing scale
                        if v_step > v_step_max:
                            v_step = v_step_max
                    elif abs(trend) == 0 and v_step > v_step_min:
                        v_step /= 2
                        steps = []
                        if v_step < v_step_min:
                            v_step = v_step_min

                v_mpp = v_mpp + v_step * step_direction

                # force the voltage to stay within the compliance range
                if v_mpp > abs(p["Vmax"]):
                    v_mpp = abs(p["Vmax"])
                if v_mpp < -1 * abs(p["Vmax"]):
                    v_mpp = -1 * abs(p["Vmax"])

                smu.set_voltage(SMUChannel.CELL, v_mpp)
                last_power = w

                self.status("Running MPP Measurement. v_step: " + str(v_step))
            else:
                # dummy measurement to keep the instrument display alive
                if parallel_reference:
                    smu.measure_both_iv_points()
                else:
                    smu.measure_current(SMUChannel.CELL)

            if self.cancelled():
                break

        smu.turn_off()

        return (data_t, data_v, data_i, data_i_ref)

    # --- protocol interface ---

    def run(self, params: dict) -> MPPResults:
        p = dict(params)
        start_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

        # check that a manual start voltage is within the compliance range
        if p["start_voltage"] != "auto" and abs(p["start_voltage"]) > abs(p["Vmax"]):
            raise ValueError(
                "ERROR: measure_MPP_time_dependent start voltage outside of "
                "compliance range"
            )

        # check that the SMU can handle the requested measurement interval
        if p["interval"] < self.smu.meas_period_min:
            p["interval"] = self.smu.meas_period_min
            self.warn(
                "WARNING: the SMU is unable to provide the requested measurement rate.\n"
                "The measurement interval has been set to the maximum allowed by the SMU."
            )

        result = MPPResults(
            start_time=start_time,
            active_area=p["active_area"],
            cell_name=p["cell_name"],
            light_int=p["light_int"],
            Nwire=p["Nwire"],
            start_voltage=p["start_voltage"],
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

            # Voc polarity check when the light is on (legacy)
            if self.check_voc_before_scan and p["light_int"] > 0:
                self.status("Checking Voc Polarity...")
                polarity_ok = self.check_voc_polarity(p)
                if self.cancelled():
                    self.status("Run Aborted")
                    return result
                if not polarity_ok:
                    self.status("ERROR: Wrong Voc Polarity.")
                    raise VocPolarityError(
                        "Error: Incorrect polarity detected for Voc.  This could "
                        "be due to wires plugged incorrectly.  Aborting Scan"
                    )

            # determine the starting voltage
            if p["start_voltage"] == "auto":
                v_mpp = self._find_start_voltage(p)
            else:
                v_mpp = p["start_voltage"]

            self.status("Running MPP Measurement...")
            t, v_smu, i_smu, i_ref = self._track(p, v_mpp)

            # average light level (legacy)
            if self.smu.use_reference_diode:
                if self.smu.reference_diode_parallel and i_ref:
                    avg_ref_current = sum(i_ref) / len(i_ref)
                    avg_light_level = abs(
                        100.0 * avg_ref_current / self.smu.full_sun_reference_current
                    )
                else:
                    avg_light_level = light_intensity
                result.light_int_meas = avg_light_level

            result.time = t
            result.voltage = v_smu
            result.current = i_smu
            result.current_reference = i_ref
            # actual starting voltage for auto runs (legacy)
            if p["start_voltage"] == "auto" and v_smu:
                result.start_voltage = v_smu[0]

            if self.cancelled():
                self.status("Run Aborted")
            else:
                self.status("Run finished")
            return result
        finally:
            self.smu.turn_off()
            self.status("Turning lamp off...")
            self.turn_lamp_off()
