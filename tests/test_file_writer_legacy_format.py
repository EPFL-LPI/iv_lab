"""Legacy data-file format compatibility tests (all in tmp_path)."""

from pathlib import Path

import pytest

from iv_lab.data import (
    ConstantCurrentResults,
    ConstantVoltageResults,
    FileWriter,
    IVResults,
    MPPResults,
    SystemContext,
)
from iv_lab.data.results import CalibrationResults
from iv_lab.services import unscramble_string

FULL_SUN_CURRENT = 0.004  # A


def make_context(tmp_path: Path, **overrides) -> SystemContext:
    data = dict(
        base_path=str(tmp_path / "data_root"),
        sd_path=str(tmp_path / "sd"),
        system_name="IVLab",
        smu_brand="Keithley",
        smu_model="2602",
        lamp_display_name="Sinus70 (Wavelabs)",
        use_reference_diode=True,
        full_sun_reference_current=FULL_SUN_CURRENT,
        calibration_datetime="Wed Jun  8 16:07:18 2022",
    )
    data.update(overrides)
    return SystemContext(**data)


def make_writer(tmp_path: Path, **overrides) -> FileWriter:
    return FileWriter(make_context(tmp_path, **overrides), generate_pdf=False)


def iv_result(**overrides) -> IVResults:
    data = dict(
        start_time="20260612_140000",
        cell_name="cellA",
        active_area=0.16,
        light_int=100.0,
        light_int_meas=99.5,
        Nwire="2 wire",
        start_V=0.0,
        stop_V=0.6,
        dV=0.05,
        sweep_rate=0.05,
        Imax=0.01,
        Dwell=5.0,
        voltage=[0.0, 0.05],
        current=[-0.004, -0.0039],
        current_reference=[-0.004, -0.00398],
        Voc=0.55,
        Jsc=-25.0,
        Vmpp=0.45,
        Jmpp=-22.0,
        Pmpp=9.9,
        PCE=9.9,
        FF=0.72,
    )
    data.update(overrides)
    return IVResults(**data)


def read_file(writer: FileWriter, result, username="felix") -> list[str]:
    csv_path, _ = writer.save(result, username)
    return csv_path, csv_path.read_text().splitlines()


def test_jv_file_name_and_location(tmp_path: Path) -> None:
    writer = make_writer(tmp_path)

    csv_path, _ = writer.save(iv_result(), "felix")

    assert csv_path.name == "cellA_JV_20260612_140000.csv"
    assert csv_path.parent == Path(writer.context.base_path) / "felix" / "data"


def test_jv_header_matches_legacy_format(tmp_path: Path) -> None:
    writer = make_writer(tmp_path)

    _, lines = read_file(writer, iv_result())

    assert lines[0] == "nHeader,25"  # 24 header lines + the nHeader line
    assert lines[1] == "Measurement System,IVLab"
    assert lines[2] == "Scan Start Time,20260612_140000"
    assert lines[3] == "Sourcemeter Brand,Keithley"
    assert lines[4] == "Sourcemeter Model,2602"
    assert lines[5] == "Sourcemeter Sense Mode,2 wire"
    assert lines[6] == "Light Source,Sinus70 (Wavelabs)"
    assert lines[7] == "Requested Light Intensity,100.0,% sun"
    assert lines[8] == "Measured Light Intensity,99.5,% sun"
    assert lines[9] == "Reference Diode 1sun Current,4.0,mA"
    assert lines[10] == "Reference Diode calibration date,Wed Jun  8 16:07:18 2022"
    assert lines[11] == "Cell Active Area,0.16,cm^2"
    assert lines[12] == "Start Voltage,0.0,V"
    assert lines[13] == "Stop Voltage,0.6,V"
    assert lines[14] == "Voltage Step,0.05,V"
    assert lines[15] == "Sweep Rate,0.05,V/sec"
    assert lines[16] == "J-V Results"
    assert lines[17] == "Jsc,-25.0,mA/cm^2"
    assert lines[18] == "Voc,0.55,V"
    assert lines[19] == "Fill Factor,0.72"
    assert lines[20] == "PCE,9.9,%"
    # ... Jmpp, Vmpp, Pmpp, then the column captions
    assert lines[24] == "Voltage(V),Current(A),light intensity (% sun)"


def test_jv_data_rows_with_light_intensity_column(tmp_path: Path) -> None:
    writer = make_writer(tmp_path)

    _, lines = read_file(writer, iv_result())

    # light intensity = -100 * i_ref / fullSunReferenceCurrent
    assert lines[25] == "0.0,-0.004,100.0"
    assert lines[26] == "0.05,-0.0039,99.5"
    assert len(lines) == 27


def test_jv_without_reference_diode_omits_light_columns(tmp_path: Path) -> None:
    writer = make_writer(tmp_path, use_reference_diode=False)

    _, lines = read_file(writer, iv_result())

    assert "Voltage(V),Current(A)" in lines
    assert not any("Reference Diode" in line for line in lines)
    assert not any("Measured Light Intensity" in line for line in lines)
    assert lines[-1] == "0.05,-0.0039"
    # nHeader matches the reduced header
    n_header = int(lines[0].split(",")[1])
    assert lines[n_header] == "0.0,-0.004"


