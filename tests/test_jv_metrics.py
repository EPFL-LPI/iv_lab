"""Tests for the JV metrics analysis wrapper.

``scipy``, ``numpy``, and ``pandas`` are deferred — only imported when
``compute_jv_metrics`` is called, not at module load.
"""

import os
import subprocess
import sys

import numpy as np
import pytest

from iv_lab.analysis import JVMetrics, compute_jv_metrics, pce


def _ideal_diode_jv(active_area: float = 0.16, n: int = 500):
    """Synthetic ideal-diode JV curve with predictable metrics.

    Returns (voltage_list, current_A_list).
    Voc ≈ 0.497 V, Jsc = -0.02 A/cm².
    """
    v = np.linspace(0.0, 0.55, n)
    jsc = -0.02   # A/cm²
    j0 = 1e-10
    vt = 0.026
    j = j0 * (np.exp(v / vt) - 1) + jsc  # A/cm²
    current = j * active_area             # A
    return list(v), list(current)


def test_import_does_not_eagerly_import_scipy() -> None:
    """``import iv_lab.analysis`` must not pull in scipy."""
    src = str((pytest.importorskip.__module__ and None) or None)  # just need a path expr
    import pathlib
    src = str(pathlib.Path(__file__).resolve().parent.parent / "src")

    code = (
        "import sys; import iv_lab.analysis; "
        "assert 'scipy' not in sys.modules, 'scipy imported at module load'; "
        "print('ok')"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": src},
    )
    assert result.stdout.strip() == "ok", result.stderr


def test_compute_jv_metrics_returns_jvmetrics() -> None:
    voltage, current = _ideal_diode_jv()
    metrics = compute_jv_metrics(voltage, current, 0.16)
    assert isinstance(metrics, JVMetrics)


def test_compute_jv_metrics_unit_conversions() -> None:
    """Jsc and Jmpp are in mA/cm², Pmpp is mW/cm² and always positive."""
    active_area = 0.16
    voltage, current = _ideal_diode_jv(active_area=active_area)

    metrics = compute_jv_metrics(voltage, current, active_area)

    # Jsc in mA/cm² (factor-of-1000 vs A/cm²), negative for a solar cell
    assert metrics.Jsc == pytest.approx(-20.0, rel=0.02)
    # Pmpp is the absolute value in mW/cm²
    assert metrics.Pmpp > 0
    # Vmpp is between 0 and Voc
    assert 0.0 < metrics.Vmpp < metrics.Voc
    # FF is a unitless ratio between 0 and 1
    assert 0.0 < metrics.FF < 1.0


def test_compute_jv_metrics_voc_and_jsc_signs() -> None:
    """Voc is positive, Jsc is negative (consumer convention)."""
    voltage, current = _ideal_diode_jv()
    metrics = compute_jv_metrics(voltage, current, 0.16)
    assert metrics.Voc > 0
    assert metrics.Jsc < 0


def test_pce_legacy_formula() -> None:
    # 100 * |Pmpp| / avgLightLevel
    assert pce(8.46, 100.0) == pytest.approx(8.46)
    assert pce(8.46, 50.0) == pytest.approx(16.92)
    assert pce(-8.46, 100.0) == pytest.approx(8.46)


def test_compute_jv_metrics_emulated_diode() -> None:
    """End-to-end check using the hardware emulator as the data source."""
    from iv_lab.config import SMUSettings
    from iv_lab.hardware.smu.base import SMUChannel
    from iv_lab.hardware.smu.drivers.emulated import EmulatedSMU

    smu = EmulatedSMU(
        SMUSettings(
            brand="Keithley", model="2602", visa_address="x",
            visa_library="x", emulate=True,
        )
    )
    smu.integration_delay = 0.0
    smu.full_sun_reference_current = 0.004
    smu.connect()
    smu.setup_voltage_output(SMUChannel.CELL, 0.01)

    voltage = [k * 0.01 for k in range(0, 61)]
    current = []
    for v in voltage:
        smu.set_voltage(SMUChannel.CELL, v)
        current.append(smu.measure_current(SMUChannel.CELL))

    metrics = compute_jv_metrics(voltage, current, 0.16, cell_name="emulated")

    assert metrics.Voc == pytest.approx(0.55, abs=0.01)
    assert metrics.Jsc == pytest.approx(-25.0, rel=0.02)
    assert 0.0 < metrics.Vmpp < 0.55
    assert 0.4 < metrics.FF < 0.9
    assert metrics.Pmpp > 0
