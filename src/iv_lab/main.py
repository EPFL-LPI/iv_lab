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
from typing import Optional

from iv_lab.config import DEFAULT_SETTINGS_FILENAME, load_settings
from iv_lab.services.auth import USERS_FILENAME

#: Legacy report logo file (in the working directory, as in legacy).
DEFAULT_LOGO_FILENAME = "EPFL_Logo.png"


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="iv_lab",
        description="IV characterization lab application (EPFL LPI).",
    )
    parser.add_argument(
        "--settings",
        default=DEFAULT_SETTINGS_FILENAME,
        help="system settings file (default: %(default)s in the working directory)",
    )
    parser.add_argument(
        "--users",
        default=USERS_FILENAME,
        help="scrambled user table (default: %(default)s in the working directory)",
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
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None, *, exec_app: bool = True) -> int:
    """Run the application; returns the process exit code.

    ``exec_app=False`` skips the Qt event loop (used by tests).
    """
    args = parse_args(argv)

    try:
        settings = load_settings(args.settings)
    except FileNotFoundError:
        print(f"ERROR: settings file not found: {args.settings}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"ERROR: could not load settings: {exc}", file=sys.stderr)
        return 1

    if args.emulate:
        settings.SMU.emulate = True
        settings.lamp.emulate = True
        if settings.arduino is not None:
            settings.arduino.emulate = True

    from iv_lab.gui.app import launch

    app, window = launch(
        settings,
        settings_file=args.settings,
        users_file=args.users,
        logo_path=args.logo,
    )

    if not exec_app:
        window.close()
        return 0
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
