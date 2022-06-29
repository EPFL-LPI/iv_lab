from PyQt5.QtGui import QDoubleValidator

from PyQt5.QtWidgets import (
    QHBoxLayout,
    QVBoxLayout,
    QPushButton,
    QWidget,
    QGroupBox,
    QComboBox,
    QLineEdit,
    QStackedWidget,
    QLabel
)


class LightLevelGroupBox(QGroupBox):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self): 
        #this group has two variants, in a stacked widget.
        self.panelLightLevelDropDown = QWidget()
        #self.panelLightLevelDropDown.setMaximumWidth(300)
        
        self.panelLightLevelManualField = QWidget()
        #self.panelLightLevelManualField.setMaximumWidth(300)
        
        #combobox to select the light level
        self.lightLevelGroupBox = QGroupBox("Light Level")
        lightLevelLayout = QVBoxLayout()
        #self.labelLightLevelMenu = QLabel("Select Light Level")
        self.menuSelectLightLevel = QComboBox()
        self.menuSelectLightLevel.setMaximumWidth(300)
        self.lightLevelStringList = ['1 Sun','Dark']
        self.lightLevelPercentList = [100,0]
        for light in self.lightLevelStringList:
            self.menuSelectLightLevel.addItem(light)
        #self.labelLightLevelMenu.setEnabled(False)
        #self.menuSelectLightLevel.setEnabled(False)
        
        lightLevelDropDownLayout = QHBoxLayout()
        lightLevelDropDownLayout.addWidget(self.menuSelectLightLevel)
        self.panelLightLevelDropDown.setLayout(lightLevelDropDownLayout)
        
        self.fieldManualLightLevel = QLineEdit("100.00")
        self.ManualLightLevelValidator = QDoubleValidator()
        self.fieldManualLightLevel.setValidator(self.ManualLightLevelValidator)
        self.labelManualLightLevel = QLabel("Manual Light Level: ")
        self.labelManualLightLevelUnits = QLabel("mW/cm^2")
        
        lightLevelManualFieldLayout = QHBoxLayout()
        lightLevelManualFieldLayout.addWidget(self.labelManualLightLevel)
        lightLevelManualFieldLayout.addWidget(self.fieldManualLightLevel)
        lightLevelManualFieldLayout.addWidget(self.labelManualLightLevelUnits)
        self.panelLightLevelManualField.setLayout(lightLevelManualFieldLayout)

        self.lightLevelStack = QStackedWidget()
        self.lightLevelStack.addWidget(self.panelLightLevelDropDown)
        self.lightLevelStack.addWidget(self.panelLightLevelManualField)
        self.lightLevelStack.setCurrentIndex(0)
        self.lightLevelModeManual = False
        
        self.labelMeasuredLightIntensity = QLabel("Measured Light Intensity: ---.-- mW/cm^2")
        
        lightLevelLayout = QVBoxLayout()
        lightLevelLayout.addWidget(self.lightLevelStack)
        lightLevelLayout.addWidget(self.labelMeasuredLightIntensity)
        self.setLayout(lightLevelLayout)
        self.setMaximumWidth(300)
        self.setEnabled(False)
    
    def setLightLevelModeManual(self):
        self.lightLevelStack.setCurrentIndex(1)
        self.lightLevelModeManual = True
        
    def setLightLevelModeMenu(self):
        self.lightLevelStack.setCurrentIndex(0)
        self.lightLevelModeManual = False
    
    def updateMeasuredLightIntensity(self,intensity):
        self.labelMeasuredLightIntensity.setText("Measured Light Intensity: " + "{:6.2f}".format(intensity) + " mW/cm^2")
    
    def setLightLevelList(self,lightLevelDict):
        self.menuSelectLightLevel.clear()
        for light in lightLevelDict:
            self.menuSelectLightLevel.addItem(light)
        self.lightLevelDictionary = lightLevelDict