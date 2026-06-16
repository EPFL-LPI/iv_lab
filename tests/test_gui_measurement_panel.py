"""Headless tests for the measurement panel parameter assembly."""

import pytest

from iv_lab.gui.panels.measurement_panel import MeasurementPanel, sanitize_cell_name


class Recorder:
    def __init__(self, panel: MeasurementPanel) -> None:
        self.runs: list[tuple[str, dict]] = []
        self.errors: list[str] = []
        self.calibration_saves: list[dict] = []
        panel.run_requested.connect(lambda label, params: self.runs.append((label, params)))
        panel.validation_error.connect(self.errors.append)
        panel.save_calibration_requested.connect(self.calibration_saves.append)


def make_panel(light_level=100.0, cell_name="My Cell #1") -> MeasurementPanel:
    panel = MeasurementPanel(lambda: light_level, lambda: cell_name)
    # buttons report isEnabled only when the (legacy-disabled) groups are
    # active, as after login + hardware init
    panel.set_logged_in(True)
    panel.set_hardware_active(True)
    return panel


def test_sanitize_cell_name_matches_legacy() -> None:
    assert sanitize_cell_name("My Cell #1") == "my-cell-1"
    assert sanitize_cell_name("  weird---name__ ") == "weird-name"
    assert len(sanitize_cell_name("x" * 100)) == 63


def test_iv_params_manual_forward(tmp_path=None) -> None:
    panel = make_panel()
    recorder = Recorder(panel)
    panel.field_iv_min_v.setText("0.10")
    panel.field_iv_max_v.setText("1.10")
    panel.field_iv_v_step.setText("10.0")  # mV
    panel.field_iv_sweep_rate.setText("50.0")  # mV/s
    panel.menu_sweep_direction.setCurrentIndex(0)  # Forward
    panel.field_cell_active_area.setText("0.16")

    panel._run_iv()

    label, params = recorder.runs[0]
    assert label == "J-V Scan"
    assert params["limits_mode"] == "Manual"
    assert params["start_V"] == pytest.approx(0.10)
    assert params["stop_V"] == pytest.approx(1.10)
    assert params["dV"] == pytest.approx(0.010)  # mV -> V
    assert params["sweep_rate"] == pytest.approx(0.050)  # mV/s -> V/s
    assert params["Imax"] == pytest.approx(0.005)  # 5 mA -> A
    assert params["Vmax"] == pytest.approx(2.0)
    assert params["Nwire"] == "2 wire"
    assert params["light_int"] == 100.0
    assert params["cell_name"] == "my-cell-1"
    assert params["Fwd_current_limit"] == pytest.approx(params["Imax"])


def test_iv_params_reverse_negates_dv() -> None:
    panel = make_panel()
    recorder = Recorder(panel)
    panel.menu_sweep_direction.setCurrentIndex(1)  # Reverse

    panel._run_iv()

    _, params = recorder.runs[0]
    assert params["start_V"] == pytest.approx(1.2)  # legacy default max
    assert params["stop_V"] == pytest.approx(0.0)
    assert params["dV"] == pytest.approx(-0.005)


def test_iv_automatic_limits_mode() -> None:
    panel = make_panel()
    recorder = Recorder(panel)
    panel.check_automatic_limits.setChecked(True)
    panel.field_iv_max_v.setText("20.0")  # now the Fwd current limit, mA/cm²
    panel.field_cell_active_area.setText("0.16")
    panel.menu_sweep_direction.setCurrentIndex(0)  # Forward

    panel._run_iv()

    _, params = recorder.runs[0]
    assert params["limits_mode"] == "Automatic"
    assert params["start_V"] == 0.0
    assert params["stop_V"] == "Voc"
    # legacy: field * area / 1000
    assert params["Fwd_current_limit"] == pytest.approx(20.0 * 0.16 / 1000.0)


