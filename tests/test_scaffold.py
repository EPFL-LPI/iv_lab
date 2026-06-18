"""Tests for `iv-lab --init` config scaffolding."""

from pathlib import Path

from iv_lab.config.settings import load_settings
from iv_lab.main import main
from iv_lab.scaffold import scaffold_user_config, settings_template
from iv_lab.services.auth import GENERIC_PASSWORD, GENERIC_USERNAME, load_users


def test_bundled_template_is_emulation_ready(tmp_path: Path) -> None:
    path = tmp_path / "system_settings.toml"
    path.write_text(settings_template(), encoding="utf-8")

    settings = load_settings(path)

    assert settings.SMU.emulate is True
    assert settings.lamp.emulate is True
    assert settings.IVsys.calibrationDiodes == {"Si1812": 1.541}


def test_scaffold_creates_both_files(tmp_path: Path) -> None:
    lines = scaffold_user_config(tmp_path)

    settings_path = tmp_path / "system_settings.toml"
    users_path = tmp_path / "users.txt"
    assert settings_path.exists()
    assert users_path.exists()
    assert "created system_settings.toml" in "\n".join(lines)

    # the seeded settings load and the generic account is present
    assert load_settings(settings_path).SMU.emulate is True
    assert load_users(users_path)[GENERIC_USERNAME] == GENERIC_PASSWORD


def test_scaffold_does_not_overwrite(tmp_path: Path) -> None:
    settings_path = tmp_path / "system_settings.toml"
    settings_path.write_text("# my edited config\n", encoding="utf-8")

    lines = scaffold_user_config(tmp_path)

    assert settings_path.read_text(encoding="utf-8") == "# my edited config\n"
    assert "kept    system_settings.toml" in "\n".join(lines)


def test_init_flag_scaffolds_user_config(tmp_path, monkeypatch, capsys) -> None:
    # user_config_dir() reads APPDATA on Windows / XDG elsewhere; point both at tmp
    monkeypatch.setenv("APPDATA", str(tmp_path))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

    exit_code = main(["--init"], exec_app=False)

    assert exit_code == 0
    target = tmp_path / "iv_lab"
    assert (target / "system_settings.toml").exists()
    assert (target / "users.txt").exists()
    assert "Config directory" in capsys.readouterr().out
