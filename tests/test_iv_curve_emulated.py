"""Headless emulated J-V scan protocol tests (no GUI, no hardware)."""

import pytest

from iv_lab.analysis.jv_metrics import JVMetrics
from iv_lab.config import LampSettings, SMUSettings
from iv_lab.data import IVResults
from iv_lab.hardware.lamp.drivers.emulated import EmulatedLamp
from iv_lab.hardware.smu.base import SMUChannel
from iv_lab.hardware.smu.drivers.emulated import EmulatedSMU
from iv_lab.measurements.protocols import IVCurveProtocol, VocPolarityError

EMULATED_FULL_SUN_CURRENT = 0.004


def fake_metrics(voltage, current, active_area, cell_name="cell") -> JVMetrics:
    return JVMetrics(Voc=0.55, Jsc=-21.2, Vmpp=0.45, Jmpp=-18.8, Pmpp=8.46, FF=0.726)


def make_smu(**overrides) -> EmulatedSMU:
    data = {
        "brand": "Keithley",
        "model": "2602",
        "visa_address": "GPIB0::24::INSTR",
        "visa_library": "visa64.dll",
        "emulate": True,
        "useReferenceDiode": False,
    }
    data.update(overrides)
    smu = EmulatedSMU(SMUSettings(**data))
    smu.integration_delay = 0.0
    smu.meas_period_min = 0.0  # avoid the legacy rate-limit dV adjustment
    smu.full_sun_reference_current = EMULATED_FULL_SUN_CURRENT
    smu.connect()
    return smu


def make_lamp() -> EmulatedLamp:
    lamp = EmulatedLamp(
        LampSettings(
            brand="Wavelabs",
            model="Sinus70",
            emulate=True,
            lightLevelDict={"100": "1 sun", "50": "0.5 sun", "0": "dummy"},
        )
    )
    lamp.connect()
    return lamp


def make_protocol(smu=None, lamp=None, **kwargs) -> IVCurveProtocol:
    smu = smu or make_smu()
    lamp = lamp or make_lamp()
    kwargs.setdefault("metrics_function", fake_metrics)
    protocol = IVCurveProtocol(smu, lamp, **kwargs)
    # legacy waits, shortened for tests
    protocol.light_intensity_measure_time = 0.0
    protocol.light_intensity_poll_interval = 0.0
    protocol.voc_check_wait = 0.0
    protocol.voc_poll_interval = 0.0
    return protocol


def iv_params(**overrides) -> dict:
    params = {
        "light_int": 100.0,
        "start_V": 0.0,
        "stop_V": 0.6,
        "dV": 0.05,
        "sweep_rate": 1000.0,  # effectively no waiting between points
        "Imax": 0.01,
        "Vmax": 2.0,
        "Dwell": 0.0,
        "Nwire": "2 wire",
        "active_area": 0.16,
        "cell_name": "test cell",
        "Fwd_current_limit": 0.001,
    }
    params.update(overrides)
    return params


def test_emulated_iv_scan_returns_result_with_plausible_data() -> None:
    protocol = make_protocol()

    result = protocol.run(iv_params())

    assert isinstance(result, IVResults)
    assert result.scan_type == "JV"
    # legacy point count: int(abs((stop-start)/dV) + 1); floating point
    # makes 0.6/0.05 = 11.999... so this is 12 points, exactly as legacy
    assert len(result.voltage) == 12
    assert len(result.current) == 12
    assert result.voltage[0] == pytest.approx(0.0)
    assert result.voltage[-1] == pytest.approx(0.6)
    # diode-shaped: photocurrent negative at 0 V, positive past Voc
    assert result.current[0] == pytest.approx(-EMULATED_FULL_SUN_CURRENT, rel=0.02)
    assert result.current[-1] > 0
    # metrics from the injected analysis function, PCE per legacy formula
    assert result.Voc == pytest.approx(0.55)
    assert result.FF == pytest.approx(0.726)
    assert result.PCE == pytest.approx(8.46)
    # parameters recorded with legacy key spelling
    assert result.cell_name == "test cell"
    assert result.start_V == pytest.approx(0.0)
    assert result.stop_V == pytest.approx(0.6)


def test_hardware_left_safe_after_scan() -> None:
    smu = make_smu()
    lamp = make_lamp()
    protocol = make_protocol(smu, lamp)

    protocol.run(iv_params())

    assert not smu.output_enabled(SMUChannel.CELL)
    assert not smu.output_enabled(SMUChannel.REFERENCE)
    assert not lamp.light_is_on


