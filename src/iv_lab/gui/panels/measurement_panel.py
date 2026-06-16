"""Measurement panel (legacy ``createMeasurementGroupBox`` plus the SMU
configuration and cell-area widgets).

The measurement type combo selects one of the stacked parameter forms;
``run`` buttons assemble the parameter dicts exactly like the legacy
``runIV`` / ``runConstantV`` / ``runConstantI`` / ``runMaxPP`` /
``runCalibration`` methods (same unit conversions, validations, and
error messages) and emit ``run_requested(label, params)`` with the core
scan-type label. Legacy field defaults are preserved.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Callable, Optional

from PySide6.QtCore import Signal
from PySide6.QtGui import QDoubleValidator
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from .calibration_panel import CalibrationPanel

#: Legacy measurement menu entries, in stack order.
MEASUREMENT_LABELS = [
    "J-V Scan",
    "Constant Voltage, Measure J",
    "Constant Current, Measure V",
    "Maximum Power Point",
    "Calibrate Reference Diode",
]

#: Combo text -> core scan-type label (core uses 'Calibration').
CORE_LABELS = {
    "Calibrate Reference Diode": "Calibration",
}


def sanitize_cell_name(value: str, allow_unicode: bool = False) -> str:
    """Legacy ``sanitizeCellName`` (django slugify variant, 63 chars max)."""
    value = str(value)
    if allow_unicode:
        value = unicodedata.normalize("NFKC", value)
    else:
        value = (
            unicodedata.normalize("NFKD", value)
            .encode("ascii", "ignore")
            .decode("ascii")
        )
    value = re.sub(r"[^\w\s-]", "", value.lower())
    sanitized = re.sub(r"[-\s]+", "-", value).strip("-_")
    if len(sanitized) > 64:
        sanitized = sanitized[0:63]
    return sanitized


def _double_field(text: str) -> QLineEdit:
    field = QLineEdit(text)
    field.setValidator(QDoubleValidator())
    return field


def _grid_rows(rows) -> QGridLayout:
    grid = QGridLayout()
    for row, (label, widget, units) in enumerate(rows):
        grid.addWidget(QLabel(label), row, 0)
        grid.addWidget(widget, row, 1)
        if units:
            grid.addWidget(QLabel(units), row, 2)
    return grid


class MeasurementPanel(QWidget):
    """Measurement selection, parameter forms, SMU config, cell area."""

    #: run_requested(core_label, params) — legacy signal_run* equivalents.
    run_requested = Signal(str, dict)
    abort_requested = Signal()
    #: save_calibration_requested(calibration_params)
    save_calibration_requested = Signal(dict)
    #: validation failures (legacy showErrorMessage)
    validation_error = Signal(str)
    measurement_selected = Signal(int)

    def __init__(
        self,
        light_level_provider: Callable[[], float],
        cell_name_provider: Callable[[], str],
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._light_level = light_level_provider
        self._cell_name = cell_name_provider

        # --- measurement group (legacy createMeasurementGroupBox) ---
        self.group_measurement = QGroupBox("Measurement")
        self.menu_measurement = QComboBox()
        self.menu_measurement.setMaximumWidth(300)
        for label in MEASUREMENT_LABELS:
            self.menu_measurement.addItem(label)
        self.menu_measurement.currentIndexChanged.connect(self._select_measurement)

        # J-V form (legacy defaults)
        self.check_automatic_limits = QCheckBox("Use Automatic Limits (0 - Fwd Limit)")
        self.check_automatic_limits.stateChanged.connect(self._toggle_iv_limits_mode)
        self.field_iv_min_v = _double_field("0.00")
        self._iv_max_v_user = 1.2
        self._iv_fwd_limit_user = 0.0
        self.field_iv_max_v = _double_field(str(self._iv_max_v_user))
        self.field_iv_max_v.textChanged.connect(self._iv_max_v_changed)
        self.label_iv_max_v = QLabel("Maximum Voltage")
        self.label_iv_max_v_units = QLabel("V")
        self.field_iv_v_step = _double_field("5.0")
        self.field_iv_sweep_rate = _double_field("20.0")
        self.field_iv_stabilization = _double_field("5.0")
        self.menu_sweep_direction = QComboBox()
        self.sweep_direction_list = ["Forward", "Reverse"]
        for direction in self.sweep_direction_list:
            self.menu_sweep_direction.addItem(direction)
        self.button_run_iv = QPushButton("Run J-V Scan")
        self.button_run_iv.clicked.connect(self._run_iv)
        self.button_abort_iv = QPushButton("Abort J-V Scan")
        self.button_abort_iv.clicked.connect(self.abort_requested)
        self.button_abort_iv.setEnabled(False)

        iv_grid = QGridLayout()
        iv_grid.addWidget(QLabel("Minimum Voltage"), 0, 0)
        iv_grid.addWidget(self.field_iv_min_v, 0, 1)
        iv_grid.addWidget(QLabel("V"), 0, 2)
        iv_grid.addWidget(self.label_iv_max_v, 1, 0)
        iv_grid.addWidget(self.field_iv_max_v, 1, 1)
        iv_grid.addWidget(self.label_iv_max_v_units, 1, 2)
        iv_grid.addWidget(QLabel("Voltage Step"), 2, 0)
        iv_grid.addWidget(self.field_iv_v_step, 2, 1)
        iv_grid.addWidget(QLabel("mV"), 2, 2)
        iv_grid.addWidget(QLabel("Sweep Rate"), 3, 0)
        iv_grid.addWidget(self.field_iv_sweep_rate, 3, 1)
        iv_grid.addWidget(QLabel("mV/s"), 3, 2)
        iv_grid.addWidget(QLabel("Stabilization Time"), 4, 0)
        iv_grid.addWidget(self.field_iv_stabilization, 4, 1)
        iv_grid.addWidget(QLabel("sec"), 4, 2)
        iv_grid.addWidget(QLabel("Sweep Direction"), 5, 0)
        iv_grid.addWidget(self.menu_sweep_direction, 5, 1)

        panel_iv = QWidget()
        panel_iv.setMaximumWidth(300)
        iv_layout = QVBoxLayout()
        iv_layout.addWidget(self.check_automatic_limits)
        iv_layout.addLayout(iv_grid)
        iv_layout.addWidget(self.button_run_iv)
        iv_layout.addWidget(self.button_abort_iv)
        panel_iv.setLayout(iv_layout)

        # constant voltage form
        self.field_cv_set_v = _double_field("0.00")
        self.field_cv_stabilization = _double_field("5.0")
        self.field_cv_interval = _double_field("0.50")
        self.field_cv_duration = _double_field("60.0")
        self.button_run_cv = QPushButton("Run Constant Voltage")
        self.button_run_cv.clicked.connect(self._run_constant_v)
        self.button_abort_cv = QPushButton("Abort Measurement")
        self.button_abort_cv.clicked.connect(self.abort_requested)
        self.button_abort_cv.setEnabled(False)

        panel_cv = QWidget()
        panel_cv.setMaximumWidth(300)
        cv_layout = QVBoxLayout()
        cv_layout.addLayout(
            _grid_rows(
                [
                    ("Set Voltage", self.field_cv_set_v, "V"),
                    ("Stabilization Time", self.field_cv_stabilization, "sec"),
                    ("Meas Interval", self.field_cv_interval, "sec"),
                    ("Meas Duration", self.field_cv_duration, "sec"),
                ]
            )
        )
        cv_layout.addWidget(self.button_run_cv)
        cv_layout.addWidget(self.button_abort_cv)
        panel_cv.setLayout(cv_layout)

        # constant current form (set current in mA, legacy)
        self.field_cc_set_i = _double_field("0.00")
        self.field_cc_stabilization = _double_field("5.0")
        self.field_cc_interval = _double_field("0.50")
        self.field_cc_duration = _double_field("60.0")
        self.button_run_cc = QPushButton("Run Constant Current")
        self.button_run_cc.clicked.connect(self._run_constant_i)
        self.button_abort_cc = QPushButton("Abort Measurement")
        self.button_abort_cc.clicked.connect(self.abort_requested)
        self.button_abort_cc.setEnabled(False)

        panel_cc = QWidget()
        panel_cc.setMaximumWidth(300)
        cc_layout = QVBoxLayout()
        cc_layout.addLayout(
            _grid_rows(
                [
                    ("Set Current", self.field_cc_set_i, "mA"),
                    ("Stabilization Time", self.field_cc_stabilization, "sec"),
                    ("Meas Interval", self.field_cc_interval, "sec"),
                    ("Meas Duration", self.field_cc_duration, "sec"),
                ]
            )
        )
        cc_layout.addWidget(self.button_run_cc)
        cc_layout.addWidget(self.button_abort_cc)
        panel_cc.setLayout(cc_layout)

        # MPP form
        self.check_automatic_mpp = QCheckBox("Find Start Voltage Automatically")
        self.check_automatic_mpp.stateChanged.connect(self._toggle_mpp_start_mode)
        self.field_mpp_start_v = _double_field("1.00")
        self.field_mpp_stabilization = _double_field("5.0")
        self.field_mpp_interval = _double_field("0.50")
        self.field_mpp_duration = _double_field("60.0")
        self.button_run_mpp = QPushButton("Run Max Power Point")
        self.button_run_mpp.clicked.connect(self._run_mpp)
        self.button_abort_mpp = QPushButton("Abort Measurement")
        self.button_abort_mpp.clicked.connect(self.abort_requested)
        self.button_abort_mpp.setEnabled(False)

        panel_mpp = QWidget()
        panel_mpp.setMaximumWidth(300)
        mpp_layout = QVBoxLayout()
        mpp_layout.addWidget(self.check_automatic_mpp)
        mpp_layout.addLayout(
            _grid_rows(
                [
                    ("Start Voltage", self.field_mpp_start_v, "V"),
                    ("Stabilization Time", self.field_mpp_stabilization, "sec"),
                    ("Meas Interval", self.field_mpp_interval, "sec"),
                    ("Meas Duration", self.field_mpp_duration, "sec"),
                ]
            )
        )
        mpp_layout.addWidget(self.button_run_mpp)
        mpp_layout.addWidget(self.button_abort_mpp)
        panel_mpp.setLayout(mpp_layout)

        # calibration form
        self.calibration_panel = CalibrationPanel()
        self.calibration_panel.run_clicked.connect(self._run_calibration)
        self.calibration_panel.abort_clicked.connect(self.abort_requested)
        self.calibration_panel.save_clicked.connect(self._save_calibration)

        self.measurement_stack = QStackedWidget()
        for panel in (panel_iv, panel_cv, panel_cc, panel_mpp, self.calibration_panel):
            self.measurement_stack.addWidget(panel)

        group_layout = QVBoxLayout()
        group_layout.addWidget(self.menu_measurement)
        group_layout.addWidget(self.measurement_stack)
        self.group_measurement.setLayout(group_layout)
        self.group_measurement.setEnabled(False)
        self.group_measurement.setMaximumWidth(300)

        # --- SMU configuration group (legacy createComplianceGroupBox) ---
        self.group_compliance = QGroupBox("SMU Configuration")
        self.menu_nwire = QComboBox()
        self.menu_nwire.addItem("2 wire")
        self.menu_nwire.addItem("4 wire")
        self.field_voltage_limit = _double_field("2.00")
        self.field_voltage_limit.setMaximumWidth(75)
        self.field_current_limit = _double_field("5.00")
        self.field_current_limit.setMaximumWidth(75)
        self.group_compliance.setLayout(
            _grid_rows(
                [
                    ("Measurement mode", self.menu_nwire, ""),
                    ("Voltage Limit", self.field_voltage_limit, "V"),
                    ("Current Limit", self.field_current_limit, "mA"),
                ]
            )
        )
        self.group_compliance.setEnabled(False)
        self.group_compliance.setMaximumWidth(300)

        # --- cell active area (legacy createCellSizeWidget) ---
        self.cell_size_widget = QWidget()
        self.field_cell_active_area = _double_field("1.00")
        self.field_cell_active_area.setMaximumWidth(75)
        area_layout = QHBoxLayout()
        area_layout.addWidget(QLabel("Cell Active Area"))
        area_layout.addWidget(self.field_cell_active_area)
        area_layout.addWidget(QLabel("cm<sup>2</sup>"))
        self.cell_size_widget.setLayout(area_layout)
        self.cell_size_widget.setEnabled(False)

        layout = QVBoxLayout()
        layout.addWidget(self.group_measurement)
        layout.addWidget(self.cell_size_widget)
        layout.addWidget(self.group_compliance)
        self.setLayout(layout)

    # --- selection and mode toggles (legacy) ---

    def _select_measurement(self, index: int) -> None:
        self.measurement_stack.setCurrentIndex(index)
        self.measurement_selected.emit(index)

    def _iv_max_v_changed(self) -> None:
        text = self.field_iv_max_v.text()
        if len(text) == 0:
            return
        if self.check_automatic_limits.isChecked():
            self._iv_fwd_limit_user = float(text)
        else:
            self._iv_max_v_user = float(text)

    def _toggle_iv_limits_mode(self) -> None:
        if self.check_automatic_limits.isChecked():
            self.field_iv_min_v.setEnabled(False)
            self.field_iv_max_v.setText(str(self._iv_fwd_limit_user))
            self.label_iv_max_v.setText("Fwd Current Limit")
            self.label_iv_max_v_units.setText("mA/cm<sup>2</sup>")
        else:
            self.field_iv_min_v.setEnabled(True)
            self.field_iv_max_v.setText(str(self._iv_max_v_user))
            self.label_iv_max_v.setText("Maximum Voltage")
            self.label_iv_max_v_units.setText("V")

    def _toggle_mpp_start_mode(self) -> None:
        self.field_mpp_start_v.setEnabled(not self.check_automatic_mpp.isChecked())

    # --- calibration access control (legacy enable/disableCalibration) ---

    def enable_calibration(self) -> None:
        if self.menu_measurement.count() < 5:
            self.menu_measurement.addItem("Calibrate Reference Diode")

    def disable_calibration(self) -> None:
        if self.menu_measurement.count() >= 5:
            self.menu_measurement.removeItem(4)

    # --- common parameter pieces (legacy run* methods) ---

    def _common_params(self) -> dict:
        return {
            "light_int": self._light_level(),
            "Nwire": str(self.menu_nwire.currentText()),
            "Imax": abs(float(self.field_current_limit.text()) / 1000.0),
            "Vmax": abs(float(self.field_voltage_limit.text())),
            "active_area": float(self.field_cell_active_area.text()),
            "cell_name": sanitize_cell_name(self._cell_name()),
        }

    # --- parameter assembly (legacy runIV etc.) ---

    def _run_iv(self) -> None:
        sweep_dir = self.sweep_direction_list[self.menu_sweep_direction.currentIndex()]
        dv = float(self.field_iv_v_step.text()) / 1000.0  # field value is mV
        v_compliance = abs(float(self.field_voltage_limit.text()))
        i_compliance = abs(float(self.field_current_limit.text()) / 1000.0)
        active_area = float(self.field_cell_active_area.text())

        if self.check_automatic_limits.isChecked():
            limits_mode = "Automatic"
            fwd_current_limit = float(self.field_iv_max_v.text()) * active_area / 1000.0
            if sweep_dir == "Forward":
                start_v, stop_v, dv = 0.0, "Voc", abs(dv)
            else:
                start_v, stop_v, dv = "Voc", 0.0, -1 * abs(dv)
        else:
            limits_mode = "Manual"
            fwd_current_limit = i_compliance

            min_v = float(self.field_iv_min_v.text())
            max_v = float(self.field_iv_max_v.text())
            if abs(max_v) > v_compliance:
                self.validation_error.emit(
                    "ERROR: Maximum voltage outside of compliance range"
                )
                return
            if abs(min_v) > v_compliance:
                self.validation_error.emit(
                    "ERROR: Minimum voltage outside of compliance range"
                )
                return
            if min_v >= max_v:
                self.validation_error.emit(
                    "ERROR: Maximum voltage must be greater\nthan Minimum for J-V scan"
                )
                return

            if sweep_dir == "Forward":
                start_v, stop_v, dv = min_v, max_v, abs(dv)
            else:
                start_v, stop_v, dv = max_v, min_v, -1 * abs(dv)

        params = self._common_params()
        params.update(
            {
                "limits_mode": limits_mode,
                "Fwd_current_limit": fwd_current_limit,
                "start_V": start_v,
                "stop_V": stop_v,
                "dV": dv,
                "sweep_rate": abs(float(self.field_iv_sweep_rate.text()) / 1000.0),
                "Dwell": abs(float(self.field_iv_stabilization.text())),
            }
        )
        self.run_requested.emit("J-V Scan", params)

    def _run_constant_v(self) -> None:
        v_compliance = abs(float(self.field_voltage_limit.text()))
        set_v = float(self.field_cv_set_v.text())
        if abs(set_v) > v_compliance:
            self.validation_error.emit(
                "ERROR: Requested voltage outside of compliance range"
            )
            return

        params = self._common_params()
        params.update(
            {
                "set_voltage": set_v,
                "Dwell": float(self.field_cv_stabilization.text()),
                "interval": float(self.field_cv_interval.text()),
                "duration": float(self.field_cv_duration.text()),
            }
        )
        self.run_requested.emit("Constant Voltage, Measure J", params)

    def _run_constant_i(self) -> None:
        i_compliance = abs(float(self.field_current_limit.text()) / 1000.0)
        set_i = float(self.field_cc_set_i.text()) / 1000.0  # field value is mA
        if abs(set_i) > i_compliance:
            self.validation_error.emit(
                "ERROR: Requested current outside of compliance range"
            )
            return

        params = self._common_params()
        params.update(
            {
                "set_current": set_i,
                "Dwell": float(self.field_cc_stabilization.text()),
                "interval": float(self.field_cc_interval.text()),
                "duration": float(self.field_cc_duration.text()),
            }
        )
        self.run_requested.emit("Constant Current, Measure V", params)

    def _run_mpp(self) -> None:
        v_compliance = abs(float(self.field_voltage_limit.text()))
        start_v = float(self.field_mpp_start_v.text())
        if abs(start_v) > v_compliance:
            self.validation_error.emit(
                "ERROR: MPP start voltage outside of compliance range"
            )
            return

        params = self._common_params()
        params.update(
            {
                "start_voltage": (
                    "auto" if self.check_automatic_mpp.isChecked() else start_v
                ),
                "Dwell": float(self.field_mpp_stabilization.text()),
                "interval": float(self.field_mpp_interval.text()),
                "duration": float(self.field_mpp_duration.text()),
            }
        )
        self.run_requested.emit("Maximum Power Point", params)

    def _run_calibration(self) -> None:
        cal = self.calibration_panel
        params = self._common_params()
        params.update(
            {
                "set_voltage": 0.0,
                "Dwell": float(cal.field_stabilization_time.text()),
                "interval": float(cal.field_interval.text()),
                "duration": float(cal.field_duration.text()),
                "reference_current": abs(
                    float(cal.field_diode_reference_current.text()) / 1000.0
                ),
            }
        )
        # legacy enables the save button when the run starts
        cal.button_save.setEnabled(True)
        self.run_requested.emit("Calibration", params)

    def _save_calibration(self) -> None:
        self.save_calibration_requested.emit(
            {"reference_current": self.calibration_panel.reference_current_a()}
        )

    # --- enable state (legacy setHardwareActive / logInValid) ---

    def set_hardware_active(self, active: bool) -> None:
        """Enable the measurement and SMU groups (legacy
        ``setHardwareActive``)."""
        self.group_measurement.setEnabled(active)
        self.group_compliance.setEnabled(active)

    def set_logged_in(self, logged_in: bool) -> None:
        """Enable the cell-area widget (legacy ``logInValid`` /
        ``logOut``)."""
        self.cell_size_widget.setEnabled(logged_in)

    # --- run state (legacy runStarted / runFinished) ---

    def set_running(self, running: bool) -> None:
        self.menu_measurement.setEnabled(not running)
        for button in (
            self.button_run_iv,
            self.button_run_cv,
            self.button_run_cc,
            self.button_run_mpp,
            self.calibration_panel.button_run,
        ):
            button.setEnabled(not running)
        for button in (
            self.button_abort_iv,
            self.button_abort_cv,
            self.button_abort_cc,
            self.button_abort_mpp,
            self.calibration_panel.button_abort,
        ):
            button.setEnabled(running)

    # --- defaults (legacy setAllFieldsToDefault, panel-owned fields) ---

    def reset_to_defaults(self) -> None:
        self.check_automatic_limits.setChecked(False)
        self._toggle_iv_limits_mode()
        self.check_automatic_mpp.setChecked(False)
        self._toggle_mpp_start_mode()
        self.field_iv_min_v.setText("0.00")
        self._iv_max_v_user = 1.2
        self._iv_fwd_limit_user = 0.0
        self.field_iv_max_v.setText(str(self._iv_max_v_user))
        self.field_iv_v_step.setText("5.0")
        self.field_iv_sweep_rate.setText("20.0")
        self.field_iv_stabilization.setText("5.0")
        self.menu_sweep_direction.setCurrentIndex(1)
        self.field_cv_set_v.setText("0.00")
        self.field_cv_stabilization.setText("5.0")
        self.field_cv_interval.setText("0.50")
        self.field_cv_duration.setText("60.0")
        self.field_cc_set_i.setText("0.00")
        self.field_cc_stabilization.setText("5.0")
        self.field_cc_interval.setText("0.50")
        self.field_cc_duration.setText("60.0")
        self.field_mpp_start_v.setText("1.00")
        self.field_mpp_stabilization.setText("5.0")
        self.field_mpp_interval.setText("0.50")
        self.field_mpp_duration.setText("60.0")
        self.field_cell_active_area.setText("0.16")
        self.menu_nwire.setCurrentIndex(0)
        self.field_voltage_limit.setText("2.00")
        self.field_current_limit.setText("5.0")
        self.menu_measurement.setCurrentIndex(0)
        self.calibration_panel.reset_to_defaults()
