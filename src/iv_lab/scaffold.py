"""Scaffold a per-user config directory for an installed package.

Backs ``iv-lab --init``: creates the per-user config directory and seeds it
with an emulation-ready ``system_settings.toml`` and a starter ``users.txt``
(the generic ``user`` / ``123456`` account). Existing files are never
overwritten, so re-running ``--init`` is safe.
"""

from __future__ import annotations

from importlib import resources
from pathlib import Path

from iv_lab.config import user_config_dir
from iv_lab.services.auth import GENERIC_PASSWORD, GENERIC_USERNAME, write_users

SETTINGS_NAME = "system_settings.toml"
USERS_NAME = "users.txt"


def settings_template() -> str:
    """Return the bundled emulation-ready settings template text."""
    return (
        resources.files("iv_lab.resources")
        .joinpath(SETTINGS_NAME)
        .read_text(encoding="utf-8")
    )


def scaffold_user_config(target: Path | None = None) -> list[str]:
    """Create ``system_settings.toml`` and ``users.txt`` in *target*.

    *target* defaults to the per-user config directory. Existing files are left
    untouched. Returns human-readable status lines describing what happened.
    """
    target = Path(target) if target is not None else user_config_dir()
    target.mkdir(parents=True, exist_ok=True)
    lines = [f"Config directory: {target}"]

    settings_path = target / SETTINGS_NAME
    if settings_path.exists():
        lines.append(f"  kept    {SETTINGS_NAME} (already exists)")
    else:
        settings_path.write_text(settings_template(), encoding="utf-8")
        lines.append(f"  created {SETTINGS_NAME} (emulation-ready; edit for your hardware)")

    users_path = target / USERS_NAME
    if users_path.exists():
        lines.append(f"  kept    {USERS_NAME} (already exists)")
    else:
        write_users(users_path, {GENERIC_USERNAME: GENERIC_PASSWORD})
        lines.append(f"  created {USERS_NAME} (generic '{GENERIC_USERNAME}' login)")

    lines.append("")
    lines.append("Next: edit the settings file for your instruments, then run `iv-lab`.")
    lines.append("Try it now without hardware:  iv-lab --emulate")
    return lines
