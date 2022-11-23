from enum import Enum
from typing import Dict

from PyQt6.QtWidgets import (
    QHBoxLayout,
    QVBoxLayout,
    QCheckBox,
    QWidget,
    QGroupBox,
    QComboBox,
    QDoubleSpinBox,
    QStackedWidget,
    QLabel
)

from iv_lab_controller.parameters import IlluminationParameters

from .parameters_widget_base import ParametersWidgetBase


class IlluminationMode(Enum):
    """
    Illumination modes.
    """
    Auto = 0
    Manual = 1


class IlluminationParametersWidget(QGroupBox, ParametersWidgetBase):
    intensities: Dict[str, float] = {
        '100% Sun': 100,
        '55% Sun': 55,
        '10% Sun': 10,
        '1% Sun': 1,
        'Dark': 0
    }

    def __init__(self):
        super().__init__('Light Level')

        self._illumination_mode: IlluminationMode = IlluminationMode.Auto

        self.init_ui()
        self.init_observers()

    def init_ui(self):
        # presets
        self.cb_intensity = QComboBox()
        self.cb_intensity.setMaximumWidth(300)
        for lbl, _ in self.intensities.items():
            self.cb_intensity.addItem(lbl)

        # manual
        lbl_manual_intensity = QLabel('Manual Light Level:')
        lbl_manual_intensity_units = QLabel('mW/cm<sup>2</sup>')
        self.sb_manual_intensity = QDoubleSpinBox()
        self.sb_manual_intensity.setDecimals(2)
        self.sb_manual_intensity.setSingleStep(0.1)

        lo_manual = QHBoxLayout()
        lo_manual.addWidget(lbl_manual_intensity)
        lo_manual.addWidget(self.sb_manual_intensity)
        lo_manual.addWidget(lbl_manual_intensity_units)

        wgt_manual = QWidget()
        wgt_manual.setLayout(lo_manual)

        # intensity setter
        self.stk_intensity = QStackedWidget()
        self.stk_intensity.addWidget(self.cb_intensity)
        self.stk_intensity.addWidget(wgt_manual)
        self.stk_intensity.setCurrentIndex(self.illumination_mode.value)
        self.manual_light_level = False

        # reference diode
        lbl_enable_reference_diode = QLabel('Enable Reference Diode')
        self.cb_enable_reference_diode = QCheckBox()

        lo_enable_reference_diode = QHBoxLayout()
        lo_enable_reference_diode.addWidget(self.cb_enable_reference_diode)
        lo_enable_reference_diode.addWidget(lbl_enable_reference_diode)

        # measured label
        lbl_measured_intensity_title = QLabel('Measured Light Intensity:')
        self.lbl_measured_intensity = QLabel('---.--')
        lbl_measured_intensity_units = QLabel('mW/cm<sup>2</sup>')

        lo_measured_intensity = QHBoxLayout()
        lo_measured_intensity.addWidget(lbl_measured_intensity_title)
        lo_measured_intensity.addWidget(self.lbl_measured_intensity)
        lo_measured_intensity.addWidget(lbl_measured_intensity_units)

        lo_main = QVBoxLayout()
        lo_main.addWidget(self.stk_intensity)
        lo_main.addLayout(lo_enable_reference_diode)
        lo_main.addLayout(lo_measured_intensity)
        self.setLayout(lo_main)
        self.setMaximumWidth(300)

        self.disable_ui()
        self.reset_fields()

    @property
    def illumination_mode(self) -> IlluminationMode:
        """
        :returns: Illumination mode.
        """
        return self._illumination_mode

    @illumination_mode.setter
    def illumination_mode(self, mode: IlluminationMode):
        """
        Set the illumination mode, changing UI as needed.
        """
        self._illumination_mode = mode
        self.stk_intensity.setCurrentIndex(mode.value)

    # @todo: Measured light level should be in Store.
    #   Create an observer for updates.
    def updateMeasuredLightIntensity(self, intensity):
        self.lbl_measured_intensity.setText(f'{intensity:6.2f}')

    def setLightLevelList(self, lightLevelDict):
        self.cb_intensity.clear()
        for light in lightLevelDict:
            self.cb_intensity.addItem(light)

        self.lightLevelDictionary = lightLevelDict

    @property
    def value(self) -> IlluminationParameters:
        """
        :returns: Illumination parameters.
        """
        params = IlluminationParameters()
        if self.illumination_mode is IlluminationMode.Manual:
            params.manual = True
            params.intensity = self.sb_manual_intensity.value()

        else:
            inten = self.intensities[self.cb_intensity.currentText()]
            params.intensity = inten
        params.reference_diode_enabled = self.cb_enable_reference_diode.isChecked()

        return params

    @value.setter
    def value(self, value: IlluminationParameters):
        """
        Set UI values.

        :param value: Desired values.
        :raises ValueError: If invalid intensity.
        """
        if value.manual.value:
            self.illumination_mode = IlluminationMode.Manual

        else:
            self.illumination_mode = IlluminationMode.Auto

            inten_index = None
            for i, i_val in enumerate(self.intensities.values()):
                if value.intensity.value == i_val:
                    inten_index = i
                    break

            if inten_index is None:
                # invalid intensity value
                raise ValueError('Invalid illumination intensity')

            self.cb_intensity.setCurrentIndex(inten_index)

    def enable_ui(self):
        self.setEnabled(True)

    def disable_ui(self):
        self.setEnabled(False)

    def reset_fields(self):
        """
        Reset fields to default values.
        """
        self.cb_intensity.setCurrentIndex(0)
        self.sb_manual_intensity.setValue(100)
