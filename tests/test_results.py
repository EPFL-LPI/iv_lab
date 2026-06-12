from dataclasses import is_dataclass

import pytest

from iv_lab.data import (
    CalibrationResults,
    ConstantCurrentResults,
    ConstantVoltageResults,
    IVResults,
    MPPResults,
)

ALL_RESULT_TYPES = [
    IVResults,
    MPPResults,
    ConstantVoltageResults,
    ConstantCurrentResults,
    CalibrationResults,
]


@pytest.mark.parametrize("result_type", ALL_RESULT_TYPES)
def test_instantiation_with_defaults(result_type) -> None:
    result = result_type()

    assert is_dataclass(result)
    assert result.scan_type  # each type carries its legacy scanType tag
    assert result.cell_name is None
    assert result.metadata == {}


def test_legacy_scan_type_tags() -> None:
    assert IVResults().scan_type == "JV"
    assert ConstantVoltageResults().scan_type == "CV"
    assert ConstantCurrentResults().scan_type == "CC"
    assert MPPResults().scan_type == "MPP"


@pytest.mark.parametrize("result_type", ALL_RESULT_TYPES)
def test_metadata_default_is_not_shared(result_type) -> None:
    a = result_type()
    b = result_type()

    a.metadata["user"] = "felix"

    assert a.metadata == {"user": "felix"}
    assert b.metadata == {}
    assert a.metadata is not b.metadata


def test_array_defaults_are_not_shared() -> None:
    a = IVResults()
    b = IVResults()

    a.voltage.append(0.1)

    assert list(a.voltage) == [0.1]
    assert list(b.voltage) == []
    assert a.voltage is not b.voltage


def test_iv_results_preserve_passed_arrays() -> None:
    v = [0.0, 0.1, 0.2]
    i = [0.005, 0.004, 0.001]
    i_ref = [0.0063, 0.0063, 0.0063]

    result = IVResults(
        cell_name="test cell",
        active_area=0.16,
        light_int=100.0,
        Nwire=4,
        start_V=0.0,
        stop_V=0.6,
        dV=0.02,
        sweep_rate=0.05,
        voltage=v,
        current=i,
        current_reference=i_ref,
        Voc=0.55,
        Jsc=21.3,
        FF=0.72,
        PCE=8.4,
    )

    # the same objects are stored, unchanged and uncopied
    assert result.voltage is v
    assert result.current is i
    assert result.current_reference is i_ref
    assert list(result.voltage) == [0.0, 0.1, 0.2]
    assert result.start_V == 0.0
    assert result.Voc == 0.55


def test_time_series_results_preserve_passed_arrays() -> None:
    t = [0.0, 0.25, 0.5]
    v = [0.45, 0.45, 0.45]
    i = [0.004, 0.0041, 0.0040]

    cv = ConstantVoltageResults(set_voltage=0.45, interval=0.25, time=t, voltage=v, current=i)
    cc = ConstantCurrentResults(set_current=0.0, time=t, voltage=v, current=i)
    mpp = MPPResults(start_voltage="auto", time=t, voltage=v, current=i)

    for result in (cv, cc, mpp):
        assert result.time is t
        assert result.voltage is v
        assert result.current is i

    assert cv.set_voltage == 0.45
    assert cc.set_current == 0.0
    assert mpp.start_voltage == "auto"


def test_calibration_results_fields() -> None:
    result = CalibrationResults(
        time=[0.0, 0.1],
        current=[0.0062, 0.0063],
        current_reference=[0.0063, 0.0063],
        reference_current=0.006318,
        calibration_datetime="Wed Jun  8 16:07:18 2022",
    )

    assert result.scan_type == "Calibration"
    assert result.reference_current == pytest.approx(0.006318)
    assert result.calibration_datetime == "Wed Jun  8 16:07:18 2022"


def test_metadata_holds_arbitrary_legacy_metadata() -> None:
    result = IVResults(metadata={"sysName": "IVLab", "user": "felix"})

    assert result.metadata["sysName"] == "IVLab"
    assert result.metadata["user"] == "felix"
