"""Plot panel (legacy ``createGraphPanels`` and ``updatePlot*``).

One stacked pyqtgraph panel per measurement type: J-V (with the results
grid), constant voltage, constant current, MPP (power plot plus the
dual-axis V/J plot), and calibration (dual-axis diode currents).

Live data arrives as the protocol data dicts re-emitted by the core
system; :meth:`update_live_data` dispatches on the dict keys, so the
panel showing the incoming data is raised automatically (this also
reproduces the legacy behavior of showing the J-V plot during the MPP
automatic start scan).
"""

from __future__ import annotations

import pyqtgraph as pg
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from iv_lab.data.results import IVResults

#: Stack indices (legacy measurement menu order).
PANEL_IV = 0
PANEL_CONSTANT_V = 1
PANEL_CONSTANT_I = 2
PANEL_MPP = 3
PANEL_CALIBRATION = 4


def _make_plot(left: str, bottom: str) -> pg.PlotWidget:
    plot = pg.PlotWidget()
    plot.setBackground("w")
    plot.showGrid(x=True, y=True, alpha=0.3)
    plot.setLabel("left", left)
    plot.setLabel("bottom", bottom)
    return plot


class _DualAxisPlot(QWidget):
    """Two curves with independent y-axes (legacy MPPIV / calibration)."""

    def __init__(self, left: str, right: str, bottom: str) -> None:
        super().__init__()
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground("w")
        plot_item = self.plot_widget.plotItem
        plot_item.setLabel("left", left, color="#ff0000")
        plot_item.showGrid(x=True, y=True, alpha=0.3)
        plot_item.setLabel("bottom", bottom)
        plot_item.setLabel("right", right, color="#0000ff")
        self.curve_left = plot_item.plot(x=[], y=[], pen=pg.mkPen("r", width=2))

        # second viewbox linked to the right axis (legacy pattern)
        self.view_box_right = pg.ViewBox()
        plot_item.scene().addItem(self.view_box_right)
        plot_item.getAxis("right").linkToView(self.view_box_right)
        self.view_box_right.setXLink(plot_item)
        self.curve_right = pg.PlotCurveItem(pen=pg.mkPen("b", width=2))
        self.view_box_right.addItem(self.curve_right)
        self._plot_item = plot_item
        plot_item.vb.sigResized.connect(self._update_views)

        layout = QVBoxLayout()
        layout.addWidget(self.plot_widget)
        self.setLayout(layout)

    def _update_views(self) -> None:
        self.view_box_right.setGeometry(self._plot_item.vb.sceneBoundingRect())

    def set_data(self, x_left, y_left, x_right, y_right) -> None:
        self.curve_left.setData(x_left, y_left)
        self.curve_right.setData(x_right, y_right)
        self._update_views()

    def clear_curves(self) -> None:
        self.curve_left.setData(x=[], y=[])
        self.curve_right.setData(x=[], y=[])


class _ResultField(QHBoxLayout):
    def __init__(self, label: str, units: str) -> None:
        super().__init__()
        self.value = QLabel("-----")
        self.addWidget(QLabel(label))
        self.addWidget(self.value)
        self.addWidget(QLabel(units))


