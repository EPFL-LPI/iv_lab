"""
verasol_gui.py — PySide6 control panel for the Oriel VeraSol LSS-7120 LED Solar Simulator.

Requires:
    pip install PySide6 pyvisa pyvisa-py

Place verasol.py in the same directory, then run:
    python verasol_gui.py
"""

from __future__ import annotations

import sys

from PySide6.QtCore import (
    QObject,
    Qt,
    QThread,
    QTimer,
    Signal,
    Slot,
)
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDoubleSpinBox,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QProgressBar,
    QPushButton,
    QSlider,
    QStatusBar,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

# ---------------------------------------------------------------------------
# Try to import the verasol driver; fall back to a stub for UI development
# ---------------------------------------------------------------------------
try:
    from verasol import CalibrationMode, LampStatus, LEDInfo, VeraSol, list_instruments
    DRIVER_AVAILABLE = True
except Exception as _import_err:  # noqa: BLE001
    DRIVER_AVAILABLE = False
    _IMPORT_ERROR = str(_import_err)

    # ---- Minimal stubs so the GUI can be laid out without hardware ----
    from dataclasses import dataclass
    from enum import Enum

    class CalibrationMode(str, Enum):
        DEFAULT = "DEFAULT"
        USER = "USER"

    @dataclass
    class LampStatus:
        output_on: bool = False
        head_disconnected: bool = True
        head_warming_up: bool = False
        head_overtemperature: bool = False
        raw: int = 4

    @dataclass
    class LEDInfo:
        index: int = 1
        wavelength_nm: float = 500.0
        power_kw_m2: float = 0.05
        max_power_kw_m2: float = 0.10

    def list_instruments():
        return []

    class VeraSol:  # type: ignore[no-redef]
        NUM_LEDS = 19
        def __init__(self, resource_name=None, timeout_ms=10000): pass
        def close(self): pass
        def identify(self): return "STUB,LSS-7120,00000000,0.00"
        def set_output(self, on): pass
        def get_output(self): return False
        def set_amplitude(self, suns): pass
        def get_amplitude(self): return 1.0
        def set_led_power(self, led, power): pass
        def get_led_power(self, led): return 0.05
        def get_led_max_power(self, led): return 0.10
        def get_led_wavelength(self, led): return 400 + (led - 1) * 37
        def get_led_info(self, led):
            return LEDInfo(led, 400 + (led-1)*37, 0.05, 0.10)
        def get_all_led_info(self):
            return [self.get_led_info(i) for i in range(1, self.NUM_LEDS + 1)]
        def store_spectrum(self, loc): pass
        def recall_spectrum(self, loc): pass
        def get_active_spectrum_location(self): return 0
        def set_calibration_mode(self, mode): pass
        def get_calibration_mode(self): return CalibrationMode.DEFAULT
        def perform_user_calibration(self): pass
        def get_status(self): return LampStatus()
        def get_errors(self): return []
        def run_led_test(self, timeout_s=60): return True
        def get_led_test_result(self, led): return (0.05, 0.05)


# ---------------------------------------------------------------------------
# Colour helpers
# ---------------------------------------------------------------------------

def _wavelength_to_rgb(nm: float) -> tuple[int, int, int]:
    """Rough perceptual colour for a given wavelength (400–1100 nm)."""
    if nm < 450:
        r, g, b = 120, 0, 220
    elif nm < 500:
        t = (nm - 450) / 50
        r, g, b = int(120 * (1 - t)), 0, int(220 + 35 * t)
    elif nm < 570:
        t = (nm - 500) / 70
        r, g, b = 0, int(200 * t), 255
    elif nm < 590:
        t = (nm - 570) / 20
        r, g, b = int(255 * t), 200, int(255 * (1 - t))
    elif nm < 625:
        t = (nm - 590) / 35
        r, g, b = 255, int(200 * (1 - t)), 0
    elif nm < 750:
        r, g, b = 200, 0, 0
    else:
        # Near-IR – shown as dark red / maroon
        v = max(60, int(180 - (nm - 750) / 3.5))
        r, g, b = v, 0, 0
    return r, g, b


# ---------------------------------------------------------------------------
# Worker thread – keeps all instrument I/O off the GUI thread
# ---------------------------------------------------------------------------