def test_iv_validation_errors_match_legacy() -> None:
    panel = make_panel()
    recorder = Recorder(panel)

    panel.field_iv_max_v.setText("5.0")  # above the 2 V compliance
    panel._run_iv()
    assert recorder.errors[-1] == "ERROR: Maximum voltage outside of compliance range"

    panel.field_iv_max_v.setText("1.0")
    panel.field_iv_min_v.setText("1.5")
    panel._run_iv()
    assert "must be greater" in recorder.errors[-1]
    assert recorder.runs == []


def test_constant_voltage_params() -> None:
    panel = make_panel(light_level=50.0)
    recorder = Recorder(panel)
    panel.field_cv_set_v.setText("0.45")

    panel._run_constant_v()

    label, params = recorder.runs[0]
    assert label == "Constant Voltage, Measure J"
    assert params["set_voltage"] == pytest.approx(0.45)
    assert params["interval"] == pytest.approx(0.50)
    assert params["duration"] == pytest.approx(60.0)
    assert params["light_int"] == 50.0


def test_constant_current_params_convert_ma() -> None:
    panel = make_panel()
    recorder = Recorder(panel)
    panel.field_cc_set_i.setText("2.5")  # mA

    panel._run_constant_i()

    _, params = recorder.runs[0]
    assert params["set_current"] == pytest.approx(0.0025)


def test_constant_current_out_of_compliance_rejected() -> None:
    panel = make_panel()
    recorder = Recorder(panel)
    panel.field_cc_set_i.setText("50.0")  # above the 5 mA limit

    panel._run_constant_i()

    assert recorder.errors[-1] == "ERROR: Requested current outside of compliance range"
    assert recorder.runs == []


def test_mpp_params_auto_and_manual() -> None:
    panel = make_panel()
    recorder = Recorder(panel)

    panel.field_mpp_start_v.setText("0.45")
    panel._run_mpp()
    assert recorder.runs[-1][1]["start_voltage"] == pytest.approx(0.45)

    panel.check_automatic_mpp.setChecked(True)
    panel._run_mpp()
    assert recorder.runs[-1][1]["start_voltage"] == "auto"
    assert not panel.field_mpp_start_v.isEnabled()


def test_calibration_params_and_save() -> None:
    panel = make_panel()
    recorder = Recorder(panel)
    panel.calibration_panel.field_diode_reference_current.setText("4.00")  # mA

    panel._run_calibration()

    label, params = recorder.runs[0]
    assert label == "Calibration"  # core label, not the combo text
    assert params["set_voltage"] == 0.0
    assert params["reference_current"] == pytest.approx(0.004)
    assert panel.calibration_panel.button_save.isEnabled()

    # derived current arrives in A, shown in mA, saved back in A
    panel.calibration_panel.set_reference_current(0.00412 * 1000.0)
    assert panel.calibration_panel.field_reference_cell_current.text() == "4.120"
    panel._save_calibration()
    assert recorder.calibration_saves[0]["reference_current"] == pytest.approx(0.00412)


def test_calibration_menu_entry_toggles() -> None:
    panel = make_panel()

    panel.disable_calibration()
    assert panel.menu_measurement.count() == 4

    panel.enable_calibration()
    assert panel.menu_measurement.count() == 5
    assert panel.menu_measurement.itemText(4) == "Calibrate Reference Diode"


def test_run_state_toggles_buttons() -> None:
    panel = make_panel()

    panel.set_running(True)
    assert not panel.button_run_iv.isEnabled()
    assert panel.button_abort_iv.isEnabled()
    assert not panel.menu_measurement.isEnabled()

    panel.set_running(False)
    assert panel.button_run_iv.isEnabled()
    assert not panel.button_abort_iv.isEnabled()


def test_reset_to_defaults_matches_legacy() -> None:
    panel = make_panel()
    panel.field_iv_v_step.setText("99")
    panel.field_cell_active_area.setText("9.9")

    panel.reset_to_defaults()

    assert panel.field_iv_v_step.text() == "5.0"
    assert panel.field_cell_active_area.text() == "0.16"  # legacy reset value
    assert panel.menu_sweep_direction.currentIndex() == 1  # legacy: Reverse
    assert panel.field_voltage_limit.text() == "2.00"
