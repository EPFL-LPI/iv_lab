"""Measurement data file writing (legacy format).

Migrated from ``system.writeDataFile`` in ``IVLab/IVlab.py``. All file
writing goes through this module (no scattered ``open()`` calls).

Preserved legacy behavior:

- file name ``<cell_name>_<scanType>_<start_time>.csv`` under
  ``<basePath>/<username>/data/``,
- the ``nHeader,N`` first line, where N counts the header lines
  *including* the ``nHeader`` line itself,
- the per-scan-type header blocks and column captions, including the
  reference-diode lines and light-intensity column only when a
  reference diode is in use,
- row formats and rounding: voltages/currents rounded to 12 digits,
  times to 6, the MPP power column ``abs(i*v*1000/area)``, and the
  light intensity column ``-100 * i_ref / fullSunReferenceCurrent``,
- saving a J-V scan also generates the PDF report,
- the scrambled duplicate copy under ``sdPath`` (scrambled file name
  *and* scrambled content), written best-effort and skipped entirely
  when ``sdPath`` is empty.

The writer receives a :class:`SystemContext` instead of reaching into
settings/hardware objects; ``core/system.py`` assembles it (calibration
values are runtime state on the SMU).
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from iv_lab.data.results import (
    ConstantCurrentResults,
    ConstantVoltageResults,
    IVResults,
    MeasurementResult,
    MPPResults,
)
from iv_lab.services.auth import scramble_string


@dataclass
class SystemContext:
    """Static system information written into data files and reports."""

    base_path: str
    #: Empty string disables the scrambled duplicate copy (legacy).
    sd_path: str
    system_name: str
    smu_brand: str
    smu_model: str
    lamp_display_name: str
    use_reference_diode: bool
    #: Reference diode current at 100% sun in A (runtime SMU state).
    full_sun_reference_current: float
    #: Formatted date of the last calibration (runtime SMU state).
    calibration_datetime: str
    #: Path of the report logo (legacy EPFL_Logo.png); optional.
    logo_path: str | None = None


class FileWriter:
    """Writes measurement results in the legacy file format."""

    def __init__(
        self,
        context: SystemContext,
        *,
        status_callback: Callable[[str], None] | None = None,
        generate_pdf: bool = True,
    ) -> None:
        self.context = context
        self._status_callback = status_callback
        #: J-V saves generate the PDF report (legacy); disable for tests.
        self.generate_pdf = generate_pdf

    def _status(self, message: str) -> None:
        if self._status_callback is not None:
            self._status_callback(message)

    # --- legacy header ---

    def _header_lines(self, result: MeasurementResult) -> list[str]:
        ctx = self.context
        lines = []
        lines.append("Measurement System," + ctx.system_name)
        lines.append("Scan Start Time," + str(result.start_time))
        lines.append("Sourcemeter Brand," + ctx.smu_brand)
        lines.append("Sourcemeter Model," + ctx.smu_model)
        lines.append("Sourcemeter Sense Mode," + str(result.Nwire))
        lines.append("Light Source," + ctx.lamp_display_name)
        lines.append(
            "Requested Light Intensity," + str(result.light_int) + ",% sun"
        )
        if ctx.use_reference_diode:
            # legacy crashed when light_int_meas was never measured; the
            # line is omitted instead
            if result.light_int_meas is not None:
                lines.append(
                    "Measured Light Intensity,"
                    + str(result.light_int_meas)
                    + ",% sun"
                )
            lines.append(
                "Reference Diode 1sun Current,"
                + str(ctx.full_sun_reference_current * 1000.0)
                + ",mA"
            )
            lines.append(
                "Reference Diode calibration date," + ctx.calibration_datetime
            )
        lines.append("Cell Active Area," + str(result.active_area) + ",cm^2")

        if result.scan_type == "JV":
            lines.append("Start Voltage," + str(result.start_V) + ",V")
            lines.append("Stop Voltage," + str(result.stop_V) + ",V")
            lines.append("Voltage Step," + str(result.dV) + ",V")
            lines.append("Sweep Rate," + str(result.sweep_rate) + ",V/sec")
            lines.append("J-V Results")
            if result.Jsc is not None:
                lines.append("Jsc," + str(result.Jsc) + ",mA/cm^2")
            if result.Voc is not None:
                lines.append("Voc," + str(result.Voc) + ",V")
            if result.FF is not None:
                lines.append("Fill Factor," + str(result.FF))
            if result.PCE is not None:
                lines.append("PCE," + str(result.PCE) + ",%")
            if result.Jmpp is not None:
                lines.append("Jmpp," + str(result.Jmpp) + ",mA/cm^2")
            if result.Vmpp is not None:
                lines.append("Vmpp," + str(result.Vmpp) + ",V")
            if result.Pmpp is not None:
                lines.append("Pmpp," + str(result.Pmpp) + ",mW/cm^2")
            if ctx.use_reference_diode:
                lines.append("Voltage(V),Current(A),light intensity (% sun)")
            else:
                lines.append("Voltage(V),Current(A)")
        elif result.scan_type == "CV":
            lines.append("Set Voltage," + str(result.set_voltage) + ",V")
            lines.append("Measurement Interval," + str(result.interval) + ",sec")
            lines.append("Measurement Duration," + str(result.duration) + ",sec")
            lines.append("Constant Voltage Results")
            if ctx.use_reference_diode:
                lines.append("Time(s),Voltage(V),Current(A),light intensity (% sun)")
            else:
                lines.append("Time(s),Voltage(V),Current(A)")
        elif result.scan_type == "CC":
            lines.append("Set Current," + str(result.set_current) + ",A")
            lines.append("Measurement Interval," + str(result.interval) + ",sec")
            lines.append("Measurement Duration," + str(result.duration) + ",sec")
            lines.append("Constant Current Results")
            lines.append("Time(s),Voltage(V),Current(A)")
        elif result.scan_type == "MPP":
            lines.append("Start Voltage," + str(result.start_voltage) + ",V")
            lines.append("Measurement Interval," + str(result.interval) + ",sec")
            lines.append("Measurement Duration," + str(result.duration) + ",sec")
            lines.append("Maximum Power Point Results")
            if ctx.use_reference_diode:
                lines.append(
                    "Time(s),Voltage(V),Current (A),Power(mW/cm^2),"
                    "light intensity (% sun)"
                )
            else:
                lines.append("Time(s),Voltage(V),Current(A),Power(mW/cm^2)")
        else:
            raise ValueError(
                "scanType entry in data dictionary must be JV, CV, CC, or MPP"
            )

        return lines

    # --- legacy data rows ---

    def _light_intensity(self, i_ref: float) -> float:
        return -100.0 * i_ref / self.context.full_sun_reference_current

    def _reference_column(self, result: MeasurementResult) -> Sequence[float]:
        i_ref = getattr(result, "current_reference", None)
        if i_ref is None:
            return [0.0] * len(result.current)
        return i_ref

    def _data_lines(self, result: MeasurementResult) -> list[str]:
        ctx = self.context
        lines = []

        if result.scan_type == "JV":
            for v, i, i_ref in zip(
                result.voltage,
                result.current,
                self._reference_column(result),
                strict=False,
            ):
                line = str(round(v, 12)) + "," + str(round(i, 12))
                if ctx.use_reference_diode:
                    line += "," + str(round(self._light_intensity(i_ref), 12))
                lines.append(line)
        elif result.scan_type == "CV":
            for t, v, i_ref, i in zip(
                result.time,
                result.voltage,
                self._reference_column(result),
                result.current,
                strict=False,
            ):
                line = (
                    str(round(t, 6))
                    + ","
                    + str(round(v, 12))
                    + ","
                    + str(round(i, 12))
                )
                if ctx.use_reference_diode:
                    line += "," + str(round(self._light_intensity(i_ref), 12))
                lines.append(line)
        elif result.scan_type == "CC":
            for t, v, i in zip(
                result.time, result.voltage, result.current, strict=False
            ):
                lines.append(
                    str(round(t, 6))
                    + ","
                    + str(round(v, 12))
                    + ","
                    + str(round(i, 12))
                )
        elif result.scan_type == "MPP":
            for t, v, i_ref, i in zip(
                result.time,
                result.voltage,
                self._reference_column(result),
                result.current,
                strict=False,
            ):
                w = abs(i * v * 1000.0 / result.active_area)
                line = (
                    str(round(t, 6))
                    + ","
                    + str(round(v, 12))
                    + ","
                    + str(round(i, 12))
                    + ","
                    + str(round(w, 12))
                )
                if ctx.use_reference_diode:
                    line += "," + str(round(self._light_intensity(i_ref), 12))
                lines.append(line)

        return lines

    # --- saving (legacy writeDataFile) ---

    def save(
        self,
        result: IVResults | ConstantVoltageResults | ConstantCurrentResults | MPPResults,
        username: str,
    ) -> tuple[Path, Path | None]:
        """Write the data file (and the J-V PDF report); returns
        ``(csv_path, pdf_path_or_None)``."""
        ctx = self.context

        filename = (
            str(result.cell_name)
            + "_"
            + result.scan_type
            + "_"
            + str(result.start_time)
            + ".csv"
        )
        pdf_filename = (
            str(result.cell_name)
            + "_"
            + result.scan_type
            + "_"
            + str(result.start_time)
            + ".pdf"
        )
        data_file_path = Path(ctx.base_path) / username / "data" / filename
        pdf_file_path = Path(ctx.base_path) / username / "data" / pdf_filename

        # build the full content (header count includes the nHeader line)
        header_lines = self._header_lines(result)
        n_lines = len(header_lines) + 1
        file_string = "nHeader," + str(n_lines) + "\n"
        for line in header_lines:
            file_string += line + "\n"
        for line in self._data_lines(result):
            file_string += line + "\n"

        data_file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(data_file_path, "w", encoding="utf-8") as f:
            f.write(file_string)

        pdf_path: Path | None = None
        if result.scan_type == "JV" and self.generate_pdf:
            from iv_lab.data.pdf_report import generate_jv_results_pdf

            generate_jv_results_pdf(
                result, username, ctx, filename, pdf_file_path
            )
            pdf_path = pdf_file_path

        self._status("Saved data to: " + str(data_file_path))

        # write the scrambled duplicate copy (legacy 'secret file'),
        # best-effort like legacy
        if ctx.sd_path != "":
            try:
                scrambled_filename = scramble_string(
                    username + "_" + Path(filename).stem
                )
                sd_file_path = Path(ctx.sd_path) / scrambled_filename
                sd_file_path.parent.mkdir(parents=True, exist_ok=True)
                with open(sd_file_path, "w", encoding="utf-8") as s:
                    s.write(scramble_string(file_string))
            except Exception:
                pass

        return (data_file_path, pdf_path)
