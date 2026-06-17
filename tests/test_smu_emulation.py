import sys

import pytest

from iv_lab.config import SMUSettings
from iv_lab.hardware.smu import (
    BaseSMU,
    SMUChannel,
    available_smu_drivers,
    create_smu,
    get_smu_driver,
    register_smu_driver,
)
from iv_lab.hardware.smu.drivers.emulated import (
    EMULATED_VOC,
    LEGACY_INTEGRATION_DELAY,
    EmulatedSMU,
)


def make_settings(**overrides) -> SMUSettings:
    data = {
        "brand": "Keithley",
        "model": "2401",
        "visa_address": "ASRL2",
        "visa_library": "C:\\Windows\\System32\\visa32.dll",
        "emulate": True,
    }
    data.update(overrides)
    return SMUSettings(**data)


def make_emulated_smu() -> EmulatedSMU:
    smu = EmulatedSMU(make_settings())
    smu.integration_delay = 0.0  # speed up tests
    smu.full_sun_reference_current = 0.004
    return smu


# --- factory and registry ---


def test_factory_returns_emulated_smu_when_emulate_true() -> None:
    smu = create_smu(make_settings(emulate=True))

    assert isinstance(smu, EmulatedSMU)
    assert isinstance(smu, BaseSMU)
    assert smu.name == "Emulated Keithley 2401"


def test_factory_applies_settings_to_emulated_smu() -> None:
    smu = create_smu(
        make_settings(autorange=False, measSpeed="fast", useReferenceDiode=False)
    )

    assert smu.autorange is False
    assert smu.meas_speed == "fast"
    assert smu.use_reference_diode is False


def test_factory_raises_for_unknown_real_driver() -> None:
    with pytest.raises(ValueError, match="no SMU driver registered"):
        create_smu(make_settings(emulate=False, brand="NoSuchBrand", model="9999"))


def test_factory_emulation_does_not_import_hardware_libraries() -> None:
    create_smu(make_settings(emulate=True))

    for module in ("pyvisa", "pymeasure", "pytrinamic"):
        assert module not in sys.modules


def test_registry_register_and_lookup() -> None:
    @register_smu_driver("TestBrand", "M1", "M2")
    class TestSMU(EmulatedSMU):
        pass

    try:
        # lookup is case-insensitive
        assert get_smu_driver("testbrand", "m1") is TestSMU
        assert get_smu_driver("TestBrand", "M2") is TestSMU
        assert ("testbrand", "m1") in available_smu_drivers()

        # duplicate registration of a different class is rejected
        with pytest.raises(ValueError, match="already registered"):

            @register_smu_driver("TestBrand", "M1")
            class OtherSMU(EmulatedSMU):
                pass

    finally:
        from iv_lab.hardware.smu import registry

        for key in [("testbrand", "m1"), ("testbrand", "m2")]:
            registry._registry.pop(key, None)


# --- emulated SMU behavior ---


def test_emulated_smu_connect_lifecycle() -> None:
    smu = make_emulated_smu()

    smu.connect()
    assert smu.is_connected()

    smu.enable_output(SMUChannel.CELL)
    smu.disconnect()

    assert not smu.is_connected()
    # disconnecting leaves the emulated instrument safe
    assert not smu.output_enabled(SMUChannel.CELL)


def test_emulated_iv_curve_is_diode_shaped() -> None:
    smu = make_emulated_smu()
    smu.connect()

    smu.setup_voltage_output(SMUChannel.CELL, 0.01)
    smu.enable_output(SMUChannel.CELL)

    voltages = [v / 100 for v in range(0, 65, 5)]  # 0 .. 0.6 V
    currents = []
    for v in voltages:
        smu.set_voltage(SMUChannel.CELL, v)
        currents.append(smu.measure_current(SMUChannel.CELL))

    # photocurrent at short circuit: i(0) ~ Isc = -full_sun_reference_current
    assert currents[0] == pytest.approx(-0.004, rel=0.02)
    # monotonically increasing diode curve
    assert all(b > a for a, b in zip(currents, currents[1:], strict=False))
    # crosses zero at the emulated Voc
    assert min(currents) < 0 < max(currents)
    zero_crossing = next(v for v, i in zip(voltages, currents, strict=False) if i >= 0)
    assert zero_crossing == pytest.approx(EMULATED_VOC, abs=0.05)


