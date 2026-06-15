"""J-V analysis: Voc, Jsc, MPP, fill factor.

Adapted from the bric-analysis-libraries jv_analysis and standard_functions
modules (EPFL BRIC). Only the functions required by compute_jv_metrics are
included; everything else has been dropped.
"""
from __future__ import annotations

import numpy as np
from numpy.polynomial import Polynomial
import pandas as pd
from scipy.stats import linregress


# ---------------------------------------------------------------------------
# internal helper (adapted from standard_functions.df_find_index_of_value)
# ---------------------------------------------------------------------------

def _find_index_of_value(
    df: pd.DataFrame | pd.Series,
    value: float,
    fit_window: int = 20,
    polydeg: int = 1,
) -> pd.DataFrame:
    """Return the index value where each series crosses *value*.

    Uses linear polynomial fitting near the crossing point when no exact
    match exists. Returns a DataFrame with columns ``'index'`` and ``'fit'``.
    """
    if isinstance(df, pd.Series):
        df = df.to_frame()

    df = df.sort_index()
    result = pd.DataFrame(index=df.columns, columns=("index", "fit"))
    pos = df[df > value]
    neg = df[df < value]

    for name, data in df.items():
        exact = data.index[data == value]
        if exact.shape[0]:
            result.loc[name] = [exact[0], None]
            continue

        dpos = pos[name].dropna()
        dneg = neg[name].dropna()

        if dpos.shape[0] and dneg.shape[0]:
            left, right = (
                (dpos, dneg)
                if dpos.index.values.mean() < dneg.index.values.mean()
                else (dneg, dpos)
            )
            half = int(fit_window / 2)
            window = pd.concat([left.iloc[-half:], right.iloc[:half]])
        else:
            side = dneg if dneg.shape[0] else dpos
            lwin = side.iloc[:fit_window]
            rwin = side.iloc[-fit_window:]
            window = lwin if abs(lwin.mean() - value) < abs(rwin.mean() - value) else rwin

        if window.shape[0] < 3:
            result.loc[name] = [np.nan, None]
            continue

        window = window.squeeze()
        try:
            fit = Polynomial.fit(window.index, window.values - value, deg=polydeg)
        except Exception:
            result.loc[name] = [np.nan, None]
            continue

        roots = fit.roots()
        if roots.shape[0] == 0:
            result.loc[name] = [np.nan, None]
            continue

        dists = [np.abs(window.index - r).min() for r in roots]
        result.loc[name] = [roots[np.argmin(dists)], fit]

    return result


# ---------------------------------------------------------------------------
# public analysis functions
# ---------------------------------------------------------------------------

def get_power(df: pd.DataFrame) -> pd.DataFrame:
    """Element-wise power P = J * V (V is the DataFrame index)."""
    return df.mul(df.index, axis=0)


def get_mpp(df: pd.DataFrame, generator: bool = False) -> pd.DataFrame:
    """Maximum power point: returns DataFrame with columns pmpp, vmpp, jmpp."""
    pdf = get_power(df)
    if generator:
        pmpp = pdf.max()
        vmpp = pdf.idxmax()
    else:
        pmpp = pdf.min()
        vmpp = pdf.idxmin()
    jmpp = pmpp / vmpp
    return pd.concat([pmpp, vmpp, jmpp], keys=["pmpp", "vmpp", "jmpp"], axis=1)


def get_jsc(df: pd.DataFrame, fit_window: int = 20) -> pd.Series:
    """Short-circuit current density via linear regression near V=0."""
    if isinstance(df, pd.Series):
        df = df.to_frame()

    df = df.sort_index()
    jsc = pd.Series(index=df.columns, dtype=np.float64)

    for name, data in df.items():
        data = data.dropna()
        if 0 in data.index:
            jsc[name] = data[0]
            continue

        dpos = data[data.index > 0].dropna()
        dneg = data[data.index < 0].dropna()

        if dpos.shape[0] and dneg.shape[0]:
            half = int(fit_window / 2)
            window = pd.concat([dneg.iloc[-half:], dpos.iloc[:half]])
        else:
            window = dpos.iloc[:fit_window] if dpos.shape[0] else dneg.iloc[-fit_window:]

        fit = linregress(window.index, window.values)
        jsc[name] = fit.intercept

    return jsc.rename("jsc")


def get_voc(df: pd.DataFrame, fit_window: int = 20) -> pd.Series:
    """Open-circuit voltage: index value where current density crosses zero."""
    roots = _find_index_of_value(df, 0, fit_window=fit_window, polydeg=1)
    return roots["index"].astype(np.float64).rename("voc")


def get_metrics(
    df: pd.DataFrame,
    generator: bool = False,
    fit_window: int = 20,
) -> pd.DataFrame:
    """Compute Vmpp/Jmpp/Pmpp, Voc, Jsc, and FF for each column in *df*.

    *df* must be indexed by voltage (V) with current density (A/cm²) as
    column values.  Returns a DataFrame with one row per cell.
    """
    parts = [
        get_mpp(df, generator),
        get_voc(df, fit_window=fit_window),
        get_jsc(df, fit_window=fit_window),
    ]
    metrics = pd.concat(parts, axis=1)
    metrics = metrics.assign(ff=lambda x: x.pmpp / (x.voc * x.jsc))
    return metrics