class InstrumentWorker(QObject):
    """Runs blocking VeraSol calls in a QThread."""

    # Signals emitted back to the GUI
    connected = Signal(str)          # IDN string
    disconnected = Signal()
    error = Signal(str)              # human-readable error message
    status_updated = Signal(object)  # LampStatus
    amplitude_updated = Signal(float)
    output_updated = Signal(bool)
    led_info_updated = Signal(list)  # list[LEDInfo]
    spectrum_location_updated = Signal(int)
    calibration_mode_updated = Signal(str)
    errors_received = Signal(list)   # list[str]
    led_test_finished = Signal(bool, list)  # (passed, list[tuple])
    log_message = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self._lamp: VeraSol | None = None

    # ---- connection ----

    @Slot(str)
    def connect(self, resource_name: str) -> None:
        try:
            self._lamp = VeraSol(resource_name or None)
            idn = self._lamp.identify()
            self.connected.emit(idn)
            self.log_message.emit(f"Connected: {idn}")
            self._refresh_all()
        except Exception as exc:
            self.error.emit(f"Connection failed: {exc}")
            self._lamp = None

    @Slot()
    def disconnect(self) -> None:
        if self._lamp:
            try:
                self._lamp.close()
            except Exception:
                pass
            self._lamp = None
        self.disconnected.emit()
        self.log_message.emit("Disconnected.")

    def _require_lamp(self) -> bool:
        if self._lamp is None:
            self.error.emit("Not connected to instrument.")
            return False
        return True

    def _refresh_all(self) -> None:
        self._refresh_status()
        self._refresh_amplitude()
        self._refresh_output()
        self._refresh_leds()
        self._refresh_spectrum()
        self._refresh_cal_mode()

    # ---- status poll ----

    @Slot()
    def poll_status(self) -> None:
        if not self._lamp:
            return
        try:
            self.status_updated.emit(self._lamp.get_status())
        except Exception as exc:
            self.log_message.emit(f"[poll] {exc}")

    def _refresh_status(self) -> None:
        try:
            self.status_updated.emit(self._lamp.get_status())
        except Exception:
            pass

    # ---- output ----

    @Slot(bool)
    def set_output(self, on: bool) -> None:
        if not self._require_lamp():
            return
        try:
            self._lamp.set_output(on)
            self.output_updated.emit(on)
            self.log_message.emit(f"Output {'ON' if on else 'OFF'}")
        except Exception as exc:
            self.error.emit(str(exc))

    def _refresh_output(self) -> None:
        try:
            self.output_updated.emit(self._lamp.get_output())
        except Exception:
            pass

    # ---- amplitude ----

    @Slot(float)
    def set_amplitude(self, suns: float) -> None:
        if not self._require_lamp():
            return
        try:
            self._lamp.set_amplitude(suns)
            self.amplitude_updated.emit(suns)
            self.log_message.emit(f"Amplitude set to {suns:.3f} sun(s)")
        except Exception as exc:
            self.error.emit(str(exc))

    def _refresh_amplitude(self) -> None:
        try:
            self.amplitude_updated.emit(self._lamp.get_amplitude())
        except Exception:
            pass

    # ---- LED power ----

    @Slot(int, float)
    def set_led_power(self, led: int, power: float) -> None:
        if not self._require_lamp():
            return
        try:
            self._lamp.set_led_power(led, power)
            self.log_message.emit(f"LED {led} power → {power:.4f} kW/m²")
        except Exception as exc:
            self.error.emit(str(exc))

    @Slot()
    def refresh_leds(self) -> None:
        self._refresh_leds()

    def _refresh_leds(self) -> None:
        if not self._lamp:
            return
        try:
            info = self._lamp.get_all_led_info()
            self.led_info_updated.emit(info)
        except Exception as exc:
            self.log_message.emit(f"[LED refresh] {exc}")

    # ---- spectrum ----

    @Slot(int)
    def recall_spectrum(self, location: int) -> None:
        if not self._require_lamp():
            return
        try:
            self._lamp.recall_spectrum(location)
            self._refresh_leds()
            self.spectrum_location_updated.emit(location)
            self.log_message.emit(f"Recalled spectrum from slot {location}")
        except Exception as exc:
            self.error.emit(str(exc))

    @Slot(int)
    def store_spectrum(self, location: int) -> None:
        if not self._require_lamp():
            return
        try:
            self._lamp.store_spectrum(location)
            self.log_message.emit(f"Stored spectrum to slot {location}")
        except Exception as exc:
            self.error.emit(str(exc))

    def _refresh_spectrum(self) -> None:
        try:
            self.spectrum_location_updated.emit(self._lamp.get_active_spectrum_location())
        except Exception:
            pass

    # ---- calibration ----

    @Slot(str)
    def set_calibration_mode(self, mode_str: str) -> None:
        if not self._require_lamp():
            return
        try:
            mode = CalibrationMode(mode_str)
            self._lamp.set_calibration_mode(mode)
            self.calibration_mode_updated.emit(mode_str)
            self.log_message.emit(f"Calibration mode → {mode_str}")
        except Exception as exc:
            self.error.emit(str(exc))

    @Slot()
    def perform_user_cal(self) -> None:
        if not self._require_lamp():
            return
        try:
            self._lamp.perform_user_calibration()
            self.log_message.emit("User calibration performed (output rescaled to 1.00 sun)")
        except Exception as exc:
            self.error.emit(str(exc))

    def _refresh_cal_mode(self) -> None:
        try:
            mode = self._lamp.get_calibration_mode()
            self.calibration_mode_updated.emit(mode.value)
        except Exception:
            pass

    # ---- errors ----

    @Slot()
    def fetch_errors(self) -> None:
        if not self._require_lamp():
            return
        try:
            errs = self._lamp.get_errors()
            self.errors_received.emit(errs)
            if errs:
                self.log_message.emit(f"Instrument errors: {'; '.join(errs)}")
            else:
                self.log_message.emit("No instrument errors queued.")
        except Exception as exc:
            self.error.emit(str(exc))

    # ---- LED self-test ----

    @Slot()
    def run_led_test(self) -> None:
        if not self._require_lamp():
            return
        try:
            self.log_message.emit("Running LED self-test (may take ~60 s)…")
            passed = self._lamp.run_led_test(timeout_s=90)
            results = []
            for i in range(1, self._lamp.NUM_LEDS + 1):
                try:
                    user_p, factory_p = self._lamp.get_led_test_result(i)
                    results.append((i, user_p, factory_p))
                except Exception:
                    results.append((i, None, None))
            self.led_test_finished.emit(passed, results)
            self.log_message.emit(f"LED test {'PASSED' if passed else 'FAILED'}")
        except Exception as exc:
            self.error.emit(str(exc))


# ---------------------------------------------------------------------------
# LED bar widget (mimics front-panel bargraph)
# ---------------------------------------------------------------------------

