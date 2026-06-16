"""Headless emulated reference diode calibration protocol tests."""

import pytest

from iv_lab.config import ArduinoSettings, LampSettings, SMUSettings
from iv_lab.data import CalibrationResults
from iv_lab.hardware.arduino.drivers.emulated import EmulatedArduino
from iv_lab.hardware.lamp.drivers.emulated import EmulatedLamp
from iv_lab.hardware.smu.base import SMUChannel
from iv_lab.hardware.smu.drivers.emulated import EmulatedSMU
from iv_lab.measurements.protocols import CalibrationProtocol

# the emulated diode reads ~ -full_sun_reference_current at 0 V on both
# channels, so with a matching certified reference current the derived
# calibration must come out at ~ the same value
EMULATED_FULL_SUN_CURRENT = 0.004
CERTIFIED_REFERENCE_CURRENT = 0.004


def make_smu(parallel: bool) -> EmulatedSMU:
    smu = EmulatedSMU(
        SMUSettings(
            brand="Keithley",
            model="2602" if parallel else "2401",
            visa_address="GPIB0::24::INSTR",
            visa_library="visa64.dll",
            emulate=True,
            useReferenceDiode=True,
        )
    )
    smu.integration_delay = 0.0
    smu.meas_period_min = 0.0
    smu.full_sun_reference_current = EMULATED_FULL_SUN_CURRENT
    smu.reference_diode_parallel = parallel
    smu.connect()
    return smu


def make_lamp() -> EmulatedLamp:
    lamp = EmulatedLamp(
        LampSettings(brand="manual", model="manual", emulate=True)
    )
    lamp.connect()
    return lamp


class RecordingArduino(EmulatedArduino):
    def __init__(self) -> None:
        super().__init__(
            ArduinoSettings(
                brand="Arduino", model="Uno", visa_address="ASRL1::INSTR", emulate=True
            )
        )
        self.stage_moves: list[str] = []

    def select_reference_cell(self) -> None:
        super().select_reference_cell()
        self.stage_moves.append("reference")

    def select_test_cell(self) -> None:
        super().select_test_cell()
        self.stage_moves.append("test")


def make_protocol(parallel=True, smu=None, lamp=None, **kwargs) -> CalibrationProtocol:
    smu = smu or make_smu(parallel)
    lamp = lamp or make_lamp()
    protocol = CalibrationProtocol(smu, lamp, **kwargs)
    protocol.light_intensity_measure_time = 0.0
    protocol.light_intensity_poll_interval = 0.0
    return protocol


def cal_params(**overrides) -> dict:
    params = {
        "light_int": 100.0,
        "reference_current": CERTIFIED_REFERENCE_CURRENT,
        "interval": 0.002,
        "duration": 0.04,
        "Imax": 0.01,
        "Vmax": 2.0,
        "Dwell": 0.0,
        "Nwire": "2 wire",
    }
    params.update(overrides)
    return params


def test_parallel_calibration_derives_reference_current() -> None:
    protocol = make_protocol(parallel=True)

    result = protocol.run(cal_params())

    assert isinstance(result, CalibrationResults)
    assert result.scan_type == "Calibration"
    assert len(result.time) >= 2
    assert len(result.current) == len(result.time)
    assert len(result.current_reference) == len(result.time)
    # certified diode matches the emulated diode: derived current ~equal
    assert result.reference_current == pytest.approx(
        EMULATED_FULL_SUN_CURRENT, rel=0.02
    )
    # legacy calFactor: (ref / avgMeas) * (100 / light_int) with avgMeas < 0
    assert result.metadata["calibration_factor"] == pytest.approx(-1.0, rel=0.02)


def test_serial_calibration_measures_channels_sequentially() -> None:
    protocol = make_protocol(parallel=False)

    result = protocol.run(cal_params())

    assert len(result.current) >= 1
    assert len(result.current_reference) >= 1
    assert result.reference_current == pytest.approx(
        EMULATED_FULL_SUN_CURRENT, rel=0.02
    )


def test_iv_old_calibration_moves_the_stage() -> None:
    smu = make_smu(parallel=False)
    arduino = RecordingArduino()
    arduino.connect()
    protocol = make_protocol(
        parallel=False, smu=smu, arduino=arduino, system_name="IV_Old"
    )

    result = protocol.run(cal_params(active_area=0.16))

    # legacy order: reference diode into the beam, then the control diode
    assert arduino.stage_moves == ["reference", "test"]
    assert result.reference_current == pytest.approx(
        EMULATED_FULL_SUN_CURRENT, rel=0.02
    )


def test_half_sun_calibration_scales_with_legacy_formula() -> None:
    protocol = make_protocol(parallel=True)

    result = protocol.run(cal_params(light_int=50.0))

    # calFactor scales by 100/light_int; the emulated diode output does
    # not depend on the lamp, so the derived value doubles
    assert result.reference_current == pytest.approx(
        2.0 * EMULATED_FULL_SUN_CURRENT, rel=0.02
    )


def test_cancelled_calibration_returns_no_reference_current() -> None:
    samples: list[dict] = []
    protocol = make_protocol(
        parallel=True,
        data_callback=samples.append,
        cancel_callback=lambda: len(samples) >= 2,
    )

    result = protocol.run(cal_params(duration=60.0))

    assert result.reference_current is None
    assert len(result.time) == 2


def test_hardware_safe_after_calibration() -> None:
    smu = make_smu(parallel=True)
    lamp = make_lamp()
    protocol = make_protocol(smu=smu, lamp=lamp)

    protocol.run(cal_params())

    assert not smu.output_enabled(SMUChannel.CELL)
    assert not smu.output_enabled(SMUChannel.REFERENCE)
    assert not lamp.light_is_on


def test_status_messages_follow_legacy_flow() -> None:
    messages: list[str] = []
    protocol = make_protocol(parallel=True, status_callback=messages.append)

    protocol.run(cal_params())

    assert "Turning lamp on..." in messages
    assert "Running Reference Diode Calibration..." in messages
    assert "Calibration finished" in messages
    assert "Turning lamp off..." in messages
