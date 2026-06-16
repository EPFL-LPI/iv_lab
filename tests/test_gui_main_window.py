"""Headless integration tests: main window wired to an emulated system."""

import json
from pathlib import Path

import pytest

from iv_lab.config import SystemSettings
from iv_lab.core import IVLabSystem
from iv_lab.gui.app import launch
from iv_lab.gui.main_window import MainWindow
from iv_lab.services import write_users

USERS = {"felix": "111111", "alice": "333333", "user": "123456"}


def settings_dict(tmp_path: Path, **overrides) -> dict:
    data = {
        "computer": {
            "hardware": "Test PC",
            "os": "Windows 11",
            "basePath": str(tmp_path / "data_root"),
            "sdPath": "",
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
            "useReferenceDiode": False,
        },
    }
    for key, value in overrides.items():
        data[key].update(value)
    return data


def make_window(tmp_path: Path, **overrides) -> MainWindow:
    settings = SystemSettings.model_validate(settings_dict(tmp_path, **overrides))
    users_file = tmp_path / "users.txt"
    if not users_file.exists():
        write_users(users_file, USERS)
    system = IVLabSystem(
        settings,
        users_file=users_file,
        settings_file=tmp_path / "system_settings.json",
        threaded=False,  # synchronous runs for tests
    )
    system.smu.integration_delay = 0.0
    system.smu.meas_period_min = 0.0
    window = MainWindow(system)
    window.suppress_error_dialogs = True
    return window


def login(window: MainWindow, username="felix", password="111111") -> None:
    window.field_username.setText(username)
    window.field_sciper.setText(password)
    window.button_login.click()


def run_cv(window: MainWindow, duration="0.05") -> None:
    panel = window.measurement_panel
    panel.menu_measurement.setCurrentIndex(1)
    panel.field_cv_interval.setText("0.002")
    panel.field_cv_duration.setText(duration)
    panel.button_run_cv.click()


# --- launch and initial state ---


def test_emulated_launch(tmp_path: Path) -> None:
    settings = SystemSettings.model_validate(settings_dict(tmp_path))
    write_users(tmp_path / "users.txt", USERS)

    app, window = launch(
        settings, users_file=tmp_path / "users.txt", threaded=False
    )

    assert window.isVisible()
    assert window.windowTitle() == "IVLab"
    assert not window.button_initialize.isEnabled()
    assert window.stack_login.currentIndex() == 0
    window.close()


def test_light_menu_generated_from_lamp_levels(tmp_path: Path) -> None:
    window = make_window(tmp_path)

    menu = window.light_panel.menu_light_level
    labels = [menu.itemText(i) for i in range(menu.count())]

    # legacy __main__ formatting: '{:4.1f} % Sun' and 'Dark' below 0.01
    assert "100.0 % Sun" in labels
    assert "50.0 % Sun" in labels
    assert "Dark" in labels
    assert not window.light_panel.manual_mode


def test_manual_lamp_uses_manual_mode(tmp_path: Path) -> None:
    window = make_window(
        tmp_path, lamp={"brand": "manual", "model": "manual", "lightLevelDict": None}
    )

    assert window.light_panel.manual_mode


# --- login / logout flow ---


def test_login_enables_widgets_and_calibration_permission(tmp_path: Path) -> None:
    window = make_window(tmp_path)

    login(window, "felix", "111111")

    assert window.system.user.username == "felix"
    assert window.button_initialize.isEnabled()
    assert window.field_cell_name.isEnabled()
    assert window.stack_login.currentIndex() == 1
    assert window.label_logged_in_user.text() == "felix"
    # felix may calibrate (legacy hardcoded permission)
    assert window.measurement_panel.menu_measurement.count() == 5


def test_login_without_calibration_permission(tmp_path: Path) -> None:
    window = make_window(tmp_path)

    login(window, "alice", "333333")

    assert window.measurement_panel.menu_measurement.count() == 4


def test_failed_login_shows_legacy_error(tmp_path: Path) -> None:
    window = make_window(tmp_path)

    login(window, "felix", "wrong")

    assert window.error_log[-1] == "Sciper not valid for user felix"
    assert window.stack_login.currentIndex() == 0


