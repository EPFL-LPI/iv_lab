"""Headless emulated MPP tracking protocol tests."""

import pytest

from iv_lab.config import LampSettings, SMUSettings
from iv_lab.data import MPPResults
from iv_lab.hardware.lamp.drivers.emulated import EmulatedLamp
from iv_lab.hardware.smu.base import SMUChannel
from iv_lab.hardware.smu.drivers.emulated import EMULATED_VOC, EmulatedSMU
from iv_lab.measurements.protocols import MPPTrackingProtocol

EMULATED_FULL_SUN_CURRENT = 0.004


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
    smu.meas_period_min = 0.0
    smu.full_sun_reference_current = EMULATED_FULL_SUN_CURRENT
    smu.connect()
    return smu


def make_lamp() -> EmulatedLamp:
    lamp = EmulatedLamp(
        LampSettings(brand="manual", model="manual", emulate=True)
    )
    lamp.connect()
    return lamp


def make_protocol(smu=None, lamp=None, **kwargs) -> MPPTrackingProtocol:
    smu = smu or make_smu()
    lamp = lamp or make_lamp()
    protocol = MPPTrackingProtocol(smu, lamp, **kwargs)
    protocol.light_intensity_measure_time = 0.0
    protocol.light_intensity_poll_interval = 0.0
    protocol.voc_check_wait = 0.0
    protocol.voc_poll_interval = 0.0
    # speed up the automatic Voc->0 start scan
    protocol.auto_scan_dv = 0.02
    protocol.auto_scan_sweep_rate = 100.0
    return protocol


def mpp_params(**overrides) -> dict:
    params = {
        "light_int": 100.0,
        "start_voltage": 0.45,
        "interval": 0.002,
        "duration": 0.1,
        "Imax": 0.01,
        "Vmax": 2.0,
        "Dwell": 0.0,
        "Nwire": "2 wire",
        "active_area": 0.16,
        "cell_name": "test cell",
    }
    params.update(overrides)
    return params


def test_mpp_tracking_returns_plausible_result() -> None:
    protocol = make_protocol()

    result = protocol.run(mpp_params())

    assert isinstance(result, MPPResults)
    assert result.scan_type == "MPP"
    assert len(result.time) >= 5
    assert len(result.voltage) == len(result.time)
    assert len(result.current) == len(result.time)
    # tracking stays near the emulated MPP region, below Voc
    assert all(0.0 < v < EMULATED_VOC for v in result.voltage)
    # the cell delivers power: positive v, negative i
    assert all(i < 0 for i in result.current)
    assert result.start_voltage == 0.45


def test_mpp_voltage_stays_near_maximum_power_point() -> None:
    # the emulated diode has its MPP around 0.45 V; starting away from it,
    # the perturb-and-observe algorithm must move toward it
    protocol = make_protocol(
        voltage_step_initial=0.01, voltage_step_max=0.02, voltage_step_min=0.002
    )

    result = protocol.run(mpp_params(start_voltage=0.30, duration=0.4, interval=0.001))

    # final tracking voltage is closer to the MPP than the start
    assert abs(result.voltage[-1] - 0.45) < abs(0.30 - 0.45)


def test_mpp_auto_start_runs_jv_scan_first() -> None:
    protocol = make_protocol()

    result = protocol.run(mpp_params(start_voltage="auto", duration=0.05))

    # the auto scan finds the MPP of the emulated diode (~0.45 V) and the
    # result records the actual numeric start voltage (legacy)
    assert isinstance(result.start_voltage, float)
    assert result.start_voltage == pytest.approx(0.45, abs=0.07)


def test_mpp_manual_start_outside_compliance_raises() -> None:
    protocol = make_protocol()

    with pytest.raises(ValueError, match="start voltage outside of compliance"):
        protocol.run(mpp_params(start_voltage=5.0))


def test_mpp_interval_clamped_with_warning() -> None:
    warnings: list[str] = []
    smu = make_smu()
    smu.meas_period_min = 0.01
    protocol = make_protocol(smu, warning_callback=warnings.append)

    result = protocol.run(mpp_params(interval=0.0001))

    assert result.interval == pytest.approx(0.01)
    assert any("unable to provide the requested measurement rate" in w for w in warnings)


def test_mpp_parallel_reference_records_iref_and_light_level() -> None:
    smu = make_smu(useReferenceDiode=True)
    smu.reference_diode_parallel = True
    protocol = make_protocol(smu)

    result = protocol.run(mpp_params())

    assert len(result.current_reference) == len(result.time)
    assert result.light_int_meas == pytest.approx(100.0, rel=0.05)


def test_mpp_cancellation_returns_partial_data() -> None:
    smu = make_smu()
    samples: list[dict] = []
    protocol = make_protocol(
        smu,
        data_callback=samples.append,
        cancel_callback=lambda: len(samples) >= 3,
    )

    result = protocol.run(mpp_params(duration=60.0))

    assert len(result.time) == 3
    assert not smu.output_enabled(SMUChannel.CELL)


def test_mpp_hardware_safe_after_run() -> None:
    smu = make_smu()
    lamp = make_lamp()
    protocol = make_protocol(smu, lamp)

    protocol.run(mpp_params())

    assert not smu.output_enabled(SMUChannel.CELL)
    assert not smu.output_enabled(SMUChannel.REFERENCE)
    assert not lamp.light_is_on


def test_mpp_legacy_voltage_step_defaults() -> None:
    protocol = make_protocol()

    # legacy system.__init__ MPPVoltageStep* defaults
    assert protocol.voltage_step_initial == 0.002
    assert protocol.voltage_step_max == 0.002
    assert protocol.voltage_step_min == 0.001
