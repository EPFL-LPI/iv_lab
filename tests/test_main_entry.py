"""Tests for the thin command-line entry point."""

import json
from pathlib import Path

from iv_lab.hardware.lamp.drivers.emulated import EmulatedLamp
from iv_lab.hardware.smu.drivers.emulated import EmulatedSMU
from iv_lab.main import main, parse_args
from iv_lab.services import write_users


def write_settings(tmp_path: Path, emulate: bool) -> Path:
    settings = {
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
        "lamp": {"brand": "manual", "model": "manual", "emulate": emulate},
        "SMU": {
            "brand": "Keithley",
            "model": "2602",
            "visa_address": "GPIB0::24::INSTR",
            "visa_library": "visa64.dll",
            "emulate": emulate,
        },
    }
    path = tmp_path / "system_settings.json"
    path.write_text(json.dumps(settings))
    return path


def test_parse_args_defaults() -> None:
    args = parse_args([])

    assert args.settings == "system_settings.json"
    assert args.users is None
    assert args.logo == "EPFL_Logo.png"
    assert not args.emulate


def test_main_launches_in_emulation(tmp_path: Path) -> None:
    settings_path = write_settings(tmp_path, emulate=True)
    users_path = tmp_path / "users.txt"
    write_users(users_path, {"felix": "111111"})

    exit_code = main(
        ["--settings", str(settings_path), "--users", str(users_path)],
        exec_app=False,
    )

    assert exit_code == 0


def test_emulate_flag_forces_emulated_hardware(tmp_path: Path) -> None:
    # settings configure real hardware; --emulate must override
    settings_path = write_settings(tmp_path, emulate=False)
    users_path = tmp_path / "users.txt"
    write_users(users_path, {"felix": "111111"})

    from iv_lab.gui import app as app_module

    captured = {}
    original_launch = app_module.launch

    def capturing_launch(settings, **kwargs):
        app, window = original_launch(settings, **kwargs)
        captured["window"] = window
        return app, window

    app_module.launch = capturing_launch
    try:
        exit_code = main(
            [
                "--settings",
                str(settings_path),
                "--users",
                str(users_path),
                "--emulate",
            ],
            exec_app=False,
        )
    finally:
        app_module.launch = original_launch

    assert exit_code == 0
    system = captured["window"].system
    assert isinstance(system.smu, EmulatedSMU)
    assert isinstance(system.lamp, EmulatedLamp)


def test_missing_settings_file_returns_error(tmp_path: Path, capsys) -> None:
    exit_code = main(
        ["--settings", str(tmp_path / "nope.json")], exec_app=False
    )

    assert exit_code == 1
    assert "settings file not found" in capsys.readouterr().err