def test_hardware_left_safe_after_error() -> None:
    smu = make_smu()
    lamp = make_lamp()
    protocol = make_protocol(smu, lamp)

    def broken_metrics(*args, **kwargs):
        raise RuntimeError("analysis exploded")

    protocol._metrics_function = broken_metrics

    with pytest.raises(RuntimeError, match="analysis exploded"):
        protocol.run(iv_params())

    assert not smu.output_enabled(SMUChannel.CELL)
    assert not lamp.light_is_on


def test_out_of_compliance_voltages_raise_legacy_errors() -> None:
    protocol = make_protocol()

    with pytest.raises(ValueError, match="start voltage outside of compliance"):
        protocol.run(iv_params(start_V=5.0))
    with pytest.raises(ValueError, match="stop voltage outside of compliance"):
        protocol.run(iv_params(stop_V=-5.0))


def test_too_fast_scan_adjusts_dv_and_warns() -> None:
    warnings: list[str] = []
    smu = make_smu()
    smu.meas_period_min = 0.5  # force the rate check to trigger
    protocol = make_protocol(smu, warning_callback=warnings.append)

    result = protocol.run(iv_params(dV=0.001, sweep_rate=1.0))

    # legacy: dV = meas_period_min * sweep_rate + 0.01
    assert result.dV == pytest.approx(0.5 * 1.0 + 0.01)
    assert any("unable to provide the requested measurement rate" in w for w in warnings)


def test_cancellation_returns_partial_data() -> None:
    smu = make_smu()
    measured = []

    cancel_after = 5

    def cancelled() -> bool:
        return len(measured) >= cancel_after

    protocol = make_protocol(smu, cancel_callback=cancelled, data_callback=measured.append)

    result = protocol.run(iv_params())

    assert len(result.voltage) == cancel_after
    assert not smu.output_enabled(SMUChannel.CELL)
    # aborted runs are not analyzed (legacy)
    assert result.Voc is None


def test_dark_scan_skips_metrics() -> None:
    protocol = make_protocol()

    result = protocol.run(iv_params(light_int=0.0))

    assert len(result.voltage) == 12
    assert result.Voc is None
    assert result.PCE is None


def test_voc_start_scan_resolves_start_voltage() -> None:
    protocol = make_protocol()

    result = protocol.run(iv_params(start_V="Voc", stop_V=0.0, Dwell=0.0))

    # the emulated cell has Voc = 0.55 V; sourcing Fwd_current_limit puts
    # the start voltage slightly above it
    assert isinstance(result.start_V, float)
    assert result.start_V == pytest.approx(0.57, abs=0.05)
    assert result.stop_V == pytest.approx(0.0)
    assert len(result.voltage) > 1


def test_wrong_voc_polarity_aborts_scan() -> None:
    smu = make_smu()
    lamp = make_lamp()
    protocol = make_protocol(smu, lamp)
    # the emulated diode always has a positive Voc; force the legacy
    # wrong-polarity reading (legacy checkVOCPolarity: v < 0)
    protocol.measure_voc = lambda params, wait: -0.5

    with pytest.raises(VocPolarityError, match="Incorrect polarity"):
        protocol.run(iv_params())

    # hardware safe after the abort
    assert not smu.output_enabled(SMUChannel.CELL)
    assert not lamp.light_is_on


def test_parallel_reference_diode_records_iref_and_light_level() -> None:
    smu = make_smu(useReferenceDiode=True)
    smu.reference_diode_parallel = True
    protocol = make_protocol(smu)

    result = protocol.run(iv_params())

    assert len(result.current_reference) == len(result.voltage)
    # reference diode at 0 V reads ~ -full_sun_reference_current
    # -> measured light level ~100 % sun
    assert result.light_int_meas == pytest.approx(100.0, rel=0.05)


def test_serial_reference_diode_uses_initial_light_measurement() -> None:
    smu = make_smu(useReferenceDiode=True)
    smu.reference_diode_parallel = False
    protocol = make_protocol(smu)
    protocol.light_intensity_measure_time = 0.0

    result = protocol.run(iv_params())

    # i_ref column is all zeros in the serial case (legacy)
    assert all(i == 0.0 for i in result.current_reference)
    assert result.light_int_meas == pytest.approx(100.0, rel=0.05)


def test_status_messages_follow_legacy_flow() -> None:
    messages: list[str] = []
    protocol = make_protocol(status_callback=messages.append)

    protocol.run(iv_params())

    assert "Turning lamp on..." in messages
    assert "Running J-V Scan..." in messages
    assert "Run finished" in messages
    assert "Turning lamp off..." in messages
