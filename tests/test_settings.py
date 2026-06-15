import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from iv_lab.config import SystemSettings, load_settings

REPO_ROOT = Path(__file__).resolve().parent.parent

MINIMAL_SETTINGS = {
    "computer": {
        "hardware": "Test PC",
        "os": "Windows 11",
        "basePath": "C:\\IVLab\\data",
        "sdPath": "",
    },
    "IVsys": {
        "sysName": "IVLab",
        "fullSunReferenceCurrent": 0.006318,
        "calibrationDateTime": "Wed Jun  8 16:07:18 2022",
        "referenceDiodeImax": 0.005,
    },
    "lamp": {
        "brand": "manual",
        "model": "manual",
        "emulate": False,
    },
    "SMU": {
        "brand": "Keithley",
        "model": "2401",
        "visa_address": "ASRL2",
        "visa_library": "C:\\Windows\\System32\\visa32.dll",
        "emulate": False,
    },
}


def write_settings(tmp_path: Path, data: dict) -> Path:
    path = tmp_path / "system_settings.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_load_minimal_settings(tmp_path: Path) -> None:
    settings = load_settings(write_settings(tmp_path, MINIMAL_SETTINGS))

    assert settings.computer.hardware == "Test PC"
    assert settings.computer.sdPath == ""
    assert settings.IVsys.sysName == "IVLab"
    assert settings.IVsys.fullSunReferenceCurrent == pytest.approx(0.006318)
    assert settings.lamp.brand == "manual"
    assert settings.SMU.model == "2401"
    assert settings.arduino is None


def test_ivsys_legacy_defaults(tmp_path: Path) -> None:
    settings = load_settings(write_settings(tmp_path, MINIMAL_SETTINGS))

    # defaults from legacy system.__init__
    assert settings.IVsys.saveDataAutomatic is False
    assert settings.IVsys.checkVOCBeforeScan is True
    assert settings.IVsys.firstPointDwellTime == 5.0
    assert settings.IVsys.MPPVoltageStepInitial == 0.002
    assert settings.IVsys.MPPVoltageStepMax == 0.002
    assert settings.IVsys.MPPVoltageStepMin == 0.001


def test_smu_legacy_defaults(tmp_path: Path) -> None:
    settings = load_settings(write_settings(tmp_path, MINIMAL_SETTINGS))

    # defaults from legacy SMU.__init__
    assert settings.SMU.referenceDiodeSenseMode == "2 wire"
    assert settings.SMU.autorange is True
    assert settings.SMU.measSpeed == "normal"
    assert settings.SMU.useReferenceDiode is True


def test_extra_legacy_fields_are_allowed(tmp_path: Path) -> None:
    data = json.loads(json.dumps(MINIMAL_SETTINGS))
    data["IVsys"]["someLegacyKey"] = 42
    data["SMU"]["anotherLegacyKey"] = "value"
    data["futureSection"] = {"a": 1}

    settings = load_settings(write_settings(tmp_path, data))

    assert settings.IVsys.someLegacyKey == 42
    assert settings.SMU.anotherLegacyKey == "value"
    assert settings.futureSection == {"a": 1}


def test_missing_required_field_gives_useful_error(tmp_path: Path) -> None:
    data = json.loads(json.dumps(MINIMAL_SETTINGS))
    del data["IVsys"]["fullSunReferenceCurrent"]

    with pytest.raises(ValidationError) as excinfo:
        load_settings(write_settings(tmp_path, data))

    assert "fullSunReferenceCurrent" in str(excinfo.value)


def test_light_level_dict_keys_coerced_to_float(tmp_path: Path) -> None:
    # JSON only allows string keys; legacy __main__ converts them to float.
    data = json.loads(json.dumps(MINIMAL_SETTINGS))
    data["lamp"] = {
        "brand": "Trinamic",
        "model": "TMCM-1260",
        "emulate": False,
        "lightLevelDict": {"100": 17, "55": 77, "1.2": 197, "0": 257},
    }

    settings = load_settings(write_settings(tmp_path, data))

    assert settings.lamp.lightLevelDict == {100.0: 17, 55.0: 77, 1.2: 197, 0.0: 257}
    assert all(isinstance(k, float) for k in settings.lamp.lightLevelDict)


def test_wavelabs_recipe_values_stay_strings(tmp_path: Path) -> None:
    data = json.loads(json.dumps(MINIMAL_SETTINGS))
    data["lamp"] = {
        "brand": "Wavelabs",
        "model": "Sinus70",
        "display name": "Sinus70 (Wavelabs)",
        "emulate": False,
        "lightLevelDict": {"100.0": "1 sun, 1 h", "0.0": "dummy"},
    }

    settings = load_settings(write_settings(tmp_path, data))

    assert settings.lamp.lightLevelDict[100.0] == "1 sun, 1 h"
    assert settings.lamp.display_name == "Sinus70 (Wavelabs)"


def test_lamp_display_name_generated_when_absent(tmp_path: Path) -> None:
    # legacy syst_param.__init__ builds 'display name' from brand and model
    settings = load_settings(write_settings(tmp_path, MINIMAL_SETTINGS))

    assert settings.lamp.display_name == "manual manual"


def test_non_manual_lamp_requires_light_level_dict(tmp_path: Path) -> None:
    data = json.loads(json.dumps(MINIMAL_SETTINGS))
    data["lamp"] = {"brand": "Trinamic", "model": "TMCM-1260", "emulate": False}

    with pytest.raises(ValidationError) as excinfo:
        load_settings(write_settings(tmp_path, data))

    assert "lightLevelDict" in str(excinfo.value)


def test_arduino_section_is_parsed_when_present(tmp_path: Path) -> None:
    data = json.loads(json.dumps(MINIMAL_SETTINGS))
    data["arduino"] = {
        "brand": "Arduino",
        "model": "Uno",
        "visa_address": "ASRL1::INSTR",
        "visa_library": "C:\\Windows\\System32\\visa32.dll",
        "emulate": False,
    }

    settings = load_settings(write_settings(tmp_path, data))

    assert settings.arduino is not None
    assert settings.arduino.brand == "Arduino"
    assert settings.arduino.visa_address == "ASRL1::INSTR"


@pytest.mark.parametrize(
    "template",
    [
        "system_settings_oldIV.json",
        "system_settings_Sinus70-1.json",
        "system_settings_OrielIV.json",
    ],
)
def test_committed_legacy_templates_load(template: str) -> None:
    settings = load_settings(REPO_ROOT / "IVLab" / template)

    assert isinstance(settings, SystemSettings)
    assert settings.IVsys.sysName
    assert settings.SMU.brand == "Keithley"
