"""Calibration form panel (legacy calibration page of the measurement
stack in ``IVLab/IV_gui.py``)."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtGui import QDoubleValidator
from PySide6.QtWidgets import (
    QGridLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


def _double_field(text: str) -> QLineEdit:
    field = QLineEdit(text)
    field.setValidator(QDoubleValidator())
    return field


class CalibrationPanel(QWidget):
    """Reference diode calibration form (legacy defaults preserved)."""

    run_clicked = Signal()
    abort_clicked = Signal()
    save_clicked = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMaximumWidth(300)

        #: Certified current of the calibration (control) diode in mA.
        self.field_diode_reference_current = _double_field("1.00")
        self.field_stabilization_time = _double_field("5.0")
        self.field_interval = _double_field("0.50")
        self.field_duration = _double_field("60.0")

        self.button_run = QPushButton("Run Calibration")
        self.button_run.clicked.connect(self.run_clicked)
        self.button_abort = QPushButton("Abort Measurement")
        self.button_abort.clicked.connect(self.abort_clicked)
        self.button_abort.setEnabled(False)

        #: Derived reference diode current in mA (filled after a run).
        self.field_reference_cell_current = _double_field("1.00")
        self.button_save = QPushButton("Save Calibration")
        self.button_save.clicked.connect(self.save_clicked)
        self.button_save.setEnabled(False)

        fields = QGridLayout()
        fields.addWidget(QLabel("Calibration Diode Iref"), 0, 0)
        fields.addWidget(self.field_diode_reference_current, 0, 1)
        fields.addWidget(QLabel("mA"), 0, 2)
        fields.addWidget(QLabel("Stabilization Time"), 1, 0)
        fields.addWidget(self.field_stabilization_time, 1, 1)
        fields.addWidget(QLabel("sec"), 1, 2)
        fields.addWidget(QLabel("Meas Interval"), 2, 0)
        fields.addWidget(self.field_interval, 2, 1)
        fields.addWidget(QLabel("sec"), 2, 2)
        fields.addWidget(QLabel("Meas Duration"), 3, 0)
        fields.addWidget(self.field_duration, 3, 1)
        fields.addWidget(QLabel("sec"), 3, 2)

        reference = QGridLayout()
        reference.addWidget(QLabel("Reference Diode Iref"), 0, 0)
        reference.addWidget(self.field_reference_cell_current, 0, 1)
        reference.addWidget(QLabel("mA"), 0, 2)

        layout = QVBoxLayout()
        layout.addLayout(fields)
        layout.addWidget(self.button_run)
        layout.addWidget(self.button_abort)
        layout.addLayout(reference)
        layout.addWidget(self.button_save)
        self.setLayout(layout)

    def set_reference_current(self, current_ma: float) -> None:
        """Show the derived current (legacy ``setCalibrationReferenceCurrent``,
        ``{:5.3f}`` in mA)."""
        self.field_reference_cell_current.setText(f"{current_ma:5.3f}")

    def reference_current_a(self) -> float:
        """Field value converted to A (legacy ``saveCalibration``)."""
        return abs(float(self.field_reference_cell_current.text()) / 1000.0)

    def reset_to_defaults(self) -> None:
        """Legacy ``setAllFieldsToDefault`` calibration entries."""
        self.button_save.setEnabled(False)
        self.field_reference_cell_current.setText("1.00")
        self.field_stabilization_time.setText("5.0")
        self.field_interval.setText("0.5")
        self.field_duration.setText("60.0")
