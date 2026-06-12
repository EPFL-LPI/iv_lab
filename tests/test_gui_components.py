"""Headless tests for the GUI building blocks (offscreen platform)."""

import pytest

from iv_lab.data.results import IVResults
from iv_lab.gui.dialogs.logoff_dialog import LogOffDialog
from iv_lab.gui.panels.light_panel import LightLevelPanel
from iv_lab.gui.panels.plot_panel import (
    PANEL_CALIBRATION,
    PANEL_CONSTANT_I,
    PANEL_CONSTANT_V,
    PANEL_IV,
    PANEL_MPP,
    PlotPanel,
)


# --- light panel ---


def test_light_panel_menu_mode_levels() -> None:
    panel = LightLevelPanel()
    panel.set_menu_mode()
    panel.set_light_level_list({"100.0 % Sun": 100.0, "50.0 % Sun": 50.0, "Dark": 0.0})

    assert panel.menu_light_level.count() == 3
    panel.menu_light_level.setCurrentIndex(1)
    assert panel.current_light_level() == 50.0


def test_light_panel_manual_mode() -> None:
    panel = LightLevelPanel()
    panel.set_manual_mode()
    panel.field_manual_light_level.setText("42.5")

    assert panel.manual_mode
    assert panel.current_light_level() == 42.5


def test_light_panel_measured_intensity_label_format() -> None:
    panel = LightLevelPanel()

    panel.update_measured_intensity(99.5)

    # legacy "{:6.2f}" formatting
    assert panel.label_measured_intensity.text() == (
        "Measured Light Intensity:  99.50% sun"
    )


# --- plot panel ---


def test_plot_panel_routes_data_by_keys() -> None:
    panel = PlotPanel()

    panel.update_live_data({"v": [0.0, 0.1], "j": [-25.0, -24.0]})
    assert panel.stack.currentIndex() == PANEL_IV

    panel.update_live_data({"t": [0.0], "j": [-25.0]})
    assert panel.stack.currentIndex() == PANEL_CONSTANT_V

    panel.update_live_data({"t": [0.0], "v": [0.55]})
    assert panel.stack.currentIndex() == PANEL_CONSTANT_I

    panel.update_live_data(
        {"t": [0.0], "w": [9.9], "v": [0.45], "j": [-22.0]}
    )
    assert panel.stack.currentIndex() == PANEL_MPP

    panel.update_live_data(
        {"t_meas": [0.0], "i_meas_ma": [-4.0], "t_ref": [0.0], "i_ref_ma": [-4.0]}
    )
    assert panel.stack.currentIndex() == PANEL_CALIBRATION


def test_plot_panel_iv_results_grid_formats() -> None:
    panel = PlotPanel()
    result = IVResults(
        Jsc=-21.234, Voc=0.5512, FF=0.7264, PCE=8.456,
        Jmpp=-18.852, Vmpp=0.4521, Pmpp=8.523, light_int_meas=99.51,
    )

    panel.update_iv_results(result)

    assert panel.field_jsc.value.text() == "-21.234"
    assert panel.field_voc.value.text() == "0.5512"
    assert panel.field_ff.value.text() == "0.7264"
    assert panel.field_pce.value.text() == "8.456"
    assert panel.field_light_int.value.text() == "99.5"


def test_plot_panel_clear_resets_results_to_dashes() -> None:
    panel = PlotPanel()
    panel.update_iv_results(IVResults(Jsc=-21.0, Voc=0.55))

    panel.clear_all()

    assert panel.field_jsc.value.text() == "-----"
    assert panel.field_voc.value.text() == "-----"


def test_plot_panel_dark_result_shows_dashes() -> None:
    panel = PlotPanel()

    panel.update_iv_results(IVResults())  # all metrics None

    assert panel.field_jsc.value.text() == "-----"
    assert panel.field_pce.value.text() == "-----"


# --- logoff dialog ---


def test_logoff_dialog_collects_entry() -> None:
    dialog = LogOffDialog()
    dialog.text_edit.setPlainText("cells degraded quickly")

    assert dialog.log_book_entry() == "cells degraded quickly"