def test_dark_jv_scan_omits_metric_lines(tmp_path: Path) -> None:
    writer = make_writer(tmp_path)
    result = iv_result(
        Voc=None, Jsc=None, Vmpp=None, Jmpp=None, Pmpp=None, PCE=None, FF=None
    )

    _, lines = read_file(writer, result)

    for prefix in ("Jsc,", "Voc,", "Fill Factor", "PCE,", "Jmpp,", "Vmpp,", "Pmpp,"):
        assert not any(line.startswith(prefix) for line in lines)
    assert "J-V Results" in lines


def test_cv_file_matches_legacy_format(tmp_path: Path) -> None:
    writer = make_writer(tmp_path)
    result = ConstantVoltageResults(
        start_time="20260612_140000",
        cell_name="cellA",
        active_area=0.16,
        light_int=100.0,
        light_int_meas=100.0,
        Nwire="2 wire",
        set_voltage=0.2,
        interval=0.25,
        duration=30.0,
        time=[0.0, 0.25],
        voltage=[0.2, 0.2],
        current=[-0.0039, -0.0038],
        current_reference=[-0.004, -0.004],
    )

    csv_path, lines = read_file(writer, result)

    assert csv_path.name == "cellA_CV_20260612_140000.csv"
    assert "Set Voltage,0.2,V" in lines
    assert "Measurement Interval,0.25,sec" in lines
    assert "Measurement Duration,30.0,sec" in lines
    assert "Constant Voltage Results" in lines
    assert "Time(s),Voltage(V),Current(A),light intensity (% sun)" in lines
    assert lines[-2] == "0.0,0.2,-0.0039,100.0"
    assert lines[-1] == "0.25,0.2,-0.0038,100.0"


def test_cc_file_matches_legacy_format(tmp_path: Path) -> None:
    writer = make_writer(tmp_path)
    result = ConstantCurrentResults(
        start_time="20260612_140000",
        cell_name="cellA",
        active_area=0.16,
        light_int=100.0,
        Nwire="4 wire",
        set_current=0.0,
        interval=0.25,
        duration=30.0,
        time=[0.0, 0.25],
        voltage=[0.55, 0.551],
        current=[0.0, 0.0],
    )

    csv_path, lines = read_file(writer, result)

    assert csv_path.name == "cellA_CC_20260612_140000.csv"
    assert "Set Current,0.0,A" in lines
    assert "Constant Current Results" in lines
    # CC has no light intensity column, even with a reference diode
    assert "Time(s),Voltage(V),Current(A)" in lines
    assert lines[-2] == "0.0,0.55,0.0"
    assert lines[-1] == "0.25,0.551,0.0"


def test_mpp_file_matches_legacy_format(tmp_path: Path) -> None:
    writer = make_writer(tmp_path)
    result = MPPResults(
        start_time="20260612_140000",
        cell_name="cellA",
        active_area=0.16,
        light_int=100.0,
        light_int_meas=100.0,
        Nwire="2 wire",
        start_voltage=0.45,
        interval=0.25,
        duration=30.0,
        time=[0.0],
        voltage=[0.45],
        current=[-0.0035],
        current_reference=[-0.004],
    )

    csv_path, lines = read_file(writer, result)

    assert csv_path.name == "cellA_MPP_20260612_140000.csv"
    assert "Start Voltage,0.45,V" in lines
    assert "Maximum Power Point Results" in lines
    assert (
        "Time(s),Voltage(V),Current (A),Power(mW/cm^2),light intensity (% sun)"
        in lines
    )
    # power column: abs(i*v*1000/area)
    expected_w = abs(-0.0035 * 0.45 * 1000.0 / 0.16)
    assert lines[-1] == f"0.0,0.45,-0.0035,{round(expected_w, 12)},100.0"


def test_calibration_results_cannot_be_saved(tmp_path: Path) -> None:
    writer = make_writer(tmp_path)

    with pytest.raises(ValueError, match="must be JV, CV, CC, or MPP"):
        writer.save(CalibrationResults(start_time="x", cell_name="c"), "felix")


def test_sd_duplicate_is_scrambled_copy(tmp_path: Path) -> None:
    writer = make_writer(tmp_path)

    csv_path, _ = writer.save(iv_result(), "felix")

    sd_dir = Path(writer.context.sd_path)
    sd_files = list(sd_dir.iterdir())
    assert len(sd_files) == 1
    # scrambled filename decodes to <username>_<csv stem>
    assert unscramble_string(sd_files[0].name) == "felix_cellA_JV_20260612_140000"
    # scrambled content decodes to the exact file content
    assert unscramble_string(sd_files[0].read_text()) == csv_path.read_text()


def test_empty_sd_path_skips_duplicate(tmp_path: Path) -> None:
    writer = make_writer(tmp_path, sd_path="")

    writer.save(iv_result(), "felix")

    assert not (tmp_path / "sd").exists()


def test_status_callback_reports_saved_path(tmp_path: Path) -> None:
    messages: list[str] = []
    writer = FileWriter(
        make_context(tmp_path),
        status_callback=messages.append,
        generate_pdf=False,
    )

    csv_path, _ = writer.save(iv_result(), "felix")

    assert messages == ["Saved data to: " + str(csv_path)]


def test_data_rows_parse_as_numbers(tmp_path: Path) -> None:
    writer = make_writer(tmp_path)

    _, lines = read_file(writer, iv_result())

    n_header = int(lines[0].split(",")[1])
    for line in lines[n_header:]:
        values = [float(x) for x in line.split(",")]
        assert len(values) == 3