class _SegmentBar(QWidget):
    """Clickable vertical power bar drawn with QPainter."""

    clicked = Signal(float)   # emits fraction 0.0–1.0

    def __init__(self, color: QColor, segments: int = 10, parent=None) -> None:
        super().__init__(parent)
        self._color = color
        self._n = segments
        self._filled = 0
        self._output_on = False
        self.setFixedWidth(28)
        self.setCursor(Qt.PointingHandCursor)

    def set_state(self, filled: int, output_on: bool) -> None:
        if filled != self._filled or output_on != self._output_on:
            self._filled = filled
            self._output_on = output_on
            self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        h, w, n = self.height(), self.width(), self._n
        g = 1  # gap between segments
        seg_h = (h - g * (n - 1)) / n
        on_color = self._color if self._output_on else QColor(180, 100, 0)
        off_color = QColor(40, 40, 40)
        for i in range(n):
            y = int(h - (i + 1) * seg_h - i * g)
            sh = max(1, int(seg_h))
            painter.fillRect(0, y, w, sh, on_color if i < self._filled else off_color)

    def _fraction(self, y: float) -> float:
        return max(0.0, min(1.0, 1.0 - y / max(1, self.height())))

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self._fraction(event.position().y()))

    def mouseMoveEvent(self, event) -> None:
        if event.buttons() & Qt.LeftButton:
            self.clicked.emit(self._fraction(event.position().y()))


class LEDBarWidget(QWidget):
    """A vertical bar + label representing one LED channel."""

    power_changed = Signal(int, float)   # (led_index, new_power_kw_m2)

    SEGMENTS = 10

    def __init__(self, led_info: LEDInfo, parent=None) -> None:
        super().__init__(parent)
        self._index = led_info.index
        self._max_power = led_info.max_power_kw_m2 or 0.10
        self._current_power = led_info.power_kw_m2
        self._output_on = False

        r, g, b = _wavelength_to_rgb(led_info.wavelength_nm)
        self._color = QColor(r, g, b)
        self._wavelength = led_info.wavelength_nm

        self._build_ui()
        self.refresh(led_info, output_on=False)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 4, 2, 4)
        layout.setSpacing(2)

        # Wavelength label
        self._wl_label = QLabel(f"{int(self._wavelength)}")
        self._wl_label.setAlignment(Qt.AlignCenter)
        font = QFont()
        font.setPointSize(7)
        self._wl_label.setFont(font)
        layout.addWidget(self._wl_label)

        # Clickable painted segment bar
        self._bar = _SegmentBar(self._color, self.SEGMENTS)
        self._bar.clicked.connect(self._on_bar_clicked)
        layout.addWidget(self._bar, stretch=1)

        # Spinbox for precise control
        self._spinbox = QDoubleSpinBox()
        self._spinbox.setDecimals(4)
        self._spinbox.setRange(0.0, self._max_power)
        self._spinbox.setSingleStep(0.001)
        self._spinbox.setValue(self._current_power)
        self._spinbox.setFixedWidth(72)
        font2 = QFont()
        font2.setPointSize(7)
        self._spinbox.setFont(font2)
        self._spinbox.valueChanged.connect(self._on_spinbox_changed)
        layout.addWidget(self._spinbox, alignment=Qt.AlignCenter)

        # LED index label
        idx_label = QLabel(f"#{self._index}")
        idx_label.setAlignment(Qt.AlignCenter)
        idx_label.setFont(font)
        layout.addWidget(idx_label)

        self.setFixedWidth(80)

    def _on_spinbox_changed(self, value: float) -> None:
        self._current_power = value
        self._update_bar()
        self.power_changed.emit(self._index, value)

    def _on_bar_clicked(self, fraction: float) -> None:
        self._spinbox.setValue(round(fraction * self._max_power, 4))

    def refresh(self, info: LEDInfo, output_on: bool) -> None:
        self._output_on = output_on
        self._max_power = info.max_power_kw_m2 or 0.10
        self._current_power = info.power_kw_m2
        self._spinbox.blockSignals(True)
        self._spinbox.setMaximum(self._max_power)
        self._spinbox.setValue(self._current_power)
        self._spinbox.blockSignals(False)
        self._update_bar()

    def set_output_on(self, on: bool) -> None:
        self._output_on = on
        self._update_bar()

    def _update_bar(self) -> None:
        fraction = (
            self._current_power / self._max_power if self._max_power > 0 else 0.0
        )
        self._bar.set_state(round(fraction * self.SEGMENTS), self._output_on)


# ---------------------------------------------------------------------------
# Connection panel
# ---------------------------------------------------------------------------

class ConnectionPanel(QGroupBox):
    connect_requested = Signal(str)
    disconnect_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__("Connection", parent)
        layout = QHBoxLayout(self)

        self._resource_combo = QComboBox()
        self._resource_combo.setEditable(True)
        self._resource_combo.setPlaceholderText("VISA resource  (blank = auto-detect)")
        self._resource_combo.setMinimumWidth(280)

        self._scan_btn = QPushButton("Scan")
        self._scan_btn.setFixedWidth(60)
        self._scan_btn.clicked.connect(self._scan)

        self._connect_btn = QPushButton("Connect")
        self._connect_btn.setFixedWidth(80)
        self._connect_btn.clicked.connect(self._on_connect)

        self._disconnect_btn = QPushButton("Disconnect")
        self._disconnect_btn.setFixedWidth(90)
        self._disconnect_btn.setEnabled(False)
        self._disconnect_btn.clicked.connect(self.disconnect_requested)

        self._idn_label = QLabel("—")
        self._idn_label.setStyleSheet("color: #888;")

        layout.addWidget(QLabel("Resource:"))
        layout.addWidget(self._resource_combo)
        layout.addWidget(self._scan_btn)
        layout.addWidget(self._connect_btn)
        layout.addWidget(self._disconnect_btn)
        layout.addWidget(QLabel("ID:"))
        layout.addWidget(self._idn_label, stretch=1)

    def _scan(self) -> None:
        resources = list_instruments()
        self._resource_combo.clear()
        if resources:
            self._resource_combo.addItems(resources)
        else:
            self._resource_combo.setPlaceholderText("No USB INSTR found")

    def _on_connect(self) -> None:
        resource = self._resource_combo.currentText().strip()
        self.connect_requested.emit(resource)

    def set_connected(self, idn: str) -> None:
        self._idn_label.setText(idn)
        self._idn_label.setStyleSheet("color: #2ecc71; font-weight: bold;")
        self._connect_btn.setEnabled(False)
        self._disconnect_btn.setEnabled(True)

    def set_disconnected(self) -> None:
        self._idn_label.setText("—")
        self._idn_label.setStyleSheet("color: #888;")
        self._connect_btn.setEnabled(True)
        self._disconnect_btn.setEnabled(False)


