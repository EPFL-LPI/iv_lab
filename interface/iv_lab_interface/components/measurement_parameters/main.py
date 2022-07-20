from typing import Dict

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtGui import QDoubleValidator

from PyQt5.QtWidgets import (
    QStackedWidget,
    QLabel,
    QLineEdit,
    QHBoxLayout,
    QVBoxLayout,
    QPushButton,
    QWidget,
    QGroupBox,
    QCheckBox,
    QComboBox,
    QGridLayout,
    QMessageBox
)

from iv_lab_controller.measurements.types import MeasurementType 

from .iv_curve import IVCurveParametersWidget
from .chronoamperometry import ChronoamperometryParametersWidget
from .chronopotentiometry import ChronopotentiometryParametersWidget
from .mpp import MPPParametersWidget
from .calibration import CalibrationParametersWidget


class MeasurementParametersWidget(QGroupBox):
    measurement_change = pyqtSignal(MeasurementType)
    run_measurement = pyqtSignal(MeasurementType)
    abort = pyqtSignal()

    def __init__(self):
        super().__init__("Measurement")
        self._measurement_index = {}

        self.init_ui()
        self.register_connections()

    @property
    def measurement_index(self) -> Dict[MeasurementType, int]:
        """
        :returns: Dictionary of {measurement type: stack index}.
        """
        return self._measurement_index
    

    def init_ui(self):
        # combobox to select the measurement type
        # self.labelMeasurementMenu = QLabel("Select Measurement Type")
        self.measurementList = [
            'J-V Scan',
            'Constant Voltage, Measure J',
            'Constant Current, Measure V',
            'Maximum Power Point',
            'Calibrate Reference Diode'
        ]

        self.cb_measurement_select = QComboBox()
        self.cb_measurement_select.setMaximumWidth(300)
        for meas in self.measurementList:
            self.cb_measurement_select.addItem(meas)

        self.cb_measurement_select.currentIndexChanged.connect(self.select_measurement)
        # self.labelMeasurementMenu.setEnabled(False)
        # self.cb_measurement_select.setEnabled(False)
        
        # one panel per measurement type
        self.iv_curve_params = IVCurveParametersWidget()
        self.chronoamp_params = ChronoamperometryParametersWidget()
        self.chronopot_params = ChronopotentiometryParametersWidget()
        self.mpp_params = MPPParametersWidget()
        self.calibration_params = CalibrationParametersWidget()
        
        self.stk_measurements = QStackedWidget()
        self.stk_measurements.addWidget(self.iv_curve_params)
        self.stk_measurements.addWidget(self.chronoamp_params)
        self.stk_measurements.addWidget(self.chronopot_params)
        self.stk_measurements.addWidget(self.mpp_params)
        self.stk_measurements.addWidget(self.calibration_params)
        # self.stk_measurements.setEnabled(False)

        self._measurement_index = {
            MeasurementType.IVCurve: 0,
            MeasurementType.Chronoamperometry: 1,
            MeasurementType.Chronopotentiometry: 2,
            MeasurementType.MPP: 3,
            MeasurementType.Calibration: 4
        }
        
        lo_main = QVBoxLayout()
        lo_main.addWidget(self.cb_measurement_select)
        lo_main.addWidget(self.stk_measurements)
        self.setLayout(lo_main)
        self.setEnabled(False)
        self.setMaximumWidth(300)

    def register_connections(self):
        self.iv_curve_params.run.connect(lambda: self.run_measurement.emit(MeasurementType.IVCurve))
        self.iv_curve_params.abort.connect(self._abort)

        self.chronoamp_params.run.connect(lambda: self.run_measurement.emit(MeasurementType.Chronoamperometry))
        self.chronoamp_params.abort.connect(self._abort)

        self.chronopot_params.run.connect(lambda: self.run_measurement.emit(MeasurementType.Chronopotentiometry))
        self.chronopot_params.abort.connect(self._abort)
        
        self.mpp_params.run.connect(lambda: self.run_measurement.emit(MeasurementType.MPP))
        self.mpp_params.abort.connect(self._abort)

        self.calibration_params.run.connect(lambda: self.run_measurement.emit(MeasurementType.Calibration))
        self.calibration_params.abort.connect(self._abort)

    def select_measurement(self, i: int):
        """
        Sets the measurement parameters to the correct type.
        Emits a `measurement_change` signal.

        :param i: Index of the measurement.
        """
        self.stk_measurements.setCurrentIndex(i)

        for meas, m_ind in self.measurement_index.items():
            if m_ind == i:
                self.measurement_change.emit(meas)
                break

    def _abort(self):
        """
        Signal to abort measurement.
        """
        self.abort.emit()