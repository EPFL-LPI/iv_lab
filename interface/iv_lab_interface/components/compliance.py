from PyQt5.QtGui import QDoubleValidator

from PyQt5.QtWidgets import (
    QLabel,
    QLineEdit,
    QHBoxLayout,
    QVBoxLayout,
    QGridLayout,
    QGroupBox,
)

class ComplianceGroupBox(QGroupBox):
    def __init__(self):
        super().__init__("Compliance")

        self.init_ui()

    def init_ui(self):

        #Compliance Voltage and current
        complianceLayout = QGridLayout()
        
        self.labelVoltageLimit = QLabel("Voltage Limit")
        self.fieldVoltageLimit = QLineEdit("2.00")
        self.voltageLimitValidator = QDoubleValidator()
        self.fieldVoltageLimit.setValidator(self.voltageLimitValidator)
        self.fieldVoltageLimit.setMaximumWidth(75)
        self.labelVoltageLimitUnits = QLabel("V")
        self.labelCurrentLimit = QLabel("Current Limit")
        self.fieldCurrentLimit = QLineEdit("5.00")
        self.currentLimitValidator = QDoubleValidator()
        self.fieldCurrentLimit.setValidator(self.currentLimitValidator)
        self.fieldCurrentLimit.setMaximumWidth(75)
        self.labelCurrentLimitUnits = QLabel("mA")
        
        complianceLayout.addWidget(self.labelVoltageLimit,0,0)
        complianceLayout.addWidget(self.fieldVoltageLimit,0,1)
        complianceLayout.addWidget(self.labelVoltageLimitUnits,0,2)
        complianceLayout.addWidget(self.labelCurrentLimit,1,0)
        complianceLayout.addWidget(self.fieldCurrentLimit,1,1)
        complianceLayout.addWidget(self.labelCurrentLimitUnits,1,2)
        
        self.setLayout(complianceLayout)
        self.setMaximumWidth(300)
        self.setEnabled(False)