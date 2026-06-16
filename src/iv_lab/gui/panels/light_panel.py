"""Light level panel (legacy ``createLightLevelGroupBox``).

Two stacked variants, as in legacy: a drop-down of configured light
levels (lamp with a ``lightLevelDict``) or a manual entry field (manual
lamp), plus the measured-intensity label.
"""

from __future__ import annotations

from PySide6.QtGui import QDoubleValidator
from PySide6.QtWidgets import (
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)


class LightLevelPanel(QGroupBox):
    """Light level selection (menu or manual) and measured intensity."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("Light Level", parent)

        # drop-down variant
        self.menu_light_level = QComboBox()
        self.menu_light_level.setMaximumWidth(300)
        #: Display text -> light level in % sun (legacy lightLevelDictionary).
        self.light_level_dictionary: dict[str, float] = {}

        drop_down_panel = QWidget()
        drop_down_layout = QHBoxLayout()
        drop_down_layout.addWidget(self.menu_light_level)
        drop_down_panel.setLayout(drop_down_layout)

        # manual variant (legacy default "100.00")
        self.field_manual_light_level = QLineEdit("100.00")
        self.field_manual_light_level.setValidator(QDoubleValidator())

        manual_panel = QWidget()
        manual_layout = QHBoxLayout()
        manual_layout.addWidget(QLabel("Manual Light Level: "))
        manual_layout.addWidget(self.field_manual_light_level)
        manual_layout.addWidget(QLabel("% sun"))
        manual_panel.setLayout(manual_layout)

        self.stack = QStackedWidget()
        self.stack.addWidget(drop_down_panel)
        self.stack.addWidget(manual_panel)
        self.stack.setCurrentIndex(0)
        self.manual_mode = False

        self.label_measured_intensity = QLabel(
            "Measured Light Intensity: ---.--% sun"
        )

        layout = QVBoxLayout()
        layout.addWidget(self.stack)
        layout.addWidget(self.label_measured_intensity)
        self.setLayout(layout)
        self.setMaximumWidth(300)
        self.setEnabled(False)

    # --- legacy interface ---

    def set_manual_mode(self) -> None:
        """Legacy ``setLightLevelModeManual`` (manual lamp)."""
        self.stack.setCurrentIndex(1)
        self.manual_mode = True

    def set_menu_mode(self) -> None:
        """Legacy ``setLightLevelModeMenu``."""
        self.stack.setCurrentIndex(0)
        self.manual_mode = False

    def set_light_level_list(self, light_levels: dict[str, float]) -> None:
        """Fill the drop-down (legacy ``setLightLevelList``)."""
        self.menu_light_level.clear()
        for label in light_levels:
            self.menu_light_level.addItem(label)
        self.light_level_dictionary = dict(light_levels)

    def current_light_level(self) -> float:
        """Selected light level in % sun (legacy run* light_int logic)."""
        if self.manual_mode:
            return float(self.field_manual_light_level.text())
        return float(self.light_level_dictionary[self.menu_light_level.currentText()])

    def update_measured_intensity(self, intensity: float) -> None:
        """Legacy ``updateMeasuredLightIntensity``."""
        self.label_measured_intensity.setText(
            "Measured Light Intensity: " + "{:6.2f}".format(intensity) + "% sun"
        )
