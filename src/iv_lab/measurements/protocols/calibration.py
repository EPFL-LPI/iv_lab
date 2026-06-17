"""Reference diode calibration protocol.

Migrated from the legacy ``system.run_reference_diode_calibration`` and
``SMU.measure_reference_calibration`` in ``IVLab/IVlab.py``.

A certified control diode (known current ``reference_current`` at
100 % sun) is measured together with the installed reference photodiode;
the new full-sun reference current is derived as::

    calFactor = (reference_current / averageMeasCurrent) * (100 / light_int)
    fullSunReferenceCurrent = abs(averageRefCurrent * calFactor)

Three measurement modes, as in legacy:

- parallel (26xx): both channels sampled together (``CHAN_BOTH``),
- serial: cell channel first, then the reference diode channel,
- IV_Old: the Arduino stage moves the reference diode and the control
  diode into the beam for two sequential constant-voltage runs.

Note: the legacy IV_Old branch unpacked the measured-current array into
an unused variable and averaged the all-zero ``i_ref`` column instead
(an apparent variable mix-up that cannot have produced a valid
calibration); this implementation uses the measured currents of the two
runs, which is the evident intent.

The protocol returns the derived ``reference_current`` in the result;
persisting it to ``system_settings.json`` (with a new calibration date)
remains a separate, user-confirmed step as in legacy.

``params`` (legacy keys): ``light_int``, ``reference_current``,
``interval``, ``duration``, ``Imax``, ``Vmax``, ``Dwell``, ``Nwire``;
``set_voltage`` is forced to 0 (legacy).
"""

from __future__ import annotations

import datetime
import time

from iv_lab.data import CalibrationResults
from iv_lab.hardware.smu.base import SMUChannel

from .base import MeasurementProtocol
from .constant_voltage import measure_current_vs_time


class CalibrationProtocol(MeasurementProtocol):
    """Reference diode calibration (legacy
    ``system.run_reference_diode_calibration``)."""

    # --- direct measurement (legacy SMU.measure_reference_calibration) ---

    def _measure_reference_calibration(
        self, p: dict
    ) -> tuple[list[float], list[float], list[float]]:
        smu = self.smu

        t_meas: list[float] = []
        i_meas: list[float] = []
        t_ref: list[float] = []
        i_ref: list[float] = []

        # apply compliance settings
        smu.set_voltage_limit(SMUChannel.CELL, p["Vmax"])
        smu.set_current_limit(SMUChannel.CELL, p["Imax"])

        channel_list = ["BOTH"] if smu.reference_diode_parallel else ["A", "B"]

        for channel in channel_list:
            if abs(p["set_voltage"]) > abs(p["Vmax"]):
                raise ValueError(
                    "ERROR: measure_I_time_dependent set voltage outside of "
                    "compliance range"
                )

            if channel in ("A", "BOTH"):
                smu.setup_voltage_output(SMUChannel.CELL, p["Imax"])
                smu.set_voltage(SMUChannel.CELL, 0.0)
                smu.enable_output(SMUChannel.CELL)
            if channel in ("B", "BOTH"):
                smu.setup_reference_diode()
                smu.enable_output(SMUChannel.REFERENCE)

            def measure(channel: str = channel) -> tuple:
                if channel == "A":
                    return (smu.measure_current(SMUChannel.CELL), None)
                if channel == "B":
                    return (None, smu.measure_current(SMUChannel.REFERENCE))
                return smu.measure_both_currents()

            self.status(
                "Stabilizing at initial operating point for "
                + str(p["Dwell"])
                + " seconds"
            )
            deadline = time.time() + p["Dwell"]
            while time.time() < deadline:
                measure()
                if self.cancelled():
                    break

            self.status("Running Constant Voltage Measurement...")

            start_time = time.time()
            meas_time = start_time  # first measurement at time zero
            while (time.time() - start_time) < p["duration"]:
                now = time.time()
                if now >= meas_time:
                    i, i_r = measure()
                    if channel in ("A", "BOTH"):
                        i_meas.append(i)
                        t_meas.append(now - start_time)
                    if channel in ("B", "BOTH"):
                        i_ref.append(i_r)
                        t_ref.append(now - start_time)

                    self.emit_data(
                        {
                            "t_meas": list(t_meas),
                            "i_meas_ma": [v * 1000.0 for v in i_meas],
                            "t_ref": list(t_ref),
                            "i_ref_ma": [v * 1000.0 for v in i_ref],
                        }
                    )

                    meas_time = meas_time + p["interval"]
                else:
                    # dummy measurement to keep the display active (legacy)
                    measure()

                if self.cancelled():
                    break

            smu.turn_off()

        # the serial case can produce different point counts; trim like legacy
        if len(t_meas) == len(t_ref):
            t = t_meas
        elif len(t_meas) > len(t_ref):
            t = t_ref
            i_meas = i_meas[0 : len(t) - 1]
        else:
            t = t_meas
            i_ref = i_ref[0 : len(t) - 1]

        return (t, i_meas, i_ref)

    # --- IV_Old: two stage-selected constant-voltage runs ---

    def _measure_with_stage(
        self, p: dict
    ) -> tuple[list[float], list[float], list[float]]:
        self.status("Moving Reference Diode Into Measurement Position...")
        self.arduino.select_reference_cell()

        _t_ref, i_ref, _zeros = measure_current_vs_time(
            self.smu,
            p,
            status=self.status,
            cancelled=self.cancelled,
            emit_data=self.emit_data,
        )

        t: list[float] = []
        i_meas: list[float] = []
        if not self.cancelled():
            self.status("Moving Control Diode Into Measurement Position...")
            self.arduino.select_test_cell()

            t, i_meas, _zeros = measure_current_vs_time(
                self.smu,
                p,
                status=self.status,
                cancelled=self.cancelled,
                emit_data=self.emit_data,
            )

        return (t, i_meas, i_ref)

    # --- protocol interface ---

    def run(self, params: dict) -> CalibrationResults:
        p = dict(params)
        p["set_voltage"] = 0.0  # legacy
        start_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

        result = CalibrationResults(
            start_time=start_time,
            light_int=p["light_int"],
            interval=p["interval"],
            duration=p["duration"],
        )

        self.status("Turning lamp on...")
        self.turn_lamp_on(p["light_int"])
        try:
            if self._is_iv_old and self.arduino is not None:
                t, i_smu, i_ref = self._measure_with_stage(p)
            else:
                self.status("Running Reference Diode Calibration...")
                t, i_smu, i_ref = self._measure_reference_calibration(p)

            result.time = t
            result.current = i_smu
            result.current_reference = i_ref

            if self.cancelled():
                self.status("Calibration Aborted")
                return result

            # process data and derive the new reference diode calibration
            average_meas_current = sum(i_smu) / len(i_smu)
            average_ref_current = sum(i_ref) / len(i_ref)
            cal_factor = (p["reference_current"] / average_meas_current) * (
                100.0 / p["light_int"]
            )
            result.reference_current = abs(average_ref_current * cal_factor)
            result.metadata["calibration_factor"] = cal_factor
            result.metadata["average_measured_current"] = average_meas_current
            result.metadata["average_reference_current"] = average_ref_current

            self.status("Calibration finished")
            return result
        finally:
            self.smu.turn_off()
            self.status("Turning lamp off...")
            self.turn_lamp_off()
