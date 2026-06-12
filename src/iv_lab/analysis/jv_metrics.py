"""Photovoltaic metrics from a J-V scan.

Thin wrapper around ``bric_analysis_libraries.jv.jv_analysis``, isolating
the external analysis package behind one internal interface (step 8 of
docs/MIGRATION.md). Voc, Jsc, FF, and PCE are *not* reimplemented.

The DataFrame plumbing and the unit conversions replicate the legacy
``system.measure_IVcurve`` in ``IVLab/IVlab.py`` exactly: current is
divided by the active area before analysis, and the returned values use
the legacy result units (V, mA/cm², mW/cm²; ``Pmpp`` as absolute value).

``numpy``, ``pandas``, and ``bric_analysis_libraries`` are imported
inside the computation so the package imports without them (consistent
with the deferred-import policy for optional dependencies).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass
class JVMetrics:
    """Photovoltaic metrics in the legacy result units."""

    Voc: float  #: open-circuit voltage in V
    Jsc: float  #: short-circuit current density in mA/cm²
    Vmpp: float  #: voltage at the maximum power point in V
    Jmpp: float  #: current density at the maximum power point in mA/cm²
    Pmpp: float  #: maximum power density in mW/cm² (absolute value)
    FF: float  #: fill factor


def compute_jv_metrics(
    voltage: Sequence[float],
    current: Sequence[float],
    active_area: float,
    cell_name: str = "cell",
) -> JVMetrics:
    """Compute J-V metrics from raw scan data.

    ``voltage`` in V, ``current`` in A, ``active_area`` in cm². The
    legacy DataFrame layout is reproduced: voltage as the index, current
    density (A/cm²) as a single column named after the cell, analyzed by
    ``bric_jv.get_metrics(df, generator=False, fit_window=4)``.
    """
    import numpy as np
    import pandas as pd

    import bric_analysis_libraries.jv.jv_analysis as bric_jv

    pairs = [(v, i / active_area) for v, i in zip(voltage, current)]

    jv_data = np.array(pairs)
    df = pd.DataFrame(jv_data)
    metrics = ["voltage", "current"]
    header = pd.MultiIndex.from_product(
        [[cell_name], metrics], names=["sample", "metrics"]
    )
    df.columns = header

    df.index = df.xs("voltage", level="metrics", axis=1).values.flatten()
    df.drop("voltage", level="metrics", axis=1, inplace=True)
    df.columns = df.columns.droplevel("metrics")

    jv_metrics = bric_jv.get_metrics(df, generator=False, fit_window=4)

    return JVMetrics(
        Voc=float(jv_metrics["voc"].iloc[0]),
        Jsc=float(jv_metrics["jsc"].iloc[0]) * 1000.0,
        Vmpp=float(jv_metrics["vmpp"].iloc[0]),
        Jmpp=float(jv_metrics["jmpp"].iloc[0]) * 1000.0,
        Pmpp=abs(float(jv_metrics["pmpp"].iloc[0]) * 1000.0),
        FF=float(jv_metrics["ff"].iloc[0]),
    )


def pce(pmpp: float, avg_light_level: float) -> float:
    """Power conversion efficiency in percent.

    Legacy formula: ``100 * |Pmpp| / avgLightLevel`` with ``Pmpp`` in
    mW/cm² and the average light level in percent of one sun
    (100 % sun = 100 mW/cm²).
    """
    return 100.0 * abs(pmpp) / avg_light_level