# ---------------------------------------------------------------------------
# Status panel
# ---------------------------------------------------------------------------

class StatusPanel(QGroupBox):
    def __init__(self, parent=None) -> None:
        super().__init__("Instrument Status", parent)
        layout = QHBoxLayout(self)

        def _indicator(label: str) -> tuple[QLabel, QLabel]:
            lbl = QLabel(label)
            dot = QLabel("●")
            dot.setStyleSheet("color: #555; font-size: 18px;")
            layout.addWidget(dot)
            layout.addWidget(lbl)
            layout.addSpacing(16)
            return lbl, dot

        _, self._dot_output = _indicator("Output ON")
        _, self._dot_head = _indicator("Head OK")
        _, self._dot_warm = _indicator("Warm")
        _, self._dot_temp = _indicator("Temp OK")

        self._raw_label = QLabel("raw=—")
        self._raw_label.setStyleSheet("color: #555; font-size: 10px;")
        layout.addStretch()
        layout.addWidget(self._raw_label)

        self._apply_disconnected()

    def _apply_disconnected(self) -> None:
        for dot in (self._dot_output, self._dot_head, self._dot_warm, self._dot_temp):
            dot.setStyleSheet("color: #555; font-size: 18px;")
        self._raw_label.setText("raw=—")

    def update_status(self, status: LampStatus) -> None:
        def _color(ok: bool, true_color: str = "#2ecc71", false_color: str = "#e74c3c") -> str:
            return true_color if ok else false_color

        self._dot_output.setStyleSheet(
            f"color: {_color(status.output_on)}; font-size: 18px;"
        )
        self._dot_head.setStyleSheet(
            f"color: {_color(not status.head_disconnected)}; font-size: 18px;"
        )
        self._dot_warm.setStyleSheet(
            f"color: {_color(not status.head_warming_up, '#2ecc71', '#f39c12')}; font-size: 18px;"
        )
        self._dot_temp.setStyleSheet(
            f"color: {_color(not status.head_overtemperature)}; font-size: 18px;"
        )
        self._raw_label.setText(f"raw={status.raw}")

    def clear(self) -> None:
        self._apply_disconnected()


# ---------------------------------------------------------------------------
# Main output control tab
# ---------------------------------------------------------------------------

class OutputTab(QWidget):
    output_toggled = Signal(bool)
    amplitude_set = Signal(float)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        # --- Output on/off ---
        out_group = QGroupBox("Output")
        out_layout = QHBoxLayout(out_group)

        self._output_btn = QPushButton("OUTPUT  OFF")
        self._output_btn.setCheckable(True)
        self._output_btn.setFixedHeight(52)
        font = QFont()
        font.setPointSize(14)
        font.setBold(True)
        self._output_btn.setFont(font)
        self._output_btn.setStyleSheet(
            "QPushButton { background: #555; color: white; border-radius: 8px; }"
            "QPushButton:checked { background: #2ecc71; color: black; }"
        )
        self._output_btn.toggled.connect(self._on_output_toggled)
        out_layout.addWidget(self._output_btn)
        layout.addWidget(out_group)

        # --- Amplitude ---
        amp_group = QGroupBox("Intensity (Amplitude)")
        amp_layout = QVBoxLayout(amp_group)

        self._amp_label = QLabel("1.000 sun(s)  =  1.000 kW/m²")
        self._amp_label.setAlignment(Qt.AlignCenter)
        font2 = QFont()
        font2.setPointSize(16)
        font2.setBold(True)
        self._amp_label.setFont(font2)
        amp_layout.addWidget(self._amp_label)

        self._amp_slider = QSlider(Qt.Horizontal)
        self._amp_slider.setRange(100, 1000)   # 0.100 – 1.000 suns × 1000
        self._amp_slider.setValue(1000)
        self._amp_slider.setTickInterval(100)
        self._amp_slider.setTickPosition(QSlider.TicksBelow)
        self._amp_slider.valueChanged.connect(self._on_slider_changed)
        amp_layout.addWidget(self._amp_slider)

        slider_labels = QWidget()
        sl_layout = QHBoxLayout(slider_labels)
        sl_layout.setContentsMargins(0, 0, 0, 0)
        sl_layout.addWidget(QLabel("0.1 sun"))
        sl_layout.addStretch()
        sl_layout.addWidget(QLabel("1.0 sun"))
        amp_layout.addWidget(slider_labels)

        fine_row = QHBoxLayout()
        fine_row.addWidget(QLabel("Fine:"))
        self._amp_spin = QDoubleSpinBox()
        self._amp_spin.setRange(0.100, 1.000)
        self._amp_spin.setDecimals(3)
        self._amp_spin.setSingleStep(0.010)
        self._amp_spin.setValue(1.000)
        self._amp_spin.setSuffix(" sun(s)")
        self._amp_spin.valueChanged.connect(self._on_spin_changed)
        fine_row.addWidget(self._amp_spin)
        fine_row.addStretch()
        self._apply_amp_btn = QPushButton("Apply")
        self._apply_amp_btn.setFixedWidth(80)
        self._apply_amp_btn.clicked.connect(self._emit_amplitude)
        fine_row.addWidget(self._apply_amp_btn)
        amp_layout.addLayout(fine_row)

        layout.addWidget(amp_group)
        layout.addStretch()

    # ---- internal ----

    def _on_slider_changed(self, value: int) -> None:
        suns = value / 1000.0
        self._amp_spin.blockSignals(True)
        self._amp_spin.setValue(suns)
        self._amp_spin.blockSignals(False)
        self._amp_label.setText(f"{suns:.3f} sun(s)  =  {suns:.3f} kW/m²")

    def _on_spin_changed(self, value: float) -> None:
        self._amp_slider.blockSignals(True)
        self._amp_slider.setValue(int(round(value * 1000)))
        self._amp_slider.blockSignals(False)
        self._amp_label.setText(f"{value:.3f} sun(s)  =  {value:.3f} kW/m²")

    def _on_output_toggled(self, checked: bool) -> None:
        self._output_btn.setText(f"OUTPUT  {'ON' if checked else 'OFF'}")
        self.output_toggled.emit(checked)

    def _emit_amplitude(self) -> None:
        self.amplitude_set.emit(self._amp_spin.value())

    # ---- public setters called from main window ----

    def set_output_state(self, on: bool) -> None:
        self._output_btn.blockSignals(True)
        self._output_btn.setChecked(on)
        self._output_btn.setText(f"OUTPUT  {'ON' if on else 'OFF'}")
        self._output_btn.blockSignals(False)

    def set_amplitude(self, suns: float) -> None:
        # If the instrument reports a value above the current widget max (e.g.
        # after user calibration), expand the range so arrow-up still works.
        if suns > self._amp_spin.maximum():
            self._amp_spin.setMaximum(suns)
            self._amp_slider.setMaximum(int(round(suns * 1000)))
        self._amp_spin.blockSignals(True)
        self._amp_slider.blockSignals(True)
        self._amp_spin.setValue(suns)
        self._amp_slider.setValue(int(round(suns * 1000)))
        self._amp_spin.blockSignals(False)
        self._amp_slider.blockSignals(False)
        self._amp_label.setText(f"{suns:.3f} sun(s)  =  {suns:.3f} kW/m²")


