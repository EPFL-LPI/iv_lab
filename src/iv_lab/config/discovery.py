"""Locate machine-specific config files when iv_lab runs as an installed package.

When the app is installed with ``pip`` (rather than run from a checkout) the
settings and users files live outside the package. These helpers find them via
an ordered search so ``iv-lab`` works regardless of the working directory:

1. an explicit path (``--settings`` / ``--users``),
2. the ``IV_LAB_SETTINGS`` environment variable (settings only),
3. the working-directory ``config/`` folder (the original behavior),
4. a per-user config directory: ``%APPDATA%\\iv_lab`` on Windows,
   ``$XDG_CONFIG_HOME/iv_lab`` (or ``~/.config/iv_lab``) elsewhere.
"""

from __future__ import annotations

import os
from pathlib import Path

from .settings import DEFAULT_SETTINGS_FILENAME

#: Environment variable holding an explicit path to the settings file.
SETTINGS_ENV_VAR = "IV_LAB_SETTINGS"

#: Application subdirectory inside the per-user config directory.
APP_DIR_NAME = "iv_lab"


def _is_windows() -> bool:
    return os.name == "nt"


def user_config_dir() -> Path:
    """Return the per-user config directory for iv_lab (platform-appropriate)."""
    if _is_windows():
        base = os.environ.get("APPDATA")
        root = Path(base) if base else Path.home() / "AppData" / "Roaming"
    else:
        base = os.environ.get("XDG_CONFIG_HOME")
        root = Path(base) if base else Path.home() / ".config"
    return root / APP_DIR_NAME


def resolve_settings_file(explicit: str | None) -> Path:
    """Locate the settings file using the ordered search above.

    Falls back to the working-directory default (``config/system_settings.toml``,
    which may not exist) so a missing-file error names a familiar location.
    """
    if explicit is not None:
        return Path(explicit)
    env = os.environ.get(SETTINGS_ENV_VAR)
    if env:
        return Path(env)
    cwd_default = Path(DEFAULT_SETTINGS_FILENAME)
    if cwd_default.exists():
        return cwd_default
    user = user_config_dir() / Path(DEFAULT_SETTINGS_FILENAME).name
    if user.exists():
        return user
    return cwd_default
