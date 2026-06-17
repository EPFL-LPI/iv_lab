"""Headless emulated constant-voltage and constant-current protocol tests."""

import pytest

from iv_lab.config import LampSettings, SMUSettings
from iv_lab.data import ConstantCurrentResults, ConstantVoltageResults
from iv_lab.hardware.lamp.drivers.emulated import EmulatedLamp
from iv_lab.hardware.smu.base import SMUChannel
from iv_lab.hardware.smu.drivers.emulated import EmulatedSMU
from iv_lab.measurements.protocols import (
    ConstantCurrentProtocol,
    ConstantVoltageProtocol,
)

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
        LampSettings(
            brand="manual", model="manual", emulate=True, lightLevelDict=None
        )
    )
    lamp.connect()
    return lamp


def make_protocol(protocol_cls, smu=None, lamp=None, **kwargs):
    smu = smu or make_smu()
    lamp = lamp or make_lamp()
    protocol = protocol_cls(smu, lamp, **kwargs)
    protocol.light_intensity_measure_time = 0.0
    protocol.light_intensity_poll_interval = 0.0
    return protocol


def base_params(**overrides) -> dict:
    params = {
        "light_int": 100.0,
        "interval": 0.005,
        "duration": 0.05,
        "Imax": 0.01,
        "Vmax": 2.0,
        "Dwell": 0.0,
        "Nwire": "2 wire",
        "active_area": 0.16,
        "cell_name": "test cell",
    }
    params.update(overrides)
    return params


# --- constant voltage (measure J) ---


def test_constant_voltage_returns_plausible_currents() -> None:
    protocol = make_protocol(ConstantVoltageProtocol)

    result = protocol.run(base_params(set_voltage=0.2))

    assert isinstance(result, ConstantVoltageResults)
    assert result.scan_type == "CV"
    assert len(result.time) >= 2
    assert len(result.current) == len(result.time)
    # legacy fills the voltage column with the setpoint
    assert all(v == 0.2 for v in result.voltage)
    # the emulated diode at 0.2 V is still close to the photocurrent
    assert result.current[0] == pytest.approx(-0.00397, rel=0.05)
    # time axis starts at zero and increases
    assert result.time[0] == pytest.approx(0.0, abs=0.01)
    assert all(b > a for a, b in zip(result.time, result.time[1:], strict=False))
    assert result.set_voltage == 0.2


def test_constant_voltage_out_of_compliance_raises_legacy_error() -> None:
    protocol = make_protocol(ConstantVoltageProtocol)

    with pytest.raises(ValueError, match="set voltage outside of compliance"):
        protocol.run(base_params(set_voltage=5.0))


def test_constant_voltage_interval_adjusted_with_warning() -> None:
    warnings: list[str] = []
    smu = make_smu()
    smu.meas_period_min = 0.02
    protocol = make_protocol(
        ConstantVoltageProtocol, smu, warning_callback=warnings.append
    )

    result = protocol.run(base_params(set_voltage=0.0, interval=0.001))

    # legacy: interval clamped to meas_period_min
    assert result.interval == pytest.approx(0.02)
    assert any("unable to provide the requested measurement rate" in w for w in warnings)


def test_constant_voltage_parallel_reference_records_iref() -> None:
    smu = make_smu(useReferenceDiode=True)
    smu.reference_diode_parallel = True
    protocol = make_protocol(ConstantVoltageProtocol, smu)

    result = protocol.run(base_params(set_voltage=0.0))

    assert len(result.current_reference) == len(result.current)
    assert result.light_int_meas == pytest.approx(100.0, rel=0.05)


def test_constant_voltage_hardware_safe_after_run_and_cancel() -> None:
    smu = make_smu()
    lamp = make_lamp()
    samples: list[dict] = []

    protocol = make_protocol(
        ConstantVoltageProtocol,
        smu,
        lamp,
        data_callback=samples.append,
        cancel_callback=lambda: len(samples) >= 2,
    )

    result = protocol.run(base_params(set_voltage=0.1, duration=60.0))

    # cancelled long run returns partial data quickly and leaves things safe
    assert len(result.time) == 2
    assert not smu.output_enabled(SMUChannel.CELL)
    assert not lamp.light_is_on


# --- constant current (measure V) ---


def test_constant_current_returns_plausible_voltages() -> None:
    protocol = make_protocol(ConstantCurrentProtocol)

    result = protocol.run(base_params(set_current=0.0))

    assert isinstance(result, ConstantCurrentResults)
    assert result.scan_type == "CC"
    assert len(result.time) >= 2
    assert len(result.voltage) == len(result.time)
    # sourcing 0 A on the emulated diode floats at Voc = 0.55 V
    assert result.voltage[0] == pytest.approx(0.55, abs=0.01)
    # legacy fills the current column with the setpoint
    assert all(i == 0.0 for i in result.current)
    # the legacy CC loop records no reference diode data
    assert result.current_reference is None


def test_constant_current_out_of_compliance_raises_legacy_error() -> None:
    protocol = make_protocol(ConstantCurrentProtocol)

    with pytest.raises(ValueError, match="set current outside of compliance"):
        protocol.run(base_params(set_current=1.0))


def test_constant_current_initial_light_measurement_recorded() -> None:
    smu = make_smu(useReferenceDiode=True)
    smu.reference_diode_parallel = False
    protocol = make_protocol(ConstantCurrentProtocol, smu)

    result = protocol.run(base_params(set_current=0.0))

    # CC uses the initial reference-diode measurement (legacy)
    assert result.light_int_meas == pytest.approx(100.0, rel=0.05)


def test_constant_current_hardware_safe_after_run() -> None:
    smu = make_smu()
    lamp = make_lamp()
    protocol = make_protocol(ConstantCurrentProtocol, smu, lamp)

    protocol.run(base_params(set_current=0.001))

    assert not smu.output_enabled(SMUChannel.CELL)
    assert not lamp.light_is_on


def test_status_messages_follow_legacy_flow() -> None:
    messages: list[str] = []
    protocol = make_protocol(ConstantCurrentProtocol, status_callback=messages.append)

    protocol.run(base_params(set_current=0.0))

    assert "Turning lamp on..." in messages
    assert "Running Constant Current Measurement..." in messages
    assert "Run finished" in messages
    assert "Turning lamp off..." in messages
