"""Tests for settings-file discovery when running as an installed package."""

from pathlib import Path

from iv_lab.config.discovery import (
    DEFAULT_SETTINGS_FILENAME,
    SETTINGS_ENV_VAR,
    resolve_settings_file,
    user_config_dir,
)


def test_explicit_path_wins(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv(SETTINGS_ENV_VAR, str(tmp_path / "env.toml"))
    explicit = tmp_path / "explicit.toml"

    assert resolve_settings_file(str(explicit)) == explicit


def test_env_var_used_when_no_explicit(monkeypatch, tmp_path: Path) -> None:
    env_path = tmp_path / "from_env.toml"
    monkeypatch.setenv(SETTINGS_ENV_VAR, str(env_path))

    assert resolve_settings_file(None) == env_path


def test_cwd_config_used_when_present(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv(SETTINGS_ENV_VAR, raising=False)
    monkeypatch.chdir(tmp_path)
    cwd_file = tmp_path / DEFAULT_SETTINGS_FILENAME
    cwd_file.parent.mkdir(parents=True)
    cwd_file.write_text("")

    assert resolve_settings_file(None) == Path(DEFAULT_SETTINGS_FILENAME)


def test_user_config_dir_fallback(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv(SETTINGS_ENV_VAR, raising=False)
    # an empty working directory so the CWD candidate does not exist
    empty_cwd = tmp_path / "empty"
    empty_cwd.mkdir()
    monkeypatch.chdir(empty_cwd)

    user_dir = tmp_path / "user_cfg"
    user_file = user_dir / "system_settings.toml"
    user_dir.mkdir()
    user_file.write_text("")
    monkeypatch.setattr("iv_lab.config.discovery.user_config_dir", lambda: user_dir)

    assert resolve_settings_file(None) == user_file


def test_falls_back_to_cwd_default_when_nothing_found(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv(SETTINGS_ENV_VAR, raising=False)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "iv_lab.config.discovery.user_config_dir", lambda: tmp_path / "nonexistent"
    )

    # nothing exists: returns the working-directory default for a familiar error
    assert resolve_settings_file(None) == Path(DEFAULT_SETTINGS_FILENAME)


def test_user_config_dir_windows(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("iv_lab.config.discovery._is_windows", lambda: True)
    monkeypatch.setenv("APPDATA", str(tmp_path / "Roaming"))

    assert user_config_dir() == tmp_path / "Roaming" / "iv_lab"


def test_user_config_dir_posix_xdg(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("iv_lab.config.discovery._is_windows", lambda: False)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))

    assert user_config_dir() == tmp_path / "xdg" / "iv_lab"
