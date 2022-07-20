from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import (
    QVBoxLayout,
    QPushButton,
    QWidget
)

from iv_lab_controller.user import User, Permission
from iv_lab_controller.base_classes.measurement_parameters import MeasurementParameters
from iv_lab_controller.measurements.types import MeasurementType
from iv_lab_controller.measurements.iv_curve_parameters import IVCurveParameters

from . import common
from .base_classes.UiToggle import UiToggleInterface
from .components.illumination import IlluminationWidget
from .components.measurement_parameters.main import MeasurementParametersWidget
from .components.cell_parameters import CellParametersWidget
from .components.compliance import ComplianceWidget


class MeasurementFrame(QWidget, UiToggleInterface):
    initialize_hardware = pyqtSignal()
    run_measurement = pyqtSignal(MeasurementType, dict)

    def __init__(self):
        super().__init__()
        self.init_ui()
        self.register_connections()

        self._hardware_initialized = False

    @property
    def hardware_is_initialized(self):
        return self._hardware_initialized
    
    def init_ui(self):
        # init button
        self.btn_initialize = QPushButton("Initialize Hardware",self)
        self.btn_initialize.setMaximumWidth(300)
        self.btn_initialize.setEnabled(False)
        
        # parameter widgets
        self.wgt_illumination_parameters = IlluminationWidget()
        self.wgt_measurement_parameters = MeasurementParametersWidget()
        self.wgt_cell_parameters = CellParametersWidget()
        self.wgt_compliance_parameters = ComplianceWidget()

        # reset button
        self.btn_reset_fields = QPushButton("Reset All Settings To Default", self)
        self.btn_reset_fields.setEnabled(False)
        
        # Set the measurement frame layout
        lo_main = QVBoxLayout()
        lo_main.addWidget(self.btn_initialize)
        lo_main.addStretch(1)
        lo_main.addWidget(self.wgt_illumination_parameters)
        lo_main.addStretch(1)
        lo_main.addWidget(self.wgt_measurement_parameters)
        lo_main.addStretch(1)
        lo_main.addWidget(self.wgt_cell_parameters)
        lo_main.addStretch(1)
        lo_main.addWidget(self.wgt_compliance_parameters)
        lo_main.addStretch(1)
        lo_main.addWidget(self.btn_reset_fields)
        
        self.setLayout(lo_main)  
    
    def register_connections(self):
        self.btn_initialize.clicked.connect(self.initialize_hardware.emit)
        self.btn_reset_fields.clicked.connect(self.setAllFieldsToDefault)

        self.wgt_measurement_parameters.run_measurement.connect(self._run_measurement)
        self.wgt_measurement_parameters.abort.connect(self.abort)

    def setAllFieldsToDefault(self):
        self.CheckBoxAutomaticLimits.setChecked(False)
        self.toggleIVLimitsMode()
        self.checkBoxAutoSave.setChecked(False)
        self.toggleAutoSaveMode()
        self.CheckBoxAutomaticMpp.setChecked(False)
        self.toggleMppStartMode()
        self.fieldIVMinV.setText('0.00')
        self.IVMaxVUser = 1.2
        self.IVFwdLimitUser = 0.0
        self.fieldIVMaxV.setText(str(self.IVMaxVUser))
        self.fieldIVVStep.setText('5.0')
        self.fieldIVSweepRate.setText('20.0')
        self.fieldIVStabilizationTime.setText('5.0')
        self.menuIVSweepDirection.setCurrentIndex(1)
        self.fieldConstantVSetV.setText('0.00')
        self.fieldConstantVStabilizationTime.setText('5.0')
        self.fieldConstantVInterval.setText('0.50')
        self.fieldConstantVDuration.setText('60.0')
        self.fieldConstantISetI.setText('0.00')
        self.fieldConstantIStabilizationTime.setText('5.0')
        self.fieldConstantIInterval.setText('0.50')
        self.fieldConstantIDuration.setText('60.0')
        self.fieldMaxPPStartV.setText('1.00')
        self.fieldMaxPPStabilizationTime.setText('5.0')
        self.fieldMaxPPInterval.setText('0.50')
        self.fieldMaxPPDuration.setText('60.0')
        self.fieldCellenableArea.setText('0.16')
        self.fieldVoltageLimit.setText('2.00')
        self.fieldCurrentLimit.setText('5.0')
        self.menuSelectLightLevel.setCurrentIndex(0)
        self.menuSelectMeasurement.setCurrentIndex(0)
        results = {}
        self.updateIVResults(results)
        #ugly hack to get around cursorPositionChanged event...
        #this event is not called when deleting a character, so write our default string
        #with a dot at the start, move the cursor to the start, and delete
        #otherwise if we put this string in directly the cursorPositionChanged callback
        #is activated and our default string is deleted.
        self.fieldCellName.setText(".Enter Cell Name Here...")
        self.fieldCellName.setCursorPosition(0)
        self.fieldCellName.del_()
        self.ButtonSaveCalibration.setEnabled(False)
        self.fieldCalibrationReferenceCellCurrent.setText('1.00')
        self.fieldCalibrationStabilizationTime.setText('5.0')
        self.fieldCalibrationInterval.setText('0.5')
        self.fieldCalibrationDuration.setText('60.0')

    def toggle_ui(self, enable: bool = True):
        """
        Enable or disable UI elements.

        :param enable: Whether to enable or disable elements.
            [Default: True]
        """
        if enable:
            self.enable_ui()

        else:
            self.disable_ui()

    def enable_ui(self):
        self.btn_initialize.setEnabled(True)

    def disable_ui(self):
        self.btn_initialize.setEnabled(False)

    def enable_measurement_ui(self):
        enable = True
        #self.labelLightLevelMenu.setEnabled(enable)
        self.wgt_illumination_parameters.setEnabled(enable)
        #self.menuSelectLightLevel.setEnabled(enable)
        #self.labelMeasurementMenu.setEnabled(enable)
        self.wgt_measurement_parameters.setEnabled(enable)
        #self.menuSelectMeasurement.setEnabled(enable)
        #self.Stack.setEnabled(enable)
        self.wgt_compliance_parameters.setEnabled(enable)

    def abort(self):
        common.StatusBar().showMessage("Aborting measurement...")

    def _run_measurement(self, measurement: MeasurementType):
        """
        Runs a given measurement type.

        :param measurement: Type of measurement to run.
        """
        if measurement is MeasurementType.IVCurve:
            self.run_iv_sweep()

        if measurement is MeasurementType.Chronoamperometry:
            self.run_chronoamperometry()

        if measurement is MeasurementType.Chronopotentiometry:
            self.run_chronopotentiometry()

        if measurement is MeasurementType.MPP:
            self.run_mpp()

        if measurement is MeasurementType.Calibration:
            self.run_calibration()
    
    def run_iv_sweep(self):
        """
        Run an IV sweep.
        Gather parameters from relevant inputs. 
        """
        comp_params = self.wgt_compliance_parameters.value
        cell_params = self.wgt_cell_parameters.value
        iv_params = self.wgt_measurement_parameters.iv_curve_params.value
        illumination_params = self.wgt_illumination_parameters.value
        
        try:
            comp_params.validate()
            cell_params.validate()
            iv_params.validate()
            illumination_params.validate()

        except ValueError as err:
            common.show_message_box(
                'Invalid measurement parameters',
                f'Invalid measurement parameters\n{err}',
                icon=QMessageBox.Critical
            )
            return

        sweepDir = iv_params.direction.value
        dV = abs(iv_params.voltage_step.value)

        v_compliance = comp_params.voltage_limit.value
        i_compliance = comp_params.current_limit.value
        cell_active_area = cell_params.cell_area.value
        
        if iv_params.use_automatic_limits.value:
            limitsMode = 'Automatic'
            FwdCurrentLimit = iv_params.max_voltage.value * cell_active_area / 1000
            if sweepDir == 'Forward':
                startV = 0.0
                stopV = 'Voc'

            else:    
                startV = 'Voc'
                stopV = 0.0
                dV *= -1

        else:
            limitsMode = 'Manual'
            FwdCurrentLimit = i_compliance

            minV = iv_params.min_voltage.value
            maxV = iv_params.max_voltage.value

            if abs(maxV) > v_compliance:
                common.show_message_box(
                    'Invalid measurement parameters',
                    'Maximum voltage outside of compliance range',
                    icon=QMessageBox.Critical
                )
                return

            if abs(minV) > v_compliance:
                common.show_message_box(
                    'Invalid measurement parameters',
                    'Minimum voltage outside of compliance range',
                    icon=QMessageBox.Critical
                )
                return

            if sweepDir == 'Forward':
                startV = minV
                stopV = maxV

            else:    
                startV = maxV
                stopV = minV
                dV *= -1
        
        common.StatusBar().showMessage("Beginning IV Scan")
        IV_params = {
            'light_int': illumination_params.intensity.value,
            'limits_mode': iv_params.use_automatic_limits.value,
            'Fwd_current_limit': comp_params.current_limit.value,
            'start_V': startV,
            'stop_V': stopV,
            'dV': dV,
            'sweep_rate': iv_params.sweep_rate.value,
            'Dwell': iv_params.stabilization_time.value,
            'Imax': i_compliance,
            'Vmax': v_compliance,
            'active_area': cell_params.cell_area.value
        }
        
        # IV_params['Imax'] = 0.010
        # self.graphWidget.setLabel('left','Current (A)')
        # self.graphWidget.setLabel('bottom','Voltage (V)')
        self.run_measurement.emit(MeasurementType.IVCurve, IV_params)

    def run_chronoamperometry(self):
        v_compliance = abs(float(self.fieldVoltageLimit.text()))
        setV = float(self.fieldConstantVSetV.text())
        if abs(setV) > v_compliance:
            self.showErrorMessage("ERROR: Requested voltage outside of compliance range")
            return
        
        self.statusBar().showStatus("Launching choronoamperometry measurement.")
        params = {}
        # param: light_int, set_voltage, duration, interval
        
        if self.lightLevelModeManual :
            params['light_int'] = float(self.fieldManualLightLevel.text())
        else:
            lightKey = self.menuSelectLightLevel.currentText()            
            params['light_int'] = self.lightLevelDictionary[lightKey]
            
        params['set_voltage'] = float(self.fieldConstantVSetV.text())
        params['Dwell'] = float(self.fieldConstantVStabilizationTime.text())
        params['interval'] = float(self.fieldConstantVInterval.text())
        params['duration'] = float(self.fieldConstantVDuration.text())
        params['Imax'] = abs(float(self.fieldCurrentLimit.text())/1000.)
        params['Vmax'] = v_compliance
        params['active_area'] = float(self.fieldCellActiveArea.text())
        cellName = self.fieldCellName.text()
        if cellName == "Enter Cell Name Here...":
            cellName = ""
        params['cell_name'] = self.sanitizeCellName(cellName)
        
        self.runStarted()
        self.signal_run_chronoamperometry_measurement.emit(params)
    
    def run_chronopotentiometry(self):
        i_compliance = abs(float(self.fieldCurrentLimit.text())/1000.)
        setI = float(self.fieldConstantISetI.text())
        if abs(setI) > i_compliance:
            self.showErrorMessage("ERROR: Requested current outside of compliance range")
            return
    
        self.showStatus("launching Constant Current Measurement")
        self.statusBar.show()
        params = {}
        # param: light_int, set_current, duration, interval
        
        if self.lightLevelModeManual :
            params['light_int'] = float(self.fieldManualLightLevel.text())
        else:
            lightKey = self.menuSelectLightLevel.currentText()            
            params['light_int'] = self.lightLevelDictionary[lightKey]
            
        params['set_current'] = float(self.fieldConstantISetI.text())/1000.
        params['Dwell'] = float(self.fieldConstantIStabilizationTime.text())
        params['interval'] = float(self.fieldConstantIInterval.text())
        params['duration'] = float(self.fieldConstantIDuration.text())
        params['Imax'] = i_compliance
        params['Vmax'] = abs(float(self.fieldVoltageLimit.text()))
        params['active_area'] = float(self.fieldCellActiveArea.text())
        cellName = self.fieldCellName.text()
        if cellName == "Enter Cell Name Here...":
            cellName = ""
        params['cell_name'] = self.sanitizeCellName(cellName)
        
        self.runStarted()
        self.signal_runConstantI.emit(params)
    
    def run_mpp(self):
        v_compliance = abs(float(self.fieldVoltageLimit.text()))
        startV = float(self.fieldMaxPPStartV.text())
        if abs(startV) > v_compliance:
            self.showErrorMessage("ERROR: MPP start voltage outside of compliance range")
            return
        
        self.showStatus("launching Maximum Power Point Measurement")
        self.statusBar.show()
        params = {}
        # param: light_int, start_voltage, duration, interval
        
        if self.lightLevelModeManual :
            params['light_int'] = float(self.fieldManualLightLevel.text())
        else:
            lightKey = self.menuSelectLightLevel.currentText()            
            params['light_int'] = self.lightLevelDictionary[lightKey]
            
        if self.CheckBoxAutomaticMpp.isChecked():
            params['start_voltage'] = 'auto'
        else:
            params['start_voltage'] = float(self.fieldMaxPPStartV.text())
        params['Dwell'] = float(self.fieldMaxPPStabilizationTime.text())
        params['interval'] = float(self.fieldMaxPPInterval.text())
        params['duration'] = float(self.fieldMaxPPDuration.text())
        params['Imax'] = abs(float(self.fieldCurrentLimit.text())/1000.)
        params['Vmax'] = v_compliance
        params['active_area'] = float(self.fieldCellActiveArea.text())
        cellName = self.fieldCellName.text()
        if cellName == "Enter Cell Name Here...":
            cellName = ""
        params['cell_name'] = self.sanitizeCellName(cellName)
        
        self.runStarted()
        self.signal_runMaxPP.emit(params)
    
    def run_calibration(self):
        v_compliance = abs(float(self.fieldVoltageLimit.text()))
        setV = float(self.fieldConstantVSetV.text())
        if abs(setV) > v_compliance:
            self.showErrorMessage("ERROR: Requested voltage outside of compliance range")
            return
        
        self.showStatus("launching Photodiode Calibration")
        self.statusBar.show()
        params = {}
        #param: light_int, set_voltage, duration, interval
        
        if self.lightLevelModeManual :
            params['light_int'] = float(self.fieldManualLightLevel.text())
        else:
            lightKey = self.menuSelectLightLevel.currentText()            
            params['light_int'] = self.lightLevelDictionary[lightKey]
            
        params['set_voltage'] = 0.0
        params['Dwell'] = float(self.fieldCalibrationStabilizationTime.text())
        params['interval'] = float(self.fieldCalibrationInterval.text())
        params['duration'] = float(self.fieldCalibrationDuration.text())
        params['reference_current'] = abs(float(self.fieldCalibrationDiodeReferenceCurrent.text())/1000.)
        params['Imax'] = abs(float(self.fieldCurrentLimit.text())/1000.)
        params['Vmax'] = v_compliance
        params['active_area'] = float(self.fieldCellActiveArea.text())
        cellName = self.fieldCellName.text()
        if cellName == "Enter Cell Name Here...":
            cellName = ""
        params['cell_name'] = self.sanitizeCellName(cellName)
        
        self.runStarted()
        self.ButtonSaveCalibration.setEnabled(True)
        self.signal_runCalibration.emit(params)