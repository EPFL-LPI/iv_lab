"""Log-off confirmation dialog with the logbook entry (legacy
``LogOffDialog``).

Unlike legacy (which emitted the logout signal itself), the dialog just
collects the optional logbook text; the main window reads
:meth:`log_book_entry` after ``exec()`` accepts.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class LogOffDialog(QDialog):
    """Confirm logout and collect the logbook entry."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Confirm Log Off")

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        self.text_edit = QTextEdit()
        self.text_edit.setMaximumHeight(100)

        layout = QVBoxLayout()
        layout.addWidget(QLabel("Logbook Entry:"))
        layout.addWidget(self.text_edit)
        layout.addWidget(buttons)
        self.setLayout(layout)

    def log_book_entry(self) -> str:
        """The text the user entered."""
        return self.text_edit.toPlainText()
