"""J-V results PDF report (legacy layout).

Migrated from ``system.generate_JV_Results_PDF`` in ``IVLab/IVlab.py``.
The page layout, plot placement, parameter/result text columns (with
their legacy number formats), the data-file-name wrapping quirk, and
the footer are preserved.

Differences from legacy, both deliberate:

- matplotlib is used through the object-oriented ``Figure`` API with an
  Agg canvas instead of the ``pyplot`` global figure (``plt.gcf()``),
  so report generation is headless and leak-free (the legacy global
  figure caused the memory leak fixed in commit 7906353),
- the EPFL logo path is taken from :class:`SystemContext.logo_path` and
  the logo is skipped if the file is absent (legacy hard-crashed on a
  missing ``EPFL_Logo.png`` in the working directory).

matplotlib is imported inside the function so the package imports
without it.
"""

from __future__ import annotations

import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from iv_lab.data.results import IVResults

if TYPE_CHECKING:
    from iv_lab.data.file_writer import SystemContext

#: Legacy page size in inches (A4 landscape).
A4_SIZE_X = 11.75
A4_SIZE_Y = 8.25


def wrap_data_file_name(data_file_name: str) -> list[tuple[str, str, str]]:
    """Legacy wrapping of the data file name into report text rows."""
    rows: list[tuple[str, str, str]] = []
    if len(data_file_name) < 35:
        rows.append(("Data File Name", data_file_name, ""))
    else:  # wrap text every 35 characters (legacy: 30-char chunks)
        rows.append(("Data File Name", data_file_name[0:30], ""))
        remainder = data_file_name[30:]
        while len(remainder) > 35:
            rows.append(("", remainder[0:30], ""))
            remainder = remainder[30:]
        rows.append(("", remainder, ""))
    return rows


def generate_jv_results_pdf(
    result: IVResults,
    username: str,
    context: SystemContext,
    data_file_name: str,
    pdf_file_path: str | Path,
) -> Path:
    """Render the legacy J-V report PDF; returns the written path."""
    # deferred import: matplotlib is optional at package import time
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure
    from matplotlib.image import imread

    date_time_string = datetime.datetime.now().strftime("%c")

    fig = Figure(figsize=(A4_SIZE_X, A4_SIZE_Y))
    FigureCanvasAgg(fig)

    data_j = [i * 1000.0 / result.active_area for i in result.current]

    # J-V plot (legacy placement, inverted current axis)
    ax1 = fig.add_axes([0.5, 0.4, 0.4, 0.4])  # x, y, width, height
    ax1.invert_yaxis()
    ax1.set_ylabel("Current density [mA/$cm^2$]")
    ax1.set_xlabel("Voltage [V]")
    ax1.grid(visible=True)
    ax1.axhline(color="k")  # solid black line across the x-axis at y=0
    ax1.plot(result.voltage, data_j, color="red")

    # report header: EPFL logo and cell name
    logo_path = context.logo_path
    if logo_path and Path(logo_path).exists():
        ax2 = fig.add_axes([0.04, 0.80, 0.15, 0.15])
        ax2.axis("off")
        ax2.imshow(imread(logo_path))

    fig.text(
        0.20,
        0.85,
        "Cell Name: " + str(result.cell_name),
        weight="bold",
        fontsize=12,
        ha="left",
    )

    # run parameter text columns (legacy coordinates and spacing)
    rp_x1 = 0.05
    rp_x2 = 0.19
    rp_y = 0.8
    rp_space = 0.0225
    params_text = [
        ("Measurement Date", date_time_string, ""),
        ("Cell Active Area", str(result.active_area), " $cm^2$"),
        ("Light Source", context.lamp_display_name, ""),
    ]
    if context.use_reference_diode:
        params_text.append(
            (
                "Reference Calibration",
                f"{context.full_sun_reference_current * 1000.0:6.4f}",
                " mA",
            )
        )
        params_text.append(("Calibration Date", context.calibration_datetime, ""))

    params_text.extend(wrap_data_file_name(data_file_name))

    params_text.append(("Sense Mode", str(result.Nwire), ""))
    params_text.append(("Current Compliance", str(result.Imax * 1000.0), " mA"))
    params_text.append(("Sweep rate", f"{result.sweep_rate * 1000:.1f}", " mV/s"))
    params_text.append(("Voltage step", str(result.dV), " V"))
    params_text.append(("Meas. Delay", str(result.Dwell), " s"))
    for label, value, units in params_text:
        fig.text(rp_x1, rp_y, label, fontsize=10, ha="left")
        fig.text(rp_x2, rp_y, ": " + value + units, fontsize=10, ha="left")
        rp_y -= rp_space

    # results text column (legacy coordinates, formats, and order)
    rt_x1 = 0.05
    rt_x2 = 0.19
    rt_y = 0.45
    rt_space = 0.0225
    results_text = [
        ("Nominal Light Intensity", str(result.light_int), "% sun")
    ]
    if result.light_int_meas is not None:
        results_text.append(
            ("Measured Intensity", f"{result.light_int_meas:6.2f}", "% sun")
        )
    if result.Jsc is not None:
        results_text.append(("Jsc", f"{result.Jsc:5.3f}", " mA/$cm^2$"))
    if result.Voc is not None:
        results_text.append(("Voc", f"{result.Voc:6.4f}", "V"))
    if result.FF is not None:
        results_text.append(("FF", f"{result.FF:6.4f}", ""))
    if result.PCE is not None:
        results_text.append(("PCE", f"{result.PCE:5.2f}", "%"))
    if result.Jmpp is not None:
        results_text.append(("Jmpp", f"{result.Jmpp:5.3f}", " mA/$cm^2$"))
    if result.Vmpp is not None:
        results_text.append(("Vmpp", f"{result.Vmpp:6.4f}", "V"))
    if result.Pmpp is not None:
        results_text.append(("Pmpp", f"{result.Pmpp:7.3f}", " mW/$cm^2$"))

    for label, value, units in results_text:
        fig.text(rt_x1, rt_y, label, fontsize=10, ha="left")
        fig.text(rt_x2, rt_y, ": " + value + units, fontsize=10, ha="left")
        rt_y -= rt_space

    # footer: measured by and date
    fig.text(
        0.05,
        0.05,
        "Measured by: " + username + " on " + context.system_name,
        fontsize=10,
        ha="left",
    )
    fig.text(0.75, 0.05, "Date: " + date_time_string, fontsize=10, ha="left")

    pdf_file_path = Path(pdf_file_path)
    fig.savefig(pdf_file_path)
    return pdf_file_path
