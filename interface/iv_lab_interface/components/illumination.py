from PyQt6.QtWidgets import (
    QHBoxLayout,
    QVBoxLayout,
    QPushButton,
    QWidget,
    QGroupBox,
    QComboBox,
    QDoubleSpinBox,
    QStackedWidget,
    QLabel
)

from iv_lab_controller.measurements.illumination_parameters import IlluminationParameters


class IlluminationWidget(QGroupBox):
    def __init__(self):
        super().__init__('Light Level')
        
        self.intensities = {
            '1 Sun': 100,
            'Dark': 0
        }

        self.init_ui()

    def init_ui(self): 
        # presets
        self.cb_intensity = QComboBox()
        self.cb_intensity.setMaximumWidth(300)
        for lbl, _ in self.intensities.items():
            self.cb_intensity.addItem(lbl)

        # manual
        lbl_manual_intensity = QLabel('Manual Light Level:')
        lbl_manual_intensity_units = QLabel('mW/cm^2')
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
        self.stk_intensity.setCurrentIndex(0)
        self.lightLevelModeManual = False
        
        # measured label
        lbl_measured_intensity_title = QLabel('Measured Light Intensity:')
        self.lbl_measured_intensity = QLabel('---.--')
        lbl_measured_intensity_units = QLabel('mW/cm^2')

        lo_measured_intensity = QHBoxLayout()
        lo_measured_intensity.addWidget(lbl_measured_intensity_title)
        lo_measured_intensity.addWidget(self.lbl_measured_intensity)
        lo_measured_intensity.addWidget(lbl_measured_intensity_units)
        
        lo_main = QVBoxLayout()
        lo_main.addWidget(self.stk_intensity)
        lo_main.addLayout(lo_measured_intensity)
        self.setLayout(lo_main)
        self.setMaximumWidth(300)
        self.setEnabled(False)

        self.reset_fields()
    
    @property
    def manual_illumination(self) -> bool:
        """
        :returns: If in manual mode.
        """
        return (self.stk_intensity.currentIndex() == 1)

    def setLightLevelModeManual(self):
        self.stk_intensity.setCurrentIndex(1)
        
        
    def setLightLevelModeMenu(self):
        self.stk_intensity.setCurrentIndex(0)
    
    def updateMeasuredLightIntensity(self,intensity):
        self.lbl_measured_intensity.setText(f'{intensity:6.2f}')
    
    def setLightLevelList(self,lightLevelDict):
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
        if self.manual_illumination:
            params.manual = True
            params.intensity = self.sb_manual_intensity.value()

        else:
            inten = self.intensities[self.cb_intensity.currentText()]
            params.intensity = inten

        return params

    def reset_fields(self):
        """
        Reset fields to default values.
        """
        self.cb_intensity.setCurrentIndex(0)
        self.sb_manual_intensity.setValue(100)
