"""Tests for the core system orchestrator (headless, emulated hardware)."""

import json
from pathlib import Path

import pytest
from PySide6.QtCore import QCoreApplication, QEventLoop, QTimer

from iv_lab.config import SystemSettings, load_settings
from iv_lab.core import IVLabSystem
from iv_lab.data.results import ConstantVoltageResults
from iv_lab.hardware.arduino.drivers.emulated import EmulatedArduino
from iv_lab.hardware.lamp.drivers.emulated import EmulatedLamp
from iv_lab.hardware.smu.base import SMUChannel
from iv_lab.hardware.smu.drivers.emulated import EmulatedSMU
from iv_lab.services import write_users

_app = QCoreApplication.instance() or QCoreApplication([])

USERS = {"felix": "111111", "alice": "333333", "user": "123456"}


def settings_dict(tmp_path: Path, **overrides) -> dict:
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
        "lamp": {"brand": "manual", "model": "manual", "emulate": True},
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


def make_system(tmp_path: Path, *, overrides=None, **kwargs) -> IVLabSystem:
    settings = SystemSettings.model_validate(settings_dict(tmp_path, **(overrides or {})))
    users_file = tmp_path / "users.txt"
    if not users_file.exists():
        write_users(users_file, USERS)
    kwargs.setdefault("threaded", False)
    kwargs.setdefault("settings_file", tmp_path / "system_settings.json")
    system = IVLabSystem(settings, users_file=users_file, **kwargs)
    # emulated drivers: no delays in tests
    system.smu.integration_delay = 0.0
    system.smu.meas_period_min = 0.0
    return system


class Records:
    """Collects the GUI-facing system signals."""

    def __init__(self, system: IVLabSystem) -> None:
        self.status: list[str] = []
        self.errors: list[str] = []
        self.data: list[dict] = []
        self.finished: list[object] = []
        self.hardware: list[bool] = []
        self.calibrations: list[float] = []

        system.status_message.connect(self.status.append)
        system.error_message.connect(self.errors.append)
        system.data_updated.connect(self.data.append)
        system.measurement_finished.connect(self.finished.append)
        system.hardware_ready.connect(self.hardware.append)
        system.calibration_ready.connect(self.calibrations.append)


def cv_params(**overrides) -> dict:
    params = {
        "light_int": 100.0,
        "set_voltage": 0.2,
        "interval": 0.002,
        "duration": 0.04,
        "Imax": 0.01,
        "Vmax": 2.0,
        "Dwell": 0.0,
        "Nwire": "2 wire",
        "active_area": 0.16,
        "cell_name": "test cell",
    }
    params.update(overrides)
    return params


# --- construction (legacy system.__init__) ---


def test_system_creates_emulated_hardware_via_factories(tmp_path: Path) -> None:
    system = make_system(tmp_path)

    assert isinstance(system.smu, EmulatedSMU)
    assert isinstance(system.lamp, EmulatedLamp)
    assert system.arduino is None  # not IV_Old

    # IVsys values applied to the SMU (legacy)
    assert system.smu.full_sun_reference_current == 0.004
    assert system.smu.calibration_datetime == "Wed Jun  8 16:07:18 2022"
    assert system.smu.reference_diode_imax == 0.005
    # 2602 outside IV_Old: parallel reference measurement
    assert system.smu.reference_diode_parallel


def test_parallel_reference_rules(tmp_path: Path) -> None:
    system_2401 = make_system(tmp_path, overrides={"SMU": {"model": "2401"}})
    assert not system_2401.smu.reference_diode_parallel

    # IV_Old without an arduino section fails like legacy
    settings = settings_dict(tmp_path)
    settings["IVsys"]["sysName"] = "IV_Old"
    with pytest.raises(ValueError, match="no arduino settings dictionary"):
        IVLabSystem(
            SystemSettings.model_validate(settings),
            users_file=tmp_path / "users.txt",
            threaded=False,
        )


def test_iv_old_creates_arduino(tmp_path: Path) -> None:
    settings = settings_dict(tmp_path)
    settings["IVsys"]["sysName"] = "IV_Old"
    settings["arduino"] = {
        "brand": "Arduino",
        "model": "Uno",
        "visa_address": "ASRL1::INSTR",
        "emulate": True,
    }
    write_users(tmp_path / "users.txt", USERS)

    system = IVLabSystem(
        SystemSettings.model_validate(settings),
        users_file=tmp_path / "users.txt",
        threaded=False,
    )

    assert isinstance(system.arduino, EmulatedArduino)
    assert not system.smu.reference_diode_parallel  # IV_Old rule


# --- hardware init ---


