"""GUI application assembly.

Builds the ``QApplication``, the core system, and the main window; the
thin command-line entry point lives in ``iv_lab.main`` (step 15 of
docs/MIGRATION.md).
"""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from iv_lab.config import SystemSettings
from iv_lab.core import IVLabSystem
from iv_lab.gui.main_window import MainWindow


def create_application(argv: list[str] | None = None) -> QApplication:
    """Return the process-wide ``QApplication`` (created on demand)."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(argv if argv is not None else sys.argv)
    return app


def launch(settings: SystemSettings, **system_kwargs) -> tuple[QApplication, MainWindow]:
    """Create the application, core system, and main window, and show it.

    ``system_kwargs`` are forwarded to :class:`IVLabSystem`
    (``settings_file``, ``users_file``, ``logo_path``, ``threaded``).
    """
    app = create_application()
    system = IVLabSystem(settings, **system_kwargs)
    window = MainWindow(system)
    window.show()
    return app, window