def test_emulated_voc_in_current_source_mode() -> None:
    # legacy measureVoc: source 0 A, measure voltage
    smu = make_emulated_smu()
    smu.connect()

    smu.setup_current_output(SMUChannel.CELL, 2.0)
    smu.set_current(SMUChannel.CELL, 0.0)
    smu.enable_output(SMUChannel.CELL)

    assert smu.measure_voltage(SMUChannel.CELL) == pytest.approx(EMULATED_VOC, abs=1e-6)


def test_emulated_current_clipped_at_compliance() -> None:
    smu = make_emulated_smu()
    smu.connect()

    smu.setup_voltage_output(SMUChannel.CELL, 0.001)  # compliance below Isc
    smu.set_voltage(SMUChannel.CELL, 0.0)

    assert smu.measure_current(SMUChannel.CELL) == pytest.approx(-0.001)


def test_emulated_reference_diode_reads_full_sun_current() -> None:
    smu = make_emulated_smu()
    smu.connect()

    smu.setup_reference_diode()
    assert smu.output_enabled(SMUChannel.REFERENCE)

    i_ref = smu.measure_current(SMUChannel.REFERENCE)
    # at 0 V the diode current is ~Isc (legacy reads near -fullSunReferenceCurrent)
    assert i_ref == pytest.approx(-smu.full_sun_reference_current, rel=0.02)

    i_cell, i_ref_both = smu.measure_both_currents()
    assert i_ref_both == pytest.approx(i_ref)


def test_emulated_measure_both_iv_points() -> None:
    # legacy measure_current_and_voltage("CHAN_BOTH"): (i_a, v_a, i_b, v_b)
    smu = make_emulated_smu()
    smu.connect()
    smu.setup_voltage_output(SMUChannel.CELL, 0.01)
    smu.set_voltage(SMUChannel.CELL, 0.3)
    smu.setup_reference_diode()

    i_cell, v_cell, i_ref, v_ref = smu.measure_both_iv_points()

    assert v_cell == pytest.approx(0.3)
    assert v_ref == pytest.approx(0.0)
    assert i_cell == pytest.approx(smu.measure_current(SMUChannel.CELL))
    assert i_ref == pytest.approx(-smu.full_sun_reference_current, rel=0.02)


def test_emulated_measure_iv_point() -> None:
    smu = make_emulated_smu()
    smu.connect()

    smu.setup_voltage_output(SMUChannel.CELL, 0.01)
    smu.set_voltage(SMUChannel.CELL, 0.3)

    i, v = smu.measure_iv_point(SMUChannel.CELL)

    assert v == pytest.approx(0.3)
    assert i == pytest.approx(smu.measure_current(SMUChannel.CELL))


def test_emulated_smu_is_deterministic_by_default() -> None:
    smu = make_emulated_smu()
    smu.connect()
    smu.setup_voltage_output(SMUChannel.CELL, 0.01)
    smu.set_voltage(SMUChannel.CELL, 0.2)

    readings = {smu.measure_current(SMUChannel.CELL) for _ in range(10)}

    assert len(readings) == 1  # no noise unless requested


def test_emulated_noise_is_seeded_and_reproducible() -> None:
    def run() -> list[float]:
        smu = make_emulated_smu()
        smu.connect()
        smu.setup_voltage_output(SMUChannel.CELL, 0.01)
        smu.set_voltage(SMUChannel.CELL, 0.2)
        smu.current_noise = 1e-5
        smu.seed_noise(42)
        return [smu.measure_current(SMUChannel.CELL) for _ in range(5)]

    first, second = run(), run()

    assert first == second  # deterministic with a fixed seed
    assert len(set(first)) > 1  # but actually noisy


def test_emulated_default_integration_delay_matches_legacy() -> None:
    assert EmulatedSMU(make_settings()).integration_delay == LEGACY_INTEGRATION_DELAY


def test_emulated_set_ttl_level_is_ignored() -> None:
    # legacy set_TTL_level does nothing in emulation mode
    make_emulated_smu().set_ttl_level(3)


def test_emulated_turn_off_disables_all_outputs() -> None:
    smu = make_emulated_smu()
    smu.connect()
    smu.enable_output(SMUChannel.CELL)
    smu.enable_output(SMUChannel.REFERENCE)

    smu.turn_off()

    assert not smu.output_enabled(SMUChannel.CELL)
    assert not smu.output_enabled(SMUChannel.REFERENCE)
