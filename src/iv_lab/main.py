"""Application entry point (step 15 of docs/MIGRATION.md).

Thin by design: parse the command line, load the settings, build the
application through :func:`iv_lab.gui.app.launch`, and start the event
loop. No hardware, measurement, or file-writing logic lives here.

Usage::

    python -m iv_lab.main [--settings PATH] [--users PATH]
                          [--logo PATH] [--emulate]

``--emulate`` forces emulation of all configured hardware regardless of
the ``emulate`` flags in the settings file, so the application runs on
machines without instruments or hardware libraries.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from iv_lab.config import resolve_settings_file, user_config_dir
from iv_lab.config.discovery import SETTINGS_ENV_VAR
from iv_lab.config.settings import DEFAULT_SETTINGS_FILENAME, load_settings
from iv_lab.services.auth import USERS_FILENAME, USERS_GENERIC_FILENAME

#: Legacy report logo file (in the working directory, as in legacy).
DEFAULT_LOGO_FILENAME = "EPFL_Logo.png"


def resolve_users_file(explicit: str | None) -> Path:
    """Return the users file to load, applying the fallback chain.

    Priority: explicit --users arg → config/users.txt (working dir) →
    <user config dir>/users.txt → config/users_generic.txt
    """
    if explicit is not None:
        return Path(explicit)
    primary = Path(USERS_FILENAME)
    if primary.exists():
        return primary
    user = user_config_dir() / Path(USERS_FILENAME).name
    if user.exists():
        return user
    return Path(USERS_GENERIC_FILENAME)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="iv_lab",
        description="IV characterization lab application (EPFL LPI).",
    )
    parser.add_argument(
        "--settings",
        default=None,
        help=(
            "system settings file; if omitted the app looks at "
            f"${SETTINGS_ENV_VAR}, then ./{DEFAULT_SETTINGS_FILENAME}, then the "
            "per-user config directory"
        ),
    )
    parser.add_argument(
        "--users",
        default=None,
        help=(
            f"scrambled user table; if omitted the app looks for "
            f"{USERS_FILENAME} first, then falls back to {USERS_GENERIC_FILENAME}"
        ),
    )
    parser.add_argument(
        "--logo",
        default=DEFAULT_LOGO_FILENAME,
        help="logo for the PDF report (default: %(default)s; skipped if absent)",
    )
    parser.add_argument(
        "--emulate",
        action="store_true",
        help="force emulation of all hardware, regardless of the settings file",
    )
    parser.add_argument(
        "--init",
        action="store_true",
        help=(
            "create a starter system_settings.toml and users.txt in the per-user "
            "config directory, then exit (does not overwrite existing files)"
        ),
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None, *, exec_app: bool = True) -> int:
    """Run the application; returns the process exit code.

    ``exec_app=False`` skips the Qt event loop (used by tests).
    """
    args = parse_args(argv)

    if args.init:
        from iv_lab.scaffold import scaffold_user_config

        for line in scaffold_user_config():
            print(line)
        return 0

    settings_path = resolve_settings_file(args.settings)
    try:
        settings = load_settings(settings_path)
    except FileNotFoundError:
        print(f"ERROR: settings file not found: {settings_path}", file=sys.stderr)
        print(
            f"Provide one with --settings PATH, set {SETTINGS_ENV_VAR}, or place it at "
            f"{user_config_dir() / Path(DEFAULT_SETTINGS_FILENAME).name}",
            file=sys.stderr,
        )
        return 1
    except Exception as exc:
        print(f"ERROR: could not load settings: {exc}", file=sys.stderr)
        return 1

    if args.emulate:
        settings.SMU.emulate = True
        settings.lamp.emulate = True
        if settings.arduino is not None:
            settings.arduino.emulate = True

    users_file = resolve_users_file(args.users)

    from iv_lab.gui.app import launch

    app, window = launch(
        settings,
        settings_file=settings_path,
        users_file=users_file,
        logo_path=args.logo,
    )

    if not exec_app:
        window.close()
        return 0
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