# ---------------------------------------------------------------------------
# LED spectrum tab
# ---------------------------------------------------------------------------

class SpectrumTab(QWidget):
    led_power_changed = Signal(int, float)

    def __init__(self, num_leds: int = 19, parent=None) -> None:
        super().__init__(parent)
        self._num_leds = num_leds
        self._bars: list[LEDBarWidget] = []
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        info = QLabel(
            "Drag spinboxes to adjust individual LED power (kW/m²). "
            "Changes are sent to the instrument immediately."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: #aaa; font-size: 11px;")
        layout.addWidget(info)

        bar_area = QWidget()
        bar_layout = QHBoxLayout(bar_area)
        bar_layout.setSpacing(4)
        bar_layout.setContentsMargins(4, 4, 4, 4)

        # Placeholder LED infos until we get real data
        placeholder = [
            LEDInfo(
                index=i,
                wavelength_nm=400 + (i - 1) * 37,
                power_kw_m2=0.05,
                max_power_kw_m2=0.10,
            )
            for i in range(1, self._num_leds + 1)
        ]
        for info_item in placeholder:
            bar = LEDBarWidget(info_item)
            bar.power_changed.connect(self.led_power_changed)
            self._bars.append(bar)
            bar_layout.addWidget(bar)

        bar_layout.addStretch()
        layout.addWidget(bar_area)

        # nm axis label
        nm_label = QLabel("← 400 nm  ·····  visible spectrum  ·····  1100 nm →    (NIR)")
        nm_label.setAlignment(Qt.AlignCenter)
        nm_label.setStyleSheet("color: #888; font-size: 10px;")
        layout.addWidget(nm_label)

    def refresh_leds(self, infos: list, output_on: bool = False) -> None:
        for info in infos:
            idx = info.index - 1
            if 0 <= idx < len(self._bars):
                self._bars[idx].refresh(info, output_on)

    def set_output_on(self, on: bool) -> None:
        for bar in self._bars:
            bar.set_output_on(on)


# ---------------------------------------------------------------------------
# Spectrum memory tab
# ---------------------------------------------------------------------------

class SpectrumMemoryTab(QWidget):
    recall_requested = Signal(int)
    store_requested = Signal(int)

    _LOCATION_LABELS = {
        0: "0 — Factory AM1.5G (read-only)",
        1: "1 — Custom (front-panel accessible)",
        **{i: f"{i} — User slot {i}" for i in range(2, 11)},
    }

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Active spectrum display
        active_row = QHBoxLayout()
        active_row.addWidget(QLabel("Active spectrum location:"))
        self._active_label = QLabel("—")
        self._active_label.setStyleSheet("font-weight: bold; color: #2ecc71;")
        active_row.addWidget(self._active_label)
        active_row.addStretch()
        layout.addLayout(active_row)

        # Recall
        recall_group = QGroupBox("Recall Spectrum")
        recall_layout = QHBoxLayout(recall_group)
        recall_layout.addWidget(QLabel("Load from location:"))
        self._recall_combo = QComboBox()
        for loc, label in self._LOCATION_LABELS.items():
            self._recall_combo.addItem(label, userData=loc)
        recall_layout.addWidget(self._recall_combo, stretch=1)
        recall_btn = QPushButton("Recall")
        recall_btn.setFixedWidth(80)
        recall_btn.clicked.connect(self._on_recall)
        recall_layout.addWidget(recall_btn)
        layout.addWidget(recall_group)

        # Store
        store_group = QGroupBox("Store Current Spectrum")
        store_layout = QHBoxLayout(store_group)
        store_layout.addWidget(QLabel("Save to location:"))
        self._store_combo = QComboBox()
        for loc in range(1, 11):
            self._store_combo.addItem(self._LOCATION_LABELS[loc], userData=loc)
        store_layout.addWidget(self._store_combo, stretch=1)
        store_btn = QPushButton("Store")
        store_btn.setFixedWidth(80)
        store_btn.clicked.connect(self._on_store)
        store_layout.addWidget(store_btn)
        layout.addWidget(store_group)

        # Quick access
        quick_group = QGroupBox("Quick Access")
        quick_layout = QHBoxLayout(quick_group)
        am15_btn = QPushButton("Recall AM1.5G (slot 0)")
        am15_btn.clicked.connect(lambda: self.recall_requested.emit(0))
        custom_btn = QPushButton("Recall Custom (slot 1)")
        custom_btn.clicked.connect(lambda: self.recall_requested.emit(1))
        quick_layout.addWidget(am15_btn)
        quick_layout.addWidget(custom_btn)
        layout.addWidget(quick_group)

        layout.addStretch()

    def _on_recall(self) -> None:
        loc = self._recall_combo.currentData()
        self.recall_requested.emit(loc)

    def _on_store(self) -> None:
        loc = self._store_combo.currentData()
        self.store_requested.emit(loc)

    def set_active_location(self, loc: int) -> None:
        label = self._LOCATION_LABELS.get(loc, str(loc))
        self._active_label.setText(label)


# ---------------------------------------------------------------------------
# Calibration tab
# ---------------------------------------------------------------------------

class CalibrationTab(QWidget):
    cal_mode_changed = Signal(str)
    perform_cal_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        # Mode selector
        mode_group = QGroupBox("Intensity Calibration Mode")
        mode_layout = QHBoxLayout(mode_group)
        mode_layout.addWidget(QLabel("Active mode:"))
        self._mode_combo = QComboBox()
        self._mode_combo.addItem("Factory Default (DEFAULT)", userData="DEFAULT")
        self._mode_combo.addItem("User Offset (USER)", userData="USER")
        self._mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        mode_layout.addWidget(self._mode_combo)
        mode_layout.addStretch()
        layout.addWidget(mode_group)

        # User cal
        usercal_group = QGroupBox("Perform User Calibration")
        usercal_layout = QVBoxLayout(usercal_group)
        desc = QLabel(
            "Place your reference sample under the head, adjust the output until "
            "your meter reads 1.00 sun, then press the button below. The controller "
            "will rescale its display to 1.00 sun at the current set point."
        )
        desc.setWordWrap(True)
        usercal_layout.addWidget(desc)
        self._perform_btn = QPushButton("Execute User Calibration  (USERCAL:PERFORM)")
        self._perform_btn.setFixedHeight(40)
        self._perform_btn.clicked.connect(self.perform_cal_requested)
        usercal_layout.addWidget(self._perform_btn)
        layout.addWidget(usercal_group)

        layout.addStretch()

    def _on_mode_changed(self) -> None:
        self.cal_mode_changed.emit(self._mode_combo.currentData())

    def set_calibration_mode(self, mode_str: str) -> None:
        self._mode_combo.blockSignals(True)
        for i in range(self._mode_combo.count()):
            if self._mode_combo.itemData(i) == mode_str:
                self._mode_combo.setCurrentIndex(i)
                break
        self._mode_combo.blockSignals(False)


# ---------------------------------------------------------------------------
# Diagnostics tab
# ---------------------------------------------------------------------------

class DiagnosticsTab(QWidget):
    fetch_errors_requested = Signal()
    led_test_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Error queue
        err_group = QGroupBox("Instrument Error Queue")
        err_layout = QVBoxLayout(err_group)
        self._errors_text = QTextEdit()
        self._errors_text.setReadOnly(True)
        self._errors_text.setMaximumHeight(100)
        self._errors_text.setPlaceholderText("Press 'Fetch Errors' to query the error queue…")
        err_layout.addWidget(self._errors_text)
        fetch_btn = QPushButton("Fetch Errors  (ERROR?)")
        fetch_btn.clicked.connect(self.fetch_errors_requested)
        err_layout.addWidget(fetch_btn)
        layout.addWidget(err_group)

        # LED self-test
        test_group = QGroupBox("LED Self-Test  (LEDTEST:POWER?)")
        test_layout = QVBoxLayout(test_group)
        note = QLabel(
            "The self-test cycles through all LEDs, measuring power at each wavelength. "
            "This takes ~60 seconds. Do not adjust settings during the test."
        )
        note.setWordWrap(True)
        test_layout.addWidget(note)

        self._test_btn = QPushButton("Run LED Self-Test")
        self._test_btn.clicked.connect(self._on_run_test)
        test_layout.addWidget(self._test_btn)

        self._test_progress = QProgressBar()
        self._test_progress.setVisible(False)
        test_layout.addWidget(self._test_progress)

        self._test_result_label = QLabel("")
        test_layout.addWidget(self._test_result_label)

        # Results table
        self._results_table = QTableWidget(0, 4)
        self._results_table.setHorizontalHeaderLabels(
            ["LED #", "Wavelength (nm)", "User Power (kW/m²)", "Factory Power (kW/m²)"]
        )
        self._results_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._results_table.setEditTriggers(QTableWidget.NoEditTriggers)
        test_layout.addWidget(self._results_table)
        layout.addWidget(test_group)

    def _on_run_test(self) -> None:
        self._test_btn.setEnabled(False)
        self._test_progress.setVisible(True)
        self._test_progress.setRange(0, 0)   # indeterminate
        self._test_result_label.setText("Running…")
        self.led_test_requested.emit()

    def show_errors(self, errors: list[str]) -> None:
        if errors:
            self._errors_text.setPlainText("\n".join(errors))
            self._errors_text.setStyleSheet("color: #e74c3c;")
        else:
            self._errors_text.setPlainText("No errors.")
            self._errors_text.setStyleSheet("color: #2ecc71;")

    def show_test_results(self, passed: bool, results: list) -> None:
        self._test_btn.setEnabled(True)
        self._test_progress.setVisible(False)
        status = "✓ PASSED" if passed else "✗ FAILED"
        color = "#2ecc71" if passed else "#e74c3c"
        self._test_result_label.setText(f"Result: {status}")
        self._test_result_label.setStyleSheet(f"color: {color}; font-weight: bold;")

        self._results_table.setRowCount(len(results))
        for row, item in enumerate(results):
            led_idx, user_p, factory_p = item
            self._results_table.setItem(row, 0, QTableWidgetItem(str(led_idx)))
            # Wavelength not available here; would need a separate query
            self._results_table.setItem(row, 1, QTableWidgetItem("—"))
            up = f"{user_p:.4f}" if user_p is not None else "—"
            fp = f"{factory_p:.4f}" if factory_p is not None else "—"
            self._results_table.setItem(row, 2, QTableWidgetItem(up))
            self._results_table.setItem(row, 3, QTableWidgetItem(fp))
            # Colour rows where user < factory
            if user_p is not None and factory_p is not None and user_p < factory_p * 0.95:
                for col in range(4):
                    cell = self._results_table.item(row, col)
                    if cell:
                        cell.setBackground(QColor(80, 30, 30))


# ---------------------------------------------------------------------------
# Activity log panel
# ---------------------------------------------------------------------------

class LogPanel(QGroupBox):
    def __init__(self, parent=None) -> None:
        super().__init__("Activity Log", parent)
        layout = QVBoxLayout(self)
        self._log = QTextEdit()
        self._log.setReadOnly(True)
        self._log.setMaximumHeight(130)
        font = QFont("Courier", 9)
        self._log.setFont(font)
        layout.addWidget(self._log)
        clear_btn = QPushButton("Clear")
        clear_btn.setFixedWidth(60)
        clear_btn.clicked.connect(self._log.clear)
        h = QHBoxLayout()
        h.addStretch()
        h.addWidget(clear_btn)
        layout.addLayout(h)

    def append(self, msg: str) -> None:
        self._log.append(msg)
        self._log.verticalScrollBar().setValue(
            self._log.verticalScrollBar().maximum()
        )


# ---------------------------------------------------------------------------
# Main window
# ---------------------------------------------------------------------------

class MainWindow(QMainWindow):
    # Signals sent to the worker (must be defined at class level)
    _sig_connect = Signal(str)
    _sig_disconnect = Signal()
    _sig_set_output = Signal(bool)
    _sig_set_amplitude = Signal(float)
    _sig_set_led_power = Signal(int, float)
    _sig_refresh_leds = Signal()
    _sig_recall_spectrum = Signal(int)
    _sig_store_spectrum = Signal(int)
    _sig_set_cal_mode = Signal(str)
    _sig_perform_cal = Signal()
    _sig_fetch_errors = Signal()
    _sig_run_led_test = Signal()
    _sig_poll_status = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("VeraSol LSS-7120 — LED Solar Simulator Control Panel")
        self.setMinimumSize(1100, 720)

        self._connected = False
        self._output_on = False

        self._build_ui()
        self._setup_worker()
        self._setup_poll_timer()

        if not DRIVER_AVAILABLE:
            self._log.append(
                f"[WARNING] verasol driver not available: {_IMPORT_ERROR}\n"
                "Running in stub mode — UI layout only."
            )

    # ---- UI construction ----

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setSpacing(8)

        # Connection bar
        self._conn_panel = ConnectionPanel()
        self._conn_panel.connect_requested.connect(self._on_connect_requested)
        self._conn_panel.disconnect_requested.connect(self._on_disconnect_requested)
        root.addWidget(self._conn_panel)

        # Status bar
        self._status_panel = StatusPanel()
        root.addWidget(self._status_panel)

        # Tab area
        self._tabs = QTabWidget()
        self._tabs.setEnabled(False)   # disabled until connected

        self._output_tab = OutputTab()
        self._output_tab.output_toggled.connect(self._on_output_toggled)
        self._output_tab.amplitude_set.connect(self._on_amplitude_set)
        self._tabs.addTab(self._output_tab, "⚡ Output")

        self._spectrum_tab = SpectrumTab(num_leds=VeraSol.NUM_LEDS)
        self._spectrum_tab.led_power_changed.connect(self._on_led_power_changed)
        self._tabs.addTab(self._spectrum_tab, "🌈 LED Spectrum")

        self._mem_tab = SpectrumMemoryTab()
        self._mem_tab.recall_requested.connect(self._sig_recall_spectrum)
        self._mem_tab.store_requested.connect(self._sig_store_spectrum)
        self._tabs.addTab(self._mem_tab, "💾 Spectrum Memory")

        self._cal_tab = CalibrationTab()
        self._cal_tab.cal_mode_changed.connect(self._sig_set_cal_mode)
        self._cal_tab.perform_cal_requested.connect(self._sig_perform_cal)
        self._tabs.addTab(self._cal_tab, "🔧 Calibration")

        self._diag_tab = DiagnosticsTab()
        self._diag_tab.fetch_errors_requested.connect(self._sig_fetch_errors)
        self._diag_tab.led_test_requested.connect(self._sig_run_led_test)
        self._tabs.addTab(self._diag_tab, "🔬 Diagnostics")

        root.addWidget(self._tabs, stretch=1)

        # Log panel
        self._log = LogPanel()
        root.addWidget(self._log)

        # Status bar
        self._statusbar = QStatusBar()
        self.setStatusBar(self._statusbar)
        self._statusbar.showMessage("Not connected.")

        self._apply_dark_theme()

    def _apply_dark_theme(self) -> None:
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #1e1e2e;
                color: #cdd6f4;
            }
            QGroupBox {
                border: 1px solid #45475a;
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 6px;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                color: #89b4fa;
            }
            QTabWidget::pane {
                border: 1px solid #45475a;
                border-radius: 4px;
            }
            QTabBar::tab {
                background: #313244;
                color: #cdd6f4;
                padding: 6px 14px;
                margin-right: 2px;
                border-radius: 4px 4px 0 0;
            }
            QTabBar::tab:selected {
                background: #45475a;
                color: #cba6f7;
                font-weight: bold;
            }
            QPushButton {
                background-color: #313244;
                color: #cdd6f4;
                border: 1px solid #45475a;
                border-radius: 4px;
                padding: 4px 10px;
            }
            QPushButton:hover { background-color: #45475a; }
            QPushButton:pressed { background-color: #585b70; }
            QPushButton:disabled { color: #585b70; }
            QSlider::groove:horizontal {
                height: 8px;
                background: #313244;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #89b4fa;
                border: none;
                width: 18px;
                height: 18px;
                margin: -5px 0;
                border-radius: 9px;
            }
            QSlider::sub-page:horizontal { background: #89b4fa; border-radius: 4px; }
            QDoubleSpinBox, QSpinBox, QComboBox, QTextEdit {
                background-color: #313244;
                color: #cdd6f4;
                border: 1px solid #45475a;
                border-radius: 4px;
                padding: 2px 4px;
            }
            QTableWidget {
                background-color: #181825;
                gridline-color: #45475a;
            }
            QHeaderView::section {
                background-color: #313244;
                color: #89b4fa;
                border: none;
                padding: 4px;
            }
            QProgressBar {
                background: #313244;
                border: 1px solid #45475a;
                border-radius: 4px;
                text-align: center;
            }
            QProgressBar::chunk { background: #89b4fa; border-radius: 4px; }
        """)

    # ---- Worker / thread setup ----

    def _setup_worker(self) -> None:
        self._thread = QThread()
        self._worker = InstrumentWorker()
        self._worker.moveToThread(self._thread)
        self._thread.start()

        # Wire signals → worker slots
        self._sig_connect.connect(self._worker.connect)
        self._sig_disconnect.connect(self._worker.disconnect)
        self._sig_set_output.connect(self._worker.set_output)
        self._sig_set_amplitude.connect(self._worker.set_amplitude)
        self._sig_set_led_power.connect(self._worker.set_led_power)
        self._sig_refresh_leds.connect(self._worker.refresh_leds)
        self._sig_recall_spectrum.connect(self._worker.recall_spectrum)
        self._sig_store_spectrum.connect(self._worker.store_spectrum)
        self._sig_set_cal_mode.connect(self._worker.set_calibration_mode)
        self._sig_perform_cal.connect(self._worker.perform_user_cal)
        self._sig_fetch_errors.connect(self._worker.fetch_errors)
        self._sig_run_led_test.connect(self._worker.run_led_test)
        self._sig_poll_status.connect(self._worker.poll_status)

        # Wire worker signals → GUI slots
        self._worker.connected.connect(self._on_connected)
        self._worker.disconnected.connect(self._on_disconnected)
        self._worker.error.connect(self._on_error)
        self._worker.log_message.connect(self._log.append)
        self._worker.status_updated.connect(self._on_status_updated)
        self._worker.amplitude_updated.connect(self._output_tab.set_amplitude)
        self._worker.output_updated.connect(self._on_output_updated)
        self._worker.led_info_updated.connect(self._on_led_info_updated)
        self._worker.spectrum_location_updated.connect(self._mem_tab.set_active_location)
        self._worker.calibration_mode_updated.connect(self._cal_tab.set_calibration_mode)
        self._worker.errors_received.connect(self._diag_tab.show_errors)
        self._worker.led_test_finished.connect(self._diag_tab.show_test_results)

    def _setup_poll_timer(self) -> None:
        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(2000)   # 2-second status poll
        self._poll_timer.timeout.connect(self._sig_poll_status)

    # ---- Slots: connection ----

    def _on_connect_requested(self, resource: str) -> None:
        self._statusbar.showMessage("Connecting…")
        self._sig_connect.emit(resource)

    def _on_disconnect_requested(self) -> None:
        self._poll_timer.stop()
        self._sig_disconnect.emit()

    @Slot(str)
    def _on_connected(self, idn: str) -> None:
        self._connected = True
        self._conn_panel.set_connected(idn)
        self._tabs.setEnabled(True)
        self._poll_timer.start()
        self._statusbar.showMessage(f"Connected — {idn}")

    @Slot()
    def _on_disconnected(self) -> None:
        self._connected = False
        self._conn_panel.set_disconnected()
        self._tabs.setEnabled(False)
        self._status_panel.clear()
        self._statusbar.showMessage("Disconnected.")

    # ---- Slots: instrument events ----

    @Slot(str)
    def _on_error(self, msg: str) -> None:
        self._log.append(f"[ERROR] {msg}")
        self._statusbar.showMessage(f"Error: {msg}", 5000)

    @Slot(object)
    def _on_status_updated(self, status: LampStatus) -> None:
        self._status_panel.update_status(status)
        # Sync output button state without re-sending the command
        if status.output_on != self._output_on:
            self._output_on = status.output_on
            self._output_tab.set_output_state(self._output_on)
            self._spectrum_tab.set_output_on(self._output_on)
        # Warn if head is over-temperature
        if status.head_overtemperature:
            self._statusbar.showMessage("⚠  Head over-temperature!", 4000)
        elif status.head_disconnected:
            self._statusbar.showMessage("⚠  Head disconnected — check CC720 cable", 4000)

    @Slot(bool)
    def _on_output_updated(self, on: bool) -> None:
        self._output_on = on
        self._output_tab.set_output_state(on)
        self._spectrum_tab.set_output_on(on)

    @Slot(list)
    def _on_led_info_updated(self, infos: list) -> None:
        self._spectrum_tab.refresh_leds(infos, output_on=self._output_on)

    # ---- Slots: user actions ----

    def _on_output_toggled(self, on: bool) -> None:
        self._sig_set_output.emit(on)

    def _on_amplitude_set(self, suns: float) -> None:
        self._sig_set_amplitude.emit(suns)

    def _on_led_power_changed(self, led: int, power: float) -> None:
        self._sig_set_led_power.emit(led, power)

    # ---- Cleanup ----

    def closeEvent(self, event) -> None:
        self._poll_timer.stop()
        if self._connected:
            self._sig_disconnect.emit()
        self._thread.quit()
        self._thread.wait(3000)
        event.accept()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("VeraSol Control Panel")
    app.setOrganizationName("Oriel Instruments / EPFL-LPI")

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