class PlotPanel(QWidget):
    """Stacked measurement plots plus the J-V results grid."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.stack = QStackedWidget()

        # J-V plot and results grid (legacy panelGraphIV)
        self.plot_iv = _make_plot("Current (mA/cm2)", "Voltage (V)")
        self._curve_iv = None

        self.iv_results_widget = QWidget()
        results_layout = QGridLayout()
        self.field_jsc = _ResultField("Jsc:", "mA/cm<sup>2</sup>")
        self.field_voc = _ResultField("Voc:", "V")
        self.field_ff = _ResultField("Fill Factor:", "")
        self.field_pce = _ResultField("PCE:", "%")
        self.field_jmpp = _ResultField("Jmpp:", "mA/cm<sup>2</sup>")
        self.field_vmpp = _ResultField("Vmpp:", "V")
        self.field_pmpp = _ResultField("Pmpp:", "mW/cm<sup>2</sup>")
        self.field_light_int = _ResultField("Light Intensity:", "% sun")
        results_layout.addLayout(self.field_jsc, 0, 0)
        results_layout.addLayout(self.field_voc, 1, 0)
        results_layout.addLayout(self.field_ff, 2, 0)
        results_layout.addLayout(self.field_pce, 3, 0)
        results_layout.addLayout(self.field_jmpp, 0, 2)
        results_layout.addLayout(self.field_vmpp, 1, 2)
        results_layout.addLayout(self.field_pmpp, 2, 2)
        results_layout.addLayout(self.field_light_int, 3, 2)
        results_layout.setColumnStretch(1, 1)
        results_layout.setColumnStretch(3, 1)
        self.iv_results_widget.setLayout(results_layout)
        self.iv_results_widget.setEnabled(False)

        panel_iv = QWidget()
        panel_iv_layout = QVBoxLayout()
        panel_iv_layout.addWidget(self.plot_iv)
        panel_iv_layout.addWidget(self.iv_results_widget)
        panel_iv.setLayout(panel_iv_layout)
        self.stack.addWidget(panel_iv)

        # constant voltage / constant current panels
        self.plot_constant_v = _make_plot("Current (mA/cm2)", "Time (sec)")
        self._curve_constant_v = None
        self.stack.addWidget(self._wrap(self.plot_constant_v))

        self.plot_constant_i = _make_plot("Voltage (V)", "Time (sec)")
        self._curve_constant_i = None
        self.stack.addWidget(self._wrap(self.plot_constant_i))

        # MPP: power plot above the dual-axis V/J plot
        self.plot_mpp = _make_plot("Power (mW/cm<sup>2</sup>)", "Time (sec)")
        self._curve_mpp = None
        self.plot_mpp_iv = _DualAxisPlot(
            "MPP Voltage (V)", "MPP Current (mA/cm2)", "Time (sec)"
        )
        panel_mpp = QWidget()
        panel_mpp_layout = QVBoxLayout()
        panel_mpp_layout.addWidget(self.plot_mpp)
        panel_mpp_layout.addWidget(self.plot_mpp_iv)
        panel_mpp.setLayout(panel_mpp_layout)
        self.stack.addWidget(panel_mpp)

        # calibration dual-axis diode currents
        self.plot_calibration = _DualAxisPlot(
            "Calibration Diode Current (mA)",
            "Reference Diode Current (mA)",
            "Time (sec)",
        )
        self.stack.addWidget(self.plot_calibration)

        layout = QVBoxLayout()
        layout.addWidget(self.stack)
        self.setLayout(layout)

    @staticmethod
    def _wrap(widget: QWidget) -> QWidget:
        panel = QWidget()
        panel_layout = QVBoxLayout()
        panel_layout.addWidget(widget)
        panel.setLayout(panel_layout)
        return panel

    # --- panel selection (legacy selectMeasurement) ---

    def select_panel(self, index: int) -> None:
        self.stack.setCurrentIndex(index)

    # --- live data (legacy updatePlot*) ---

    @staticmethod
    def _set_curve(plot, curve, x, y):
        if curve is None:
            return plot.plot(x, y, pen=pg.mkPen("r", width=2))
        curve.setData(x, y)
        return curve

    def update_live_data(self, data: dict) -> None:
        """Route a protocol live-data dict to its plot by its keys."""
        if "i_meas_ma" in data:  # calibration
            self.stack.setCurrentIndex(PANEL_CALIBRATION)
            self.plot_calibration.set_data(
                data["t_meas"], data["i_meas_ma"], data["t_ref"], data["i_ref_ma"]
            )
        elif "w" in data:  # MPP tracking
            self.stack.setCurrentIndex(PANEL_MPP)
            self._curve_mpp = self._set_curve(
                self.plot_mpp, self._curve_mpp, data["t"], data["w"]
            )
            self.plot_mpp_iv.set_data(data["t"], data["v"], data["t"], data["j"])
        elif "t" in data and "j" in data:  # constant voltage
            self.stack.setCurrentIndex(PANEL_CONSTANT_V)
            self._curve_constant_v = self._set_curve(
                self.plot_constant_v, self._curve_constant_v, data["t"], data["j"]
            )
        elif "t" in data and "v" in data:  # constant current
            self.stack.setCurrentIndex(PANEL_CONSTANT_I)
            self._curve_constant_i = self._set_curve(
                self.plot_constant_i, self._curve_constant_i, data["t"], data["v"]
            )
        elif "v" in data and "j" in data:  # J-V scan (also MPP auto start)
            self.stack.setCurrentIndex(PANEL_IV)
            self._curve_iv = self._set_curve(
                self.plot_iv, self._curve_iv, data["v"], data["j"]
            )

    # --- J-V results grid (legacy updateIVResults) ---

    def update_iv_results(self, result: IVResults | None) -> None:
        def fmt(value, spec):
            return spec.format(value) if value is not None else "-----"

        if result is None:
            result = IVResults()
        self.field_jsc.value.setText(fmt(result.Jsc, "{:.3f}"))
        self.field_voc.value.setText(fmt(result.Voc, "{:.4f}"))
        self.field_ff.value.setText(fmt(result.FF, "{:.4f}"))
        self.field_pce.value.setText(fmt(result.PCE, "{:.3f}"))
        self.field_jmpp.value.setText(fmt(result.Jmpp, "{:.3f}"))
        self.field_vmpp.value.setText(fmt(result.Vmpp, "{:.4f}"))
        self.field_pmpp.value.setText(fmt(result.Pmpp, "{:.3f}"))
        self.field_light_int.value.setText(fmt(result.light_int_meas, "{:.1f}"))

    # --- clearing (legacy clearPlot*) ---

    def clear_all(self) -> None:
        for plot, attr in (
            (self.plot_iv, "_curve_iv"),
            (self.plot_constant_v, "_curve_constant_v"),
            (self.plot_constant_i, "_curve_constant_i"),
            (self.plot_mpp, "_curve_mpp"),
        ):
            plot.clear()
            setattr(self, attr, None)
        self.plot_mpp_iv.clear_curves()
        self.plot_calibration.clear_curves()
        self.update_iv_results(None)