def test_logout_resets_ui(tmp_path: Path) -> None:
    window = make_window(tmp_path)
    login(window)
    window.button_initialize.click()  # hardware init

    window._do_logout("done for today")

    assert window.stack_login.currentIndex() == 0
    assert not window.button_initialize.isEnabled()
    assert not window.measurement_panel.group_measurement.isEnabled()
    assert window.status_bar.currentMessage() == "Please Log In"


# --- hardware init ---


def test_initialize_hardware_enables_measurement_groups(tmp_path: Path) -> None:
    window = make_window(tmp_path)
    login(window)

    assert not window.measurement_panel.group_measurement.isEnabled()
    window.button_initialize.click()

    assert window.measurement_panel.group_measurement.isEnabled()
    assert window.light_panel.isEnabled()
    assert window.system.smu.is_connected()


# --- measurements through the real click path ---


def test_cv_run_via_buttons_updates_plots_and_state(tmp_path: Path) -> None:
    window = make_window(tmp_path)
    login(window)
    window.button_initialize.click()

    run_cv(window)

    assert "CV" in window.system.results
    assert len(window.system.results["CV"].time) >= 2
    # plot received data and the run state was restored
    assert window.plot_panel._curve_constant_v is not None
    assert window.measurement_panel.button_run_cv.isEnabled()
    assert window.button_save_data.isEnabled()


def test_dark_jv_run_updates_results_grid(tmp_path: Path) -> None:
    window = make_window(tmp_path)
    login(window)
    window.button_initialize.click()

    panel = window.measurement_panel
    panel.menu_measurement.setCurrentIndex(0)
    window.light_panel.menu_light_level.setCurrentIndex(
        window.light_panel.menu_light_level.findText("Dark")
    )
    panel.field_iv_v_step.setText("50.0")  # 50 mV steps
    panel.field_iv_sweep_rate.setText("100000")
    panel.menu_sweep_direction.setCurrentIndex(0)
    panel.field_iv_min_v.setText("0.0")
    panel.field_iv_max_v.setText("0.4")
    panel.button_run_iv.click()

    assert "JV" in window.system.results
    # dark scan: no metrics, grid shows dashes
    assert window.plot_panel.field_jsc.value.text() == "-----"


def test_save_data_via_button_writes_file(tmp_path: Path) -> None:
    window = make_window(tmp_path)
    login(window)
    window.button_initialize.click()
    run_cv(window)

    window.field_cell_name.setText("My Best Cell")
    window.button_save_data.click()

    saved = list((tmp_path / "data_root" / "felix" / "data").glob("*.csv"))
    assert len(saved) == 1
    assert saved[0].name.startswith("My Best Cell_CV_")


def test_calibration_flow_fills_field_and_saves_settings(tmp_path: Path) -> None:
    window = make_window(tmp_path, SMU={"useReferenceDiode": True})
    window.system.smu.reference_diode_parallel = True
    login(window, "felix", "111111")
    window.button_initialize.click()

    panel = window.measurement_panel
    panel.menu_measurement.setCurrentIndex(4)
    cal = panel.calibration_panel
    cal.field_diode_reference_current.setText("4.00")  # mA
    cal.field_interval.setText("0.002")
    cal.field_duration.setText("0.04")
    cal.button_run.click()

    # the derived current (~4 mA) landed in the field, in mA
    assert float(cal.field_reference_cell_current.text()) == pytest.approx(4.0, rel=0.05)
    assert cal.button_save.isEnabled()

    cal.button_save.click()
    saved = json.loads((tmp_path / "system_settings.json").read_text())
    assert saved["IVsys"]["fullSunReferenceCurrent"] == pytest.approx(0.004, rel=0.05)


# --- per-user GUI configuration (legacy load/saveSettingsFile) ---


def test_user_config_round_trip(tmp_path: Path) -> None:
    window = make_window(tmp_path)
    login(window)
    window.measurement_panel.field_iv_v_step.setText("12.5")
    window.measurement_panel.menu_nwire.setCurrentIndex(1)  # 4 wire

    window._do_logout("")  # saves the config, then resets fields
    assert window.measurement_panel.field_iv_v_step.text() == "5.0"

    config_path = tmp_path / "data_root" / "felix" / "IVLab_config.json"
    assert config_path.exists()

    login(window)  # reloads the config
    assert window.measurement_panel.field_iv_v_step.text() == "12.5"
    assert window.measurement_panel.menu_nwire.currentText() == "4 wire"
