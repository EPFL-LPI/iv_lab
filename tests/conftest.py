"""Shared test setup.

A single offscreen QApplication for the whole session: the GUI tests
need QtWidgets, and Qt allows only one application object per process
(modules using QCoreApplication.instance() pick this one up).
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

_app = QApplication.instance() or QApplication([])