def test_hardware_init_connects_everything(tmp_path: Path) -> None:
    system = make_system(tmp_path)
    records = Records(system)

    assert system.hardware_init()

    assert system.smu.is_connected()
    assert system.lamp.is_connected()
    assert records.hardware == [True]


def test_hardware_init_failure_emits_legacy_message(tmp_path: Path) -> None:
    system = make_system(tmp_path)
    records = Records(system)

    def broken_open():
        raise ValueError("no VISA resource")

    system.smu._open = broken_open

    assert not system.hardware_init()
    assert records.hardware == [False]
    assert "Error initializing keithley sourcemeter" in records.errors[0]
    assert "no VISA resource" in records.errors[0]


# --- login / logout ---


def test_login_logout_with_logbook(tmp_path: Path) -> None:
    system = make_system(tmp_path)
    records = Records(system)

    assert system.login("Felix", "111111")
    assert system.user.username == "felix"
    assert "User set to: felix" in records.status

    system.logout("all good")
    assert system.user is None
    assert "Please Log In" in records.status

    log_lines = (tmp_path / "sd" / "ivlablog.txt").read_text().splitlines()
    assert log_lines[0].endswith("user felix logged on")
    assert log_lines[1].endswith("user comment: all good")
    assert log_lines[2].endswith("user felix logged off")


def test_failed_login_emits_legacy_errors(tmp_path: Path) -> None:
    system = make_system(tmp_path)
    records = Records(system)

    assert not system.login("nobody", "x")
    assert records.errors[-1] == "Username not valid"

    assert not system.login("felix", "wrong")
    assert records.errors[-1] == "Sciper not valid for user felix"


def test_missing_user_table_blocks_login(tmp_path: Path) -> None:
    settings = SystemSettings.model_validate(settings_dict(tmp_path))
    system = IVLabSystem(
        settings, users_file=tmp_path / "missing_users.txt", threaded=False
    )
    records = Records(system)

    assert system.user_table_error is not None
    assert not system.login("felix", "111111")
    assert "User table corrupted or absent" in records.errors[0]


def test_logout_clears_results_and_disconnects(tmp_path: Path) -> None:
    system = make_system(tmp_path)
    system.hardware_init()
    system.login("felix", "111111")
    system.results["CV"] = ConstantVoltageResults()

    system.logout()

    assert system.results == {}
    assert not system.smu.is_connected()
    assert not system.lamp.is_connected()


# --- measurements (synchronous mode) ---


def test_run_measurement_stores_result_and_reemits_signals(tmp_path: Path) -> None:
    system = make_system(tmp_path)
    system.hardware_init()
    system.login("felix", "111111")
    records = Records(system)

    assert system.run_measurement("Constant Voltage, Measure J", cv_params())

    assert len(records.finished) == 1
    result = records.finished[0]
    assert isinstance(result, ConstantVoltageResults)
    assert system.results["CV"] is result
    assert records.data  # live data re-emitted
    assert "Turning lamp off..." in records.status


def test_unknown_measurement_label_is_rejected(tmp_path: Path) -> None:
    system = make_system(tmp_path)
    records = Records(system)

    assert not system.run_measurement("Bogus Scan", {})
    assert "Unknown measurement type" in records.errors[0]


def test_protocol_error_reaches_error_signal(tmp_path: Path) -> None:
    system = make_system(tmp_path)
    system.hardware_init()
    records = Records(system)

    system.run_measurement(
        "Constant Voltage, Measure J", cv_params(set_voltage=5.0)
    )

    assert any("outside of compliance range" in e for e in records.errors)
    assert records.finished == []
    assert not system.smu.output_enabled(SMUChannel.CELL)


def test_dark_jv_scan_via_core(tmp_path: Path) -> None:
    # dark scan: no metrics computation, so no analysis libraries needed
    system = make_system(tmp_path)
    system.hardware_init()
    records = Records(system)

    params = {
        "light_int": 0.0,
        "start_V": 0.0,
        "stop_V": 0.4,
        "dV": 0.05,
        "sweep_rate": 1000.0,
        "Imax": 0.01,
        "Vmax": 2.0,
        "Dwell": 0.0,
        "Nwire": "2 wire",
        "active_area": 0.16,
        "cell_name": "dark cell",
        "Fwd_current_limit": 0.001,
    }
    assert system.run_measurement("J-V Scan", params)

    assert "JV" in system.results
    assert len(system.results["JV"].voltage) > 1
    assert system.results["JV"].Voc is None


