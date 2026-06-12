"""Main window (legacy ``Window`` in ``IVLab/IV_gui.py``).

Assembles the panels and connects them to the
:class:`~iv_lab.core.IVLabSystem` signals. The window never creates
hardware, never writes measurement files, and never calls
``processEvents`` — all work happens in the core system and its
workers; the GUI communicates through signals and slots only.

Preserved legacy behavior includes the enable cascade (login enables
the init button and per-user widgets; hardware init enables the
measurement groups), the run button state machine, the per-user GUI
configuration file (``<basePath>/<user>/IVLab_config.json``), the light
level menu generated from the lamp's level dictionary, calibration
access by user permission, and the logout flow with the logbook dialog.
"""

from __future__ import annotations

import json
import os
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from iv_lab.core import IVLabSystem
from iv_lab.data.results import IVResults

from .dialogs.logoff_dialog import LogOffDialog
from .panels.light_panel import LightLevelPanel
from .panels.measurement_panel import CORE_LABELS, MeasurementPanel
from .panels.plot_panel import PlotPanel

#: Legacy per-user GUI configuration file name.
USER_CONFIG_FILENAME = "IVLab_config.json"


class MainWindow(QMainWindow):
    """IVLab main window wired to the core system."""

    def __init__(self, system: IVLabSystem, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.system = system
        #: Tests set this to avoid modal error dialogs.
        self.suppress_error_dialogs = False
        #: All error messages shown (newest last).
        self.error_log: list[str] = []

        self.setWindowTitle("IVLab")
        self.resize(1200, 600)

        # --- left column ---
        self.button_initialize = QPushButton("Initialize Hardware")
        self.button_initialize.setMaximumWidth(300)
        self.button_initialize.setEnabled(False)
        self.button_initialize.clicked.connect(self._initialize_hardware)

        self.light_panel = LightLevelPanel()
        self.measurement_panel = MeasurementPanel(
            light_level_provider=self.light_panel.current_light_level,
            cell_name_provider=lambda: self.field_cell_name.text(),
        )

        self.button_reset_defaults = QPushButton("Reset All Settings To Default")
        self.button_reset_defaults.setEnabled(False)
        self.button_reset_defaults.clicked.connect(self.set_all_fields_to_default)

        left = QWidget()
        left_layout = QVBoxLayout()
        left_layout.addWidget(self.button_initialize)
        left_layout.addStretch(1)
        left_layout.addWidget(self.light_panel)
        left_layout.addStretch(1)
        left_layout.addWidget(self.measurement_panel)
        left_layout.addStretch(1)
        left_layout.addWidget(self.button_reset_defaults)
        left.setLayout(left_layout)

        # --- plot header (cell name, auto-save, save, login/logout) ---
        self.field_cell_name = QLineEdit("")
        self.field_cell_name.setPlaceholderText("Enter Cell Name Here...")
        self.field_cell_name.setMinimumWidth(500)
        self.field_cell_name.setEnabled(False)

        self.check_auto_save = QCheckBox("Auto-save")
        self.check_auto_save.setEnabled(False)
        self.check_auto_save.stateChanged.connect(self._toggle_auto_save)

        self.button_save_data = QPushButton("Save Data")
        self.button_save_data.setEnabled(False)
        self.button_save_data.clicked.connect(self._save_scan_data)

        login_panel = QWidget()
        login_layout = QHBoxLayout()
        self.field_username = QLineEdit("")
        self.field_username.setPlaceholderText("Username")
        self.field_username.setMinimumWidth(100)
        self.field_sciper = QLineEdit("")
        self.field_sciper.setPlaceholderText("Sciper")
        self.field_sciper.setMinimumWidth(100)
        self.field_sciper.returnPressed.connect(self._log_in)
        self.button_login = QPushButton("Log In")
        self.button_login.clicked.connect(self._log_in)
        login_layout.addWidget(self.field_username)
        login_layout.addWidget(self.field_sciper)
        login_layout.addWidget(self.button_login)
        login_panel.setLayout(login_layout)

        logout_panel = QWidget()
        logout_layout = QHBoxLayout()
        self.label_logged_in_user = QLabel("")
        self.button_logout = QPushButton("Log Out")
        self.button_logout.clicked.connect(self._confirm_logout)
        logout_layout.addWidget(QLabel("Logged in as: "))
        logout_layout.addWidget(self.label_logged_in_user)
        logout_layout.addWidget(self.button_logout)
        logout_panel.setLayout(logout_layout)

        self.stack_login = QStackedWidget()
        self.stack_login.addWidget(login_panel)
        self.stack_login.addWidget(logout_panel)
        self.stack_login.setCurrentIndex(0)  # 0 = login, 1 = logout

        header = QWidget()
        header_layout = QHBoxLayout()
        header_layout.addWidget(self.field_cell_name)
        header_layout.addWidget(self.check_auto_save)
        header_layout.addWidget(self.button_save_data)
        header_layout.addStretch(1)
        header_layout.addWidget(self.stack_login)
        header.setLayout(header_layout)

        # --- plots ---
        self.plot_panel = PlotPanel()

        right = QWidget()
        right_layout = QVBoxLayout()
        right_layout.addWidget(header)
        right_layout.addWidget(self.plot_panel)
        right.setLayout(right_layout)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setStretchFactor(1, 10)

        central = QWidget()
        central_layout = QHBoxLayout()
        central_layout.addWidget(splitter)
        central_layout.setContentsMargins(10, 10, 10, 10)
        central.setLayout(central_layout)
        self.setCentralWidget(central)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Please Log In")

        self._connect_panels()
        self._connect_system()
        self._configure_light_panel()
        self._register_config_fields()

    # --- wiring ---

    def _connect_panels(self) -> None:
        panel = self.measurement_panel
        panel.run_requested.connect(self._run_measurement)
        panel.abort_requested.connect(self.system.abort_run)
        panel.validation_error.connect(self._show_error)
        panel.save_calibration_requested.connect(
            self.system.save_calibration_to_system_settings
        )
        panel.measurement_selected.connect(self.plot_panel.select_panel)

    def _connect_system(self) -> None:
        system = self.system
        system.status_message.connect(self.status_bar.showMessage)
        system.error_message.connect(self._show_error)
        system.warning_message.connect(self._show_error)  # legacy error_window
        system.data_updated.connect(self.plot_panel.update_live_data)
        system.measurement_finished.connect(self._on_measurement_finished)
        system.calibration_ready.connect(self._on_calibration_ready)
        system.hardware_ready.connect(self._set_hardware_active)
        system.user_logged_in.connect(self._on_logged_in)
        system.user_logged_out.connect(self._on_logged_out)

    def _configure_light_panel(self) -> None:
        """Legacy ``__main__`` light level setup from the lamp settings."""
        lamp_settings = self.system.settings.lamp
        if lamp_settings.brand.lower() == "manual":
            self.light_panel.set_manual_mode()
            return

        self.light_panel.set_menu_mode()
        light_levels: dict[str, float] = {}
        for level in (lamp_settings.lightLevelDict or {}):
            if level < 0.01:
                light_levels["Dark"] = level
            else:
                light_levels[f"{level:4.1f} % Sun"] = level
        self.light_panel.set_light_level_list(light_levels)

    # --- error display (legacy showErrorMessage / error_window) ---

    def _show_error(self, message: str) -> None:
        self.error_log.append(message)
        if not self.suppress_error_dialogs:
            QMessageBox.critical(self, "IVlab Error", message)

    # --- login / logout (legacy logIn / logInValid / logOut) ---

    def _log_in(self) -> None:
        self.system.login(self.field_username.text(), self.field_sciper.text())

    def _on_logged_in(self, user) -> None:
        self.button_initialize.setEnabled(True)
        self.field_cell_name.setEnabled(True)
        self.check_auto_save.setEnabled(True)
        self.measurement_panel.set_logged_in(True)
        self.button_reset_defaults.setEnabled(True)
        self.plot_panel.iv_results_widget.setEnabled(True)
        self.label_logged_in_user.setText(user.username)
        self.stack_login.setCurrentIndex(1)
        self.field_username.setText("")
        self.field_sciper.setText("")

        # only certain users may calibrate (legacy)
        if user.can_calibrate:
            self.measurement_panel.enable_calibration()
        else:
            self.measurement_panel.disable_calibration()

        self.load_user_config()

    def _confirm_logout(self) -> None:
        dialog = LogOffDialog(self)
        if not dialog.exec():
            return
        self._do_logout(dialog.log_book_entry())

    def _do_logout(self, log_book_entry: str) -> None:
        # save the user's GUI configuration before the system clears state
        self.save_user_config()

        self.system.logout(log_book_entry)

    def _on_logged_out(self) -> None:
        self._set_hardware_active(False)
        self.button_initialize.setEnabled(False)
        self.field_cell_name.setEnabled(False)
        self.check_auto_save.setEnabled(False)
        self.button_save_data.setEnabled(False)
        self.measurement_panel.set_logged_in(False)
        self.button_reset_defaults.setEnabled(False)
        self.plot_panel.iv_results_widget.setEnabled(False)
        self.plot_panel.clear_all()
        self.stack_login.setCurrentIndex(0)
        self.set_all_fields_to_default()

    # --- hardware (legacy initializeHardware / setHardwareActive) ---

    def _initialize_hardware(self) -> None:
        self.system.hardware_init()

    def _set_hardware_active(self, active: bool) -> None:
        self.light_panel.setEnabled(active)
        self.measurement_panel.set_hardware_active(active)

    # --- measurements (legacy runStarted / runFinished) ---

    def _run_measurement(self, label: str, params: dict) -> None:
        self._set_running(True)
        self.system.run_measurement(label, params)

    def _set_running(self, running: bool) -> None:
        self.measurement_panel.set_running(running)
        self.button_save_data.setEnabled(not running)

    def _on_measurement_finished(self, result) -> None:
        self._set_running(False)
        if isinstance(result, IVResults):
            self.plot_panel.update_iv_results(result)
        if getattr(result, "light_int_meas", None) is not None:
            self.light_panel.update_measured_intensity(result.light_int_meas)

    def _on_calibration_ready(self, reference_current_a: float) -> None:
        # shown in mA (legacy setCalibrationReferenceCurrent)
        self.measurement_panel.calibration_panel.set_reference_current(
            reference_current_a * 1000.0
        )

    # --- saving (legacy saveScanData / toggleAutoSaveMode) ---

    def _save_scan_data(self) -> None:
        combo_text = str(self.measurement_panel.menu_measurement.currentText())
        label = CORE_LABELS.get(combo_text, combo_text)
        self.system.save_data(label, self.field_cell_name.text())

    def _toggle_auto_save(self) -> None:
        self.system.toggle_auto_save(self.check_auto_save.isChecked())

    # --- per-user GUI configuration (legacy load/saveSettingsFile) ---

    def _register_config_fields(self) -> None:
        panel = self.measurement_panel
        cal = panel.calibration_panel
        #: legacy UIFields name -> QLineEdit
        self._config_fields = {
            "ManualLightLevel": self.light_panel.field_manual_light_level,
            "IVMinimumVoltage": panel.field_iv_min_v,
            "IVMaximumVoltage": panel.field_iv_max_v,
            "IVVoltageStep": panel.field_iv_v_step,
            "IVSweepRate": panel.field_iv_sweep_rate,
            "IVStabilizationTime": panel.field_iv_stabilization,
            "ConstantVSetV": panel.field_cv_set_v,
            "ConstantVStabilizationTime": panel.field_cv_stabilization,
            "ConstantVInterval": panel.field_cv_interval,
            "ConstantVDuration": panel.field_cv_duration,
            "ConstantISetI": panel.field_cc_set_i,
            "ConstantIStabilizationTime": panel.field_cc_stabilization,
            "ConstantIInterval": panel.field_cc_interval,
            "ConstantIDuration": panel.field_cc_duration,
            "MaxPPStartV": panel.field_mpp_start_v,
            "MaxPPStabilizationTime": panel.field_mpp_stabilization,
            "MaxPPInterval": panel.field_mpp_interval,
            "MaxPPDuration": panel.field_mpp_duration,
            "CalibrationStabilizationTime": cal.field_stabilization_time,
            "CalibrationInterval": cal.field_interval,
            "CalibrationDuration": cal.field_duration,
            "CalibrationReferenceCellCurrent": cal.field_reference_cell_current,
            "VoltageLimit": panel.field_voltage_limit,
            "CurrentLimit": panel.field_current_limit,
            "CellActiveArea": panel.field_cell_active_area,
        }
        #: legacy UIDropDowns name -> QComboBox
        self._config_dropdowns = {
            "lightLevel": self.light_panel.menu_light_level,
            "measurementType": panel.menu_measurement,
            "2wire4wire": panel.menu_nwire,
            "sweepDirection": panel.menu_sweep_direction,
        }

    def _user_config_path(self) -> Optional[str]:
        if self.system.user is None:
            return None
        return os.path.join(
            self.system.settings.computer.basePath,
            self.system.user.username,
            USER_CONFIG_FILENAME,
        )

    def save_user_config(self) -> None:
        """Legacy ``saveSettingsFile`` (same keys and layout)."""
        path = self._user_config_path()
        if path is None:
            return
        config = {name: field.text() for name, field in self._config_fields.items()}
        for name, dropdown in self._config_dropdowns.items():
            config[name] = dropdown.currentText()
        config["CheckBoxAutomaticLimits"] = (
            self.measurement_panel.check_automatic_limits.isChecked()
        )
        config["CheckBoxAutoSave"] = self.check_auto_save.isChecked()
        config["CheckBoxAutomaticMpp"] = (
            self.measurement_panel.check_automatic_mpp.isChecked()
        )
        config["IVMaxVUser"] = self.measurement_panel._iv_max_v_user
        config["IVFwdLimitUser"] = self.measurement_panel._iv_fwd_limit_user

        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w") as outfile:
                json.dump(config, outfile)
        except Exception:
            self._show_error("ERROR: Could not create settings file " + path)

    def load_user_config(self) -> None:
        """Legacy ``loadSettingsFile``; missing files are ignored."""
        path = self._user_config_path()
        if path is None or not os.path.exists(path):
            return
        try:
            with open(path) as config_file:
                config = json.load(config_file)
        except Exception:
            return

        for name, field in self._config_fields.items():
            if name in config:
                field.setText(str(config[name]))
        for name, dropdown in self._config_dropdowns.items():
            if name in config:
                index = dropdown.findText(str(config[name]))
                if index >= 0:
                    dropdown.setCurrentIndex(index)
        panel = self.measurement_panel
        if "CheckBoxAutomaticLimits" in config:
            panel.check_automatic_limits.setChecked(bool(config["CheckBoxAutomaticLimits"]))
        if "CheckBoxAutoSave" in config:
            self.check_auto_save.setChecked(bool(config["CheckBoxAutoSave"]))
        if "CheckBoxAutomaticMpp" in config:
            panel.check_automatic_mpp.setChecked(bool(config["CheckBoxAutomaticMpp"]))
        if "IVMaxVUser" in config:
            panel._iv_max_v_user = float(config["IVMaxVUser"])
        if "IVFwdLimitUser" in config:
            panel._iv_fwd_limit_user = float(config["IVFwdLimitUser"])

    # --- defaults (legacy setAllFieldsToDefault) ---

    def set_all_fields_to_default(self) -> None:
        self.measurement_panel.reset_to_defaults()
        self.check_auto_save.setChecked(False)
        self._toggle_auto_save()
        if self.light_panel.menu_light_level.count() > 0:
            self.light_panel.menu_light_level.setCurrentIndex(0)
        self.field_cell_name.setText("")
        self.plot_panel.update_iv_results(None)

    # --- shutdown ---

    def closeEvent(self, event) -> None:  # noqa: N802 - Qt naming
        self.system.shutdown()
        super().closeEvent(event)
