"""Photovoltaic metrics from a J-V scan.

Thin wrapper around the internal ``jv_analysis`` module, isolating the
analysis logic behind one interface (step 8 of docs/MIGRATION.md). Voc,
Jsc, FF, and PCE are not reimplemented here.

``numpy`` and ``jv_analysis`` (which imports ``pandas`` and ``scipy``) are
imported inside ``compute_jv_metrics`` so the package imports without them,
consistent with the deferred-import policy for heavy scientific dependencies.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass


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

    ``voltage`` in V, ``current`` in A, ``active_area`` in cm².  The
    legacy result units are used: Jsc/Jmpp in mA/cm², Pmpp in mW/cm²
    as an absolute value.
    """
    import numpy as np
    import pandas as pd

    from . import jv_analysis

    j_density = np.array(current) / active_area  # A/cm²
    df = pd.DataFrame({cell_name: j_density}, index=list(voltage))

    result = jv_analysis.get_metrics(df, generator=False, fit_window=4)

    return JVMetrics(
        Voc=float(result["voc"].iloc[0]),
        Jsc=float(result["jsc"].iloc[0]) * 1000.0,
        Vmpp=float(result["vmpp"].iloc[0]),
        Jmpp=float(result["jmpp"].iloc[0]) * 1000.0,
        Pmpp=abs(float(result["pmpp"].iloc[0]) * 1000.0),
        FF=float(result["ff"].iloc[0]),
    )


def pce(pmpp: float, avg_light_level: float) -> float:
    """Power conversion efficiency in percent.

    Legacy formula: ``100 * |Pmpp| / avgLightLevel`` with ``Pmpp`` in
    mW/cm² and the average light level in percent of one sun
    (100 % sun = 100 mW/cm²).
    """
    return 100.0 * abs(pmpp) / avg_light_level