def test_calibration_emits_reference_current(tmp_path: Path) -> None:
    system = make_system(
        tmp_path, overrides={"SMU": {"useReferenceDiode": True}}
    )
    system.hardware_init()
    records = Records(system)

    params = {
        "light_int": 100.0,
        "reference_current": 0.004,
        "interval": 0.002,
        "duration": 0.04,
        "Imax": 0.01,
        "Vmax": 2.0,
        "Dwell": 0.0,
        "Nwire": "2 wire",
    }
    assert system.run_measurement("Calibration", params)

    assert len(records.calibrations) == 1
    assert records.calibrations[0] == pytest.approx(0.004, rel=0.05)
    # calibration results are not stored as saveable scan data
    assert system.results == {}


# --- saving ---


def test_save_data_uses_legacy_messages_and_overwrites_cell_name(
    tmp_path: Path,
) -> None:
    system = make_system(tmp_path)
    system.hardware_init()
    system.login("felix", "111111")
    records = Records(system)

    # nothing measured yet: legacy error message
    assert not system.save_data("J-V Scan", "cellX")
    assert records.errors[-1] == "ERROR: No current J-V Data available to save."

    system.run_measurement("Constant Voltage, Measure J", cv_params())
    assert system.save_data("Constant Voltage, Measure J", "renamed cell")

    saved = list((tmp_path / "data_root" / "felix" / "data").glob("*.csv"))
    assert len(saved) == 1
    assert saved[0].name.startswith("renamed cell_CV_")
    assert system.results["CV"].cell_name == "renamed cell"


def test_auto_save_writes_file_after_run(tmp_path: Path) -> None:
    system = make_system(tmp_path)
    system.hardware_init()
    system.login("felix", "111111")
    system.toggle_auto_save(True)

    system.run_measurement("Constant Voltage, Measure J", cv_params())

    saved = list((tmp_path / "data_root" / "felix" / "data").glob("*.csv"))
    assert len(saved) == 1


# --- calibration persistence ---


def test_save_calibration_updates_settings_file(tmp_path: Path) -> None:
    system = make_system(tmp_path)

    system.save_calibration_to_system_settings({"reference_current": 0.0051})

    assert system.smu.full_sun_reference_current == 0.0051
    assert system.settings.IVsys.fullSunReferenceCurrent == 0.0051

    # the file reloads through the settings loader
    reloaded = load_settings(tmp_path / "system_settings.json")
    assert reloaded.IVsys.fullSunReferenceCurrent == 0.0051
    assert reloaded.IVsys.calibrationDateTime != "Wed Jun  8 16:07:18 2022"


def test_save_calibration_preserves_arduino_section(tmp_path: Path) -> None:
    # legacy dropped the arduino section on rewrite; the migrated code keeps it
    settings = settings_dict(tmp_path)
    settings["IVsys"]["sysName"] = "IV_Old"
    settings["arduino"] = {
        "brand": "Arduino",
        "model": "Uno",
        "visa_address": "ASRL1::INSTR",
        "emulate": True,
    }
    write_users(tmp_path / "users.txt", USERS)
    system = IVLabSystem(
        SystemSettings.model_validate(settings),
        users_file=tmp_path / "users.txt",
        settings_file=tmp_path / "system_settings.json",
        threaded=False,
    )

    system.save_calibration_to_system_settings({"reference_current": 0.005})

    saved = json.loads((tmp_path / "system_settings.json").read_text())
    assert saved["arduino"]["brand"] == "Arduino"


# --- threaded mode ---


def wait_for(signal, timeout_ms: int = 5000) -> list:
    """Run an event loop until ``signal`` fires (or fail on timeout)."""
    loop = QEventLoop()
    received = []

    def on_signal(*args):
        received.append(args)
        loop.quit()

    signal.connect(on_signal)
    QTimer.singleShot(timeout_ms, loop.quit)
    loop.exec()
    assert received, "timed out waiting for signal"
    return received


def test_threaded_measurement_runs_and_can_be_aborted(tmp_path: Path) -> None:
    system = make_system(tmp_path, threaded=True)
    system.hardware_init()
    records = Records(system)

    # long run; abort as soon as live data arrives
    system.data_updated.connect(lambda data: system.abort_run())
    assert system.run_measurement(
        "Constant Voltage, Measure J", cv_params(duration=60.0)
    )
    assert system.is_measurement_running()

    # a second start while running is rejected
    assert not system.run_measurement("Constant Voltage, Measure J", cv_params())
    assert "already running" in records.errors[-1]

    wait_for(system.measurement_finished)

    assert len(records.finished) == 1
    assert len(records.finished[0].time) >= 1
    assert not system.smu.output_enabled(SMUChannel.CELL)

    # let the thread wind down before the next test
    for _ in range(50):
        if not system.is_measurement_running():
            break
        QCoreApplication.processEvents()
