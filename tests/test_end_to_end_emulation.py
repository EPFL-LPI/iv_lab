"""Step 16 end-to-end validation: a full user session in emulation.

Drives the complete chain through the real GUI widget paths — settings
loading, factories, core system, protocols, workers, services, file
writer, PDF report — with emulated hardware and the *real* analysis
package when installed. No hardware libraries, all files in tmp_path.
"""

import json
from pathlib import Path

import pytest

from iv_lab.config import SystemSettings, load_settings
from iv_lab.core import IVLabSystem
from iv_lab.gui.main_window import MainWindow
from iv_lab.services import unscramble_string, write_users

USERS = {"felix": "111111", "alice": "333333", "user": "123456"}


def make_settings(tmp_path: Path) -> SystemSettings:
    data = {
        "computer": {
            "hardware": "Test PC",
            "os": "Windows 11",
            "basePath": str(tmp_path / "data_root"),
            "sdPath": str(tmp_path / "sd"),
        },
        "IVsys": {
            "sysName": "IVLab",
            "fullSunReferenceCurrent": 0.004,
            "calibrationDateTime": "Wed Jun  8 16:07:18 2022",
            "referenceDiodeImax": 0.005,
        },
        "lamp": {
            "brand": "Wavelabs",
            "model": "Sinus70",
            "emulate": True,
            "lightLevelDict": {"100": "1 sun", "50": "0.5 sun", "0": "dummy"},
        },
        "SMU": {
            "brand": "Keithley",
            "model": "2602",
            "visa_address": "GPIB0::24::INSTR",
            "visa_library": "visa64.dll",
            "emulate": True,
            "useReferenceDiode": True,
        },
    }
    path = tmp_path / "system_settings.json"
    path.write_text(json.dumps(data))
    return load_settings(path)


def make_window(tmp_path: Path) -> MainWindow:
    write_users(tmp_path / "users.txt", USERS)
    system = IVLabSystem(
        make_settings(tmp_path),
        users_file=tmp_path / "users.txt",
        settings_file=tmp_path / "system_settings.json",
        threaded=False,
    )
    system.smu.integration_delay = 0.0
    system.smu.meas_period_min = 0.0

    # shorten the legacy waits (5 s light measurement, 1 s Voc check)
    original_build = system._build_protocol

    def fast_build(spec):
        protocol = original_build(spec)
        protocol.light_intensity_measure_time = 0.02
        protocol.light_intensity_poll_interval = 0.0
        protocol.voc_check_wait = 0.0
        protocol.voc_poll_interval = 0.0
        return protocol

    system._build_protocol = fast_build

    window = MainWindow(system)
    window.suppress_error_dialogs = True
    return window


def login(window: MainWindow, username: str, password: str) -> None:
    window.field_username.setText(username)
    window.field_sciper.setText(password)
    window.button_login.click()


def test_full_session_login_to_logout(tmp_path: Path) -> None:
    window = make_window(tmp_path)
    system = window.system
    panel = window.measurement_panel

    # --- login and hardware init ---
    login(window, "felix", "111111")
    assert system.user.username == "felix"
    window.button_initialize.click()
    assert system.smu.is_connected()
    assert system.lamp.is_connected()

    # --- lit J-V scan at 1 sun, through the real click path ---
    window.field_cell_name.setText("E2E Cell")
    window.light_panel.menu_light_level.setCurrentIndex(
        window.light_panel.menu_light_level.findText("100.0 % Sun")
    )
    panel.menu_measurement.setCurrentIndex(0)
    panel.field_iv_min_v.setText("0.0")
    panel.field_iv_max_v.setText("0.6")
    panel.field_iv_v_step.setText("10.0")  # 10 mV
    panel.field_iv_sweep_rate.setText("100000")
    panel.menu_sweep_direction.setCurrentIndex(0)
    panel.field_cell_active_area.setText("0.16")
    panel.button_run_iv.click()

    result = system.results["JV"]
    assert len(result.voltage) > 30
    # real bric metrics on the emulated diode
    assert result.Voc == pytest.approx(0.55, abs=0.01)
    assert result.Jsc == pytest.approx(-25.0, rel=0.05)
    assert result.PCE is not None and result.PCE > 0
    # parallel reference diode measured ~100% sun
    assert result.light_int_meas == pytest.approx(100.0, rel=0.05)
    # the results grid shows the values
    assert window.plot_panel.field_voc.value.text() == "0.5500"

    # --- save: legacy-format CSV, PDF report, scrambled sd duplicate ---
    window.button_save_data.click()

    data_dir = tmp_path / "data_root" / "felix" / "data"
    csv_files = list(data_dir.glob("*.csv"))
    pdf_files = list(data_dir.glob("*.pdf"))
    assert len(csv_files) == 1 and len(pdf_files) == 1
    assert csv_files[0].name.startswith("E2E Cell_JV_")

    lines = csv_files[0].read_text().splitlines()
    n_header = int(lines[0].split(",")[1])
    assert lines[0].startswith("nHeader,")
    assert "Measurement System,IVLab" in lines
    assert any(line.startswith("Voc,0.55") for line in lines)
    # data rows parse: V, I, light intensity
    for line in lines[n_header:]:
        assert len([float(x) for x in line.split(",")]) == 3

    assert pdf_files[0].read_bytes()[:5] == b"%PDF-"

    sd_files = [f for f in (tmp_path / "sd").iterdir() if f.name != "ivlablog.txt"]
    assert len(sd_files) == 1
    assert unscramble_string(sd_files[0].read_text()) == csv_files[0].read_text()

    # --- MPP tracking ---
    panel.menu_measurement.setCurrentIndex(3)
    panel.field_mpp_start_v.setText("0.45")
    panel.field_mpp_interval.setText("0.002")
    panel.field_mpp_duration.setText("0.05")
    panel.button_run_mpp.click()

    mpp = system.results["MPP"]
    assert len(mpp.time) >= 5
    assert all(0.0 < v < 0.55 for v in mpp.voltage)

    # --- calibration (felix has permission) and save to settings ---
    panel.menu_measurement.setCurrentIndex(4)
    cal = panel.calibration_panel
    cal.field_diode_reference_current.setText("4.00")
    cal.field_interval.setText("0.002")
    cal.field_duration.setText("0.04")
    cal.button_run.click()
    assert float(cal.field_reference_cell_current.text()) == pytest.approx(4.0, rel=0.05)

    cal.button_save.click()
    saved_settings = load_settings(tmp_path / "system_settings.json")
    assert saved_settings.IVsys.fullSunReferenceCurrent == pytest.approx(0.004, rel=0.05)
    assert saved_settings.lamp.brand == "Wavelabs"  # file intact

    # --- logout: logbook, hardware safe and disconnected ---
    window._do_logout("end-to-end validation run")

    log_lines = (tmp_path / "sd" / "ivlablog.txt").read_text().splitlines()
    assert log_lines[0].endswith("user felix logged on")
    assert log_lines[-2].endswith("user comment: end-to-end validation run")
    assert log_lines[-1].endswith("user felix logged off")
    assert not system.smu.is_connected()
    assert not system.lamp.light_is_on


def test_calibration_permissions_across_users(tmp_path: Path) -> None:
    window = make_window(tmp_path)

    # alice: no calibration entry
    login(window, "alice", "333333")
    assert window.measurement_panel.menu_measurement.count() == 4
    window._do_logout("")

    # blank username logs in as the generic user, with calibration
    login(window, "", "anything")
    assert window.system.user.username == "user"
    assert window.measurement_panel.menu_measurement.count() == 5
