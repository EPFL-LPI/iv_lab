"""Tests for the JV metrics analysis wrapper.

``bric_analysis_libraries`` is not required: a fake module is injected
into ``sys.modules``. ``numpy`` and ``pandas`` are real (runtime
dependencies of the package).
"""

import sys
import types

import pytest

from iv_lab.analysis import JVMetrics, compute_jv_metrics, pce


@pytest.fixture
def fake_bric(monkeypatch):
    """Inject a fake bric_analysis_libraries.jv.jv_analysis module."""
    import pandas as pd

    state = types.SimpleNamespace(received=None, kwargs=None)

    def get_metrics(df, **kwargs):
        state.received = df
        state.kwargs = kwargs
        return pd.DataFrame(
            {
                "voc": [0.55],
                "jsc": [-0.0212],  # A/cm²
                "vmpp": [0.45],
                "jmpp": [-0.0188],  # A/cm²
                "pmpp": [-0.00846],  # W/cm²
                "ff": [0.726],
            }
        )

    jv_analysis_mod = types.ModuleType("bric_analysis_libraries.jv.jv_analysis")
    jv_analysis_mod.get_metrics = get_metrics
    jv_mod = types.ModuleType("bric_analysis_libraries.jv")
    jv_mod.jv_analysis = jv_analysis_mod
    bric_mod = types.ModuleType("bric_analysis_libraries")
    bric_mod.jv = jv_mod

    monkeypatch.setitem(sys.modules, "bric_analysis_libraries", bric_mod)
    monkeypatch.setitem(sys.modules, "bric_analysis_libraries.jv", jv_mod)
    monkeypatch.setitem(
        sys.modules, "bric_analysis_libraries.jv.jv_analysis", jv_analysis_mod
    )
    return state


def test_import_does_not_require_analysis_libraries() -> None:
    # checked in a fresh interpreter: other tests may legitimately import
    # bric at runtime, so the in-process sys.modules is not meaningful here
    import os
    import subprocess
    from pathlib import Path

    src = Path(__file__).resolve().parent.parent / "src"
    code = (
        "import sys; import iv_lab.analysis; "
        "assert 'bric_analysis_libraries' not in sys.modules, 'imported at module load'; "
        "print('ok')"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": str(src)},
    )
    assert result.stdout.strip() == "ok", result.stderr


def test_compute_jv_metrics_legacy_dataframe_layout(fake_bric) -> None:
    voltage = [0.0, 0.2, 0.4, 0.6]
    current = [-0.0034, -0.0033, -0.0028, 0.001]  # A
    active_area = 0.16  # cm²

    compute_jv_metrics(voltage, current, active_area, cell_name="my cell")

    df = fake_bric.received
    # legacy layout: voltage as index, current density as the only column
    assert list(df.index) == voltage
    assert list(df.columns) == ["my cell"]
    assert df["my cell"].iloc[0] == pytest.approx(-0.0034 / 0.16)
    # legacy call arguments
    assert fake_bric.kwargs == {"generator": False, "fit_window": 4}


def test_compute_jv_metrics_legacy_unit_conversions(fake_bric) -> None:
    metrics = compute_jv_metrics([0.0, 0.5], [-0.003, 0.001], 0.16)

    assert isinstance(metrics, JVMetrics)
    assert metrics.Voc == pytest.approx(0.55)
    assert metrics.Jsc == pytest.approx(-21.2)  # A/cm² -> mA/cm²
    assert metrics.Vmpp == pytest.approx(0.45)
    assert metrics.Jmpp == pytest.approx(-18.8)
    assert metrics.Pmpp == pytest.approx(8.46)  # abs, W/cm² -> mW/cm²
    assert metrics.FF == pytest.approx(0.726)


def test_pce_legacy_formula() -> None:
    # 100 * |Pmpp| / avgLightLevel
    assert pce(8.46, 100.0) == pytest.approx(8.46)
    assert pce(8.46, 50.0) == pytest.approx(16.92)
    assert pce(-8.46, 100.0) == pytest.approx(8.46)


def test_real_bric_pipeline_on_emulated_diode() -> None:
    """End-to-end check with the real analysis package (skipped when it
    is not installed). Exercises the scipy ``trapz`` compatibility shim."""
    pytest.importorskip("bric_analysis_libraries")

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

    # the emulated diode model: Voc = 0.55 V, Isc = -4 mA over 0.16 cm²
    assert metrics.Voc == pytest.approx(0.55, abs=0.01)
    assert metrics.Jsc == pytest.approx(-25.0, rel=0.02)
    assert 0.0 < metrics.Vmpp < 0.55
    assert 0.4 < metrics.FF < 0.9
    assert metrics.Pmpp > 0
