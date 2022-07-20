import os
import logging
from typing import Callable, Dict

from .iv_system_parameters import IVSystemParameters
from .lamp import Lamp
from .smu import SMU
from .computer_parameters import ComputerParameters
from .iv_system_parameters import IVSystemParameters
from ..measurements.iv_curve_result import IVCurveResult
from ..measurements.chronoamperometry_result import ChronoamperometryResult
from ..measurements.chronopotentiometry_result import ChronopotentiometryResult
from ..measurements.mpp_result import MPPResult


class System:
    @staticmethod
    def from_parameters(parameters: IVSystemParameters, emulate: bool = False) -> 'System':
        """
        Create System from SystemParameters

        :param parameters: System parameters to use.
        :param emulate: Run in emulation mode. [Default: False]
        """
        smu = SMU(parameters.SMU)
        smu.fullSunReferenceCurrent = parameters.IVsys['fullSunReferenceCurrent']
        smu.calibrationDateTime = parameters.IVsys['calibrationDateTime']

        lamp_params = parameters.lamp
        lamp_type = lamp.type_from_model(lamp_params['brand'], lamp_params['model'])
        lamp_ctrl = lamp.get_controller(lamp_type)

        if lamp_type is Lamp.KeithleyFilterWheel:
            self.lamp = lamp_ctrl(self.smu, emulate=emulate)

        elif lamp_type is Lamp.OrielLSS7120:
            self.lamp = lamp_ctrl(lamp_params['visa_address'], emulate=emulate)

        else:
            self.lamp = lamp_ctrl(emulate=emulate)

        return system(lamp, smu)

    @staticmethod
    def from_settings_file(path: str, emulate: bool = False) -> 'System':
        """
        Create System from settings file.

        :param path: Path to system settings file to use.
        :param emulate: Run in emulation mode. [Default: False]
        """
        pass

    def __init__(self, emulate: bool = False):
        """
        :param emulate: Run in emulation mode. [Default: False]
        """
        self._emulate = emulate
        
        # map of measurement name to methods
        # available to users through the application interface
        self._user_measurements = {
            'IV curve': self.measure_iv_curve,
            'Constant voltage': self.measure_chronoamperometry,
            'Constant current': self.measure_chronopotentiometry,
            'MPP': self.measure_mpp
        }
        
        self._admin_measurements = {
            'Calibrate': self.calibrate
        }

        self._lamp = None
        self._smu = None
        self._computer_parameters = None
        self._iv_system_parameters = None
                
        # Preferences, to be moved into separate GUI page at some point
        self.saveDataAutomatic = False
        self.checkVOCBeforeScan = True
        self.firstPointDwellTime = 5.0
        self.MPPVoltageStep = 0.002
        self.MPPVoltageStepMax = 0.016
        self.MPPVoltageStepMin = 0.000125
        self.MPPStepGain = 10  # change this to modify convergence time for MPP algo
        
        self.data_IV = None
        self.IV_Results = None
        self.data_CC = None
        self.CC_Results = None
        self.data_CV = None
        self.CV_Results = None
        self.data_MPP = None
        self.MPP_Results = None
        
    @property
    def emulate(self) -> bool:
        """
        :returns: If the system is running in emulation mode.
        """
        return self._emulate

    @property
    def user_measurements(self) -> Dict[str, Callable]:
        """
        :returns: Dictionary of name-method pairs available to users.
        """
        return self._user_measurements

    @property
    def admin_measurements(self) -> Dict[str, Callable]:
        """
        :returns: Dictionary of name-method pairs available only to admins.
        """
        return self._admin_measurements

    @property
    def lamp(self) -> Lamp:
        """
        :returns: The System's lamp controller.
        """
        return self._lamp
    
    @property
    def smu(self) -> SMU:
        """
        :returns: The System's SMU controller.
        """
        return self._smu
    
    @property
    def computer_parameters(self) -> ComputerParameters:
        """
        :returns: The System's computer parameters.
        """
        return self._computer_parameters
    
    @property
    def iv_system_parameters(self) -> IVSystemParameters:
        """
        :returns: The System's IV system parameters.
        """
        return self._iv_system_parameters

    def connect(self):
        """
        Connect to and initialize hardware.
        """
        self.smu.connect()
        self.lamp.connect()

    def disconnect(self):
        """
        Disconnect from hardware.
        """
        pass

    def lamp_on(self):
        """
        Turn lamp on.
        """
        self.lamp.light_on()
    
    def lamp_off(self):
        """
        Turn lamp off..
        """
        self.lamp.light_off()
    
    def measure_light_intensity(self):
        raise NotImplementedError()
    
    def measure_iv_curve(self, IV_param) -> IVCurveResult:
        """
        Runs a chrono-amperometry measurement.
            Holds the current constant, and measures the potential.
        """
        dateTimeString = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        self.IV_Results = {}
        self.IV_Results['active_area'] = IV_param['active_area']
        self.IV_Results['cell_name'] = IV_param['cell_name']
        self.IV_Results['start_V'] = IV_param['start_V']
        self.IV_Results['stop_V'] = IV_param['stop_V']
        #pre-fill default NaN values - important to put something here in case there is an error during the scan
        #self.IV_Results['Voc'] = float('nan')
        #self.IV_Results['Jsc'] = float('nan')
        #self.IV_Results['Vmpp'] = float('nan')
        #self.IV_Results['Jmpp'] = float('nan')
        #self.IV_Results['Pmpp'] = float('nan')
        #self.IV_Results['PCE'] = float('nan')
        #self.IV_Results['FF'] = float('nan')
        
        self.data_IV = {}
        self.data_IV['scanType'] = 'JV'
        self.data_IV['start_time'] = dateTimeString
        self.data_IV['v'] = []
        self.data_IV['i'] = []

        #this parameter is now set from the front panel
        #IV_param["Dwell"] = self.firstPointDwellTime
        
        #check that the start and stop voltages do not exceed minimum or maximum values.
        if IV_param['start_V'] != 'Voc':
            if abs(IV_param['start_V']) > abs(IV_param['Vmax']):
                if self.win != None:
                    self.win.runFinished() # also lowers abortRun flag
                    
                raise ValueError("ERROR: measure_IVcurve start voltage outside of compliance range")
        if IV_param['stop_V'] != 'Voc':
            if abs(IV_param['stop_V']) > abs(IV_param['Vmax']):
                if self.win != None:
                    self.win.runFinished() # also lowers abortRun flag
                    
                raise ValueError("ERROR: measure_IVcurve stop voltage outside of compliance range")
        
        #turn the lamp on
        self.show_status("Turning lamp on...")
            
        lampError = self.turn_lamp_on(IV_param['light_int']) #True
        
        if not lampError:
            while(True): #use while loop to be able to break out at any time if run aborted.
                #measure light intensity on the reference diode if configured
                if self.smu.useReferenceDiode and (IV_param['light_int'] > 1.0):
                    
                    lightIntensity = self.measure_light_intensity() #status messages set internally
                    
                    if self.abortRunFlag() :
                        self.show_status("Run Aborted")
                        break
                    if abs((lightIntensity - IV_param['light_int'])/IV_param['light_int']) > 0.1 :
                        self.error_window("Error: Light level measured by reference diode is more than 10% off from requested level.  Aborting Scan")
                        
                        self.show_status("Run Aborted (Wrong Light Level)")
                            
                        break
                    
                VocPolarityOK = True
                if self.checkVOCBeforeScan and IV_param['light_int']  > 0: #check Voc polarity only when light is on
                    self.show_status("Checking Voc Polarity...")
                    VocPolarityOK = self.smu.checkVOCPolarity(IV_param)
                if self.abortRunFlag():
                    self.show_status("Run Aborted")
                    break
                if not VocPolarityOK:
                    self.show_status("ERROR: Wrong Voc Polarity...")
                    self.error_window("Error: Incorrect polarity detected for Voc.  This could be due to wires plugged incorrectly or light source not turning on.  Aborting Scan")
                    self.show_status("Run Aborted (Wrong Voc Polarity)")
                    
                    break
                    
                self.show_status("Running J-V Scan...")
                
                try:
                    (v_smu, i_smu, i_ref) = self.smu.measure_IV_point_by_point(IV_param) #measure_IVcurve(IV_param)
                except ValueError as err:
                    self.error_window(str(err))
                    break
                except Exception as err:
                    print(err)
                    self.error_window("Execution Error in smu.measure_IVcurve().\nSee terminal for details.")
                    break
                
                if self.smu.useReferenceDiode:
                    if self.smu.referenceDiodeParallel: #light level was measured real-time during scan
                        avgRefCurrent = sum(i_ref)/len(i_ref)
                        avgLightLevel = abs(100. * avgRefCurrent / self.smu.fullSunReferenceCurrent)
                        if self.app != None:
                            self.win.updateMeasuredLightIntensity(avgLightLevel)
                            self.app.processEvents()
                        lightLevelCorrectionFactor = IV_param['light_int'] / avgLightLevel
                    else: #light level was only measured once at the beginning
                        avgLightLevel = lightIntensity
                        lightLevelCorrectionFactor = IV_param['light_int'] / avgLightLevel
                else:
                    lightLevelCorrectionFactor = 1.0
                    avgLightLevel = IV_param['light_int']
                
                if len(v_smu) > 1:
                    self.IV_Results = {}
                    self.IV_Results['active_area'] = IV_param['active_area']
                    self.IV_Results['cell_name'] = IV_param['cell_name']
                    self.IV_Results['light_int'] = IV_param['light_int']
                    if self.smu.useReferenceDiode:
                        self.IV_Results['light_int_meas'] = IV_param['light_int']/lightLevelCorrectionFactor
                    self.IV_Results['Imax'] = IV_param['Imax']
                    self.IV_Results['Dwell'] = IV_param['Dwell']
                    
                    if IV_param['light_int'] > 0 and not self.abortRunFlag(): #don't analyze dark or aborted runs
                        pairs = []
                        dataJ = []
                        for v, i in zip(v_smu, i_smu):
                            pairs.append((v, i * lightLevelCorrectionFactor / IV_param['active_area']))
                            dataJ.append(i * 1000. * lightLevelCorrectionFactor / IV_param['active_area'])
                        #update JV plot with data from single-point light level correction.
                        
                        if self.win != None:
                            self.win.updatePlotIV(v_smu,dataJ)
                            
                        jvData = np.array(pairs)
                        df = pd.DataFrame(jvData)
                        metrics = [ 'voltage', 'current' ]
                        header = pd.MultiIndex.from_product( [ [ IV_param['cell_name'] ], metrics ], names = [ 'sample', 'metrics' ]  )
                        df.columns = header
                        
                        df.index = df.xs( 'voltage', level = 'metrics', axis = 1 ).values.flatten()
                        df.drop( 'voltage', level = 'metrics', axis = 1, inplace = True )
                        df.columns = df.columns.droplevel( 'metrics' )

                        jv_metrics = bric_jv.get_metrics(df, generator=False)
                        #print(jv_metrics)
                        
                        self.IV_Results['Voc'] = float(jv_metrics['voc'])
                        self.IV_Results['Jsc'] = float(jv_metrics['jsc'])*1000.
                        self.IV_Results['Vmpp'] = float(jv_metrics['vmpp'])
                        self.IV_Results['Jmpp'] = float(jv_metrics['jmpp'])*1000.
                        self.IV_Results['Pmpp'] = abs(float(jv_metrics['pmpp'])*1000.)
                        self.IV_Results['PCE'] = 100. * abs(float(jv_metrics['pmpp'])*1000.) / avgLightLevel #IV_param['light_int'] #percent
                        self.IV_Results['FF'] = float(jv_metrics['ff'])
                            
                    #use actual voltage start and stop values for datafile.
                    #important in case of 0-Voc scanning, or scan abort
                    if len(v_smu) > 0:
                        self.IV_Results['start_V'] = v_smu[0]
                        self.IV_Results['stop_V'] = v_smu[len(v_smu)-1]
                    else:
                        self.IV_Results['start_V'] = IV_param['start_V']
                        self.IV_Results['stop_V'] = IV_param['stop_V']
                    self.IV_Results['dV'] = IV_param['dV']
                    self.IV_Results['sweep_rate'] = IV_param['sweep_rate']
                    
                    if self.win != None:
                        self.win.updateIVResults(self.IV_Results)
                        
                    #self.flag_abortRun = False        
                    self.data_IV = {}
                    self.data_IV['scanType'] = 'JV'
                    self.data_IV['start_time'] = dateTimeString
                    self.data_IV['v'] = v_smu
                    self.data_IV['i'] = i_smu
                    self.data_IV['i_ref'] = i_ref
                    
                break #break out of while loop
                
            self.show_status("Turning lamp off...")
            
            lampError = self.turn_lamp_off()
        
        if lampError:
            self.show_status("Lamp Error")
        elif self.abortRunFlag():
            self.show_status("Run Aborted")
        else:
            self.show_status("Run finished")
        
        if self.saveDataAutomatic and len(self.data_IV['v']) > 0:
            self.writeDataFile(self.data_IV, self.username, self.IV_Results)
        
        if self.win != None:
            self.win.runFinished() # also lowers abortRun flag
    
    def measure_chronopotentiometry(self, param) -> ChronopotentiometryResult:
        """
        Runs a chrono-potentiometry measurement.
            Holds the potential constant, and measures the current.
        """
        # self.flag_abortRun = False
        if self.app != None:
            self.app.processEvents()
        
        dateTimeString = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if abs(param['set_current']) > abs(param['Imax']):
            if self.win != None:
                self.win.runFinished() # also lowers abortRun flag
            raise ValueError("ERROR: measure_V_time_dependent set current outside of compliance range")
        
        #this parameter is now set from the front panel
        #param["Dwell"] = self.firstPointDwellTime
        
        #param: light int, set current, time, interval
        self.show_status("Turning lamp on...")
            
        #self.lamp.light_on(param['light_int'])
        lampError = self.turn_lamp_on(param['light_int']) #True
        runError = False

        if not lampError:
            try:
                while(True):
                    if self.smu.useReferenceDiode and (param['light_int'] > 1.0):
                        lightIntensity = self.measure_light_intensity() #status messages set internally
                        
                        if self.abortRunFlag() :
                            break
                                
                        elif abs((lightIntensity - param['light_int'])/param['light_int']) > 0.1 :
                            self.show_status("Run Aborted (Wrong Light Level)")
                            self.error_window("Error: Light level measured by reference diode is more than 10% off from requested level.  Aborting Scan")
                            break
                                
                    self.show_status("Running Constant Current Measurement...")
                    
                    t, v_smu = self.smu.measure_V_time_dependent(param)
                    
                    i_smu = []
                    for v in v_smu:
                        i_smu.append(param['set_current'])
                    
                    self.CC_Results = {}
                    self.CC_Results['active_area'] = param['active_area']
                    self.CC_Results['cell_name'] = param['cell_name']
                    self.CC_Results['light_int'] = param['light_int']
                    if self.smu.useReferenceDiode:
                        self.CC_Results['light_int_meas'] = lightIntensity
                    self.CC_Results['set_current'] = param['set_current']
                    self.CC_Results['interval'] = param['interval']
                    self.CC_Results['duration'] = param['duration']

                    self.data_CC = {}
                    self.data_CC['scanType'] = 'CC'
                    self.data_CC['start_time'] = dateTimeString
                    self.data_CC['t'] = t
                    self.data_CC['v'] = v_smu
                    self.data_CC['i'] = i_smu
                    
                    if self.saveDataAutomatic:
                        self.writeDataFile(self.data_CC, self.username, self.CC_Results)

                    break #break out of infinite while loop
                    
            except ValueError as err:
                self.error_window(str(err))
                self.show_status("Run Aborted With Error")
                runError = True
            except Exception as err:
                print(err)
                self.error_window("Execution Error in measure_V_time_dependent().\nSee terminal for details.")
                self.show_status("Run Aborted With Error")
                runError = True
        
        self.show_status("Turning lamp off...")
                    
        lampError = self.turn_lamp_off()
        
        if runError:
            self.show_status("Run Aborted With Error")
        elif self.abortRunFlag():
            self.show_status("Run Aborted")
        else:
            self.show_status("Run finished")
                            
        if self.win != None:
            self.win.runFinished() # also lowers abortRun flag
            #self.flag_abortRun = False  
    
    def measure_chronoamperometry(self, param) -> ChronoamperometryResult:
        # self.flag_abortRun = False
        if self.app != None:
            self.app.processEvents()
        
        dateTimeString = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if abs(param['set_voltage']) > abs(param['Vmax']):
            if self.win != None:
                self.win.runFinished() # also lowers abortRun flag
            raise ValueError("ERROR: measure_I_time_dependent set voltage outside of compliance range")
        
        #this parameter is now set from the front panel
        #param["Dwell"] = self.firstPointDwellTime
        
        #param: light int, set voltage, time, interval
        self.show_status("Turning lamp on...")
        lampError = self.turn_lamp_on(param['light_int']) #True
        runError = False

        if not lampError:
            try:
                while(True):
                    if self.smu.useReferenceDiode and (param['light_int'] > 1.0):
                        lightIntensity = self.measure_light_intensity() #status messages set internally
                        
                        param['light_int_meas'] = lightIntensity
                        
                        if self.abortRunFlag() :
                            #break out directly if run aborted during setup - don't even start the measurement
                            break
                            
                        elif abs((lightIntensity - param['light_int'])/param['light_int']) > 0.1 :
                            self.error_window("Error: Light level measured by reference diode is more than 10% off from requested level.  Aborting Scan")
                            self.show_status("Run Aborted (Wrong Light Level)")
                            break
                                
                    self.show_status("Running Constant Voltage Measurement...")
                    
                    t, i_smu_corrected, i_smu = self.smu.measure_I_time_dependent(param)
                    
                    v_smu = []
                    for i in i_smu:
                        v_smu.append(param['set_voltage'])
                    
                    self.CV_Results = {}
                    self.CV_Results['active_area'] = param['active_area']
                    self.CV_Results['cell_name'] = param['cell_name']
                    self.CV_Results['light_int'] = param['light_int']
                    if self.smu.useReferenceDiode:
                        self.CV_Results['light_int_meas'] = lightIntensity
                    self.CV_Results['set_voltage'] = param['set_voltage']
                    self.CV_Results['interval'] = param['interval']
                    self.CV_Results['duration'] = param['duration']

                    self.data_CV = {}
                    self.data_CV['scanType'] = 'CV'
                    self.data_CV['start_time'] = dateTimeString
                    self.data_CV['t'] = t
                    self.data_CV['v'] = v_smu
                    self.data_CV['i_corr'] = i_smu_corrected
                    self.data_CV['i'] = i_smu
                    
                    if self.saveDataAutomatic:
                        self.writeDataFile(self.data_CV, self.username, self.CV_Results)
                    
                    break #break out of infinite while loop
                    
            except ValueError as err:
                self.error_window(str(err))
                self.show_status("Run Aborted With Error")
                runError = True
            except Exception as err:
                print(err)
                self.error_window("Execution Error in measure_I_time_dependent().\nSee terminal for details.")
                self.show_status("Run Aborted With Error")
                runError = True
        
        self.show_status("Turning lamp off...")
                    
        lampError = self.turn_lamp_off()
        
        if runError:
            self.show_status("Run Aborted With Error")
        elif self.abortRunFlag():
            self.show_status("Run Aborted")
        else:
            self.show_status("Run finished")
                            
        if self.win != None:
            self.win.runFinished() # also lowers abortRun flag
            #self.flag_abortRun = False  
    
    def measure_mpp(self, param) -> MPPResult:
        """
        Runs an MPP measurement.
        """
        # self.flag_abortRun = False
        if self.app != None:
            self.app.processEvents()
        
        dateTimeString = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        #check if the start voltage is within the compliance range
        if param['start_voltage'] != 'auto':
            if abs(param['start_voltage']) > abs(param['Vmax']):
                if self.win != None:
                    self.win.runFinished() # also lowers abortRun flag
                raise ValueError("ERROR: measure_MPP_time_dependent start voltage outside of compliance range")
        
        #this parameter is now set from the front panel
        #param["Dwell"] = self.firstPointDwellTime
        
        param['voltage_step'] = self.MPPVoltageStep
        param['voltage_step_max'] = self.MPPVoltageStepMax
        param['voltage_step_min'] = self.MPPVoltageStepMin
        param['MPP_step_gain'] = self.MPPStepGain
        
        #param: light int, start voltage, time, interval
        self.show_status("Turning lamp on...")
        lampError = self.turn_lamp_on(param['light_int']) #True
        runError = False

        if not lampError:
            try:
                while(True):
            
                    if self.smu.useReferenceDiode and (param['light_int'] > 1.0):
                        lightIntensity = self.measure_light_intensity() #status messages set internally
                        
                        param['light_int_meas'] = lightIntensity
                        if self.abortRunFlag() :
                            #break out directly if run aborted during setup - don't even start the measurement
                            break
                            
                        elif abs((lightIntensity - param['light_int'])/param['light_int']) > 0.1 :
                            self.error_window("Error: Light level measured by reference diode is more than 10% off from requested level.  Aborting Scan")
                            self.show_status("Run Aborted (Wrong Light Level)")
                            break
                            
                    #check Voc polarity.  If it is ok and the run has not been aborted during the Voc check, run MPP
                    VocPolarityOK = True #variable must be defined in case Voc Polarity is not checked
                    if self.checkVOCBeforeScan and param['light_int']  > 0: #check Voc polarity when light greater than zero
                        self.show_status("Checking Voc Polarity...")
                        
                        VocPolarityOK = self.smu.checkVOCPolarity(param)
                        
                        if self.abortRunFlag() :
                            #break out directly if run aborted during Voc check
                            break
                            
                        if not VocPolarityOK :
                            self.show_status("ERROR: Wrong Voc Polarity.")
                            
                            self.error_window("Error: Incorrect polarity detected for Voc.  This could be due to wires plugged incorrectly.  Aborting Scan")
                            self.show_status("Run Aborted")
                            break
                        
                    #if we get this far then the setup was all ok and we can start the measurement
                    self.show_status("Running MPP Measurement...")
                    
                    t, v_smu, i_smu_corrected, i_smu = self.smu.measure_MPP_time_dependent(param)
                
                    self.MPP_Results = {}
                    self.MPP_Results['active_area'] = param['active_area']
                    self.MPP_Results['cell_name'] = param['cell_name']
                    self.MPP_Results['light_int'] = param['light_int']
                    if self.smu.useReferenceDiode:
                        self.MPP_Results['light_int_meas'] = lightIntensity
                    if param['start_voltage'] == 'auto' and len(v_smu) > 0:
                        self.MPP_Results['start_voltage'] = v_smu[0]
                    else:
                        self.MPP_Results['start_voltage'] = param['start_voltage']
                    self.MPP_Results['interval'] = param['interval']
                    self.MPP_Results['duration'] = param['duration']

                    self.data_MPP = {}
                    self.data_MPP['scanType'] = 'MPP'
                    self.data_MPP['start_time'] = dateTimeString
                    self.data_MPP['t'] = t
                    self.data_MPP['v'] = v_smu
                    self.data_MPP['i'] = i_smu
                    self.data_MPP['i_corr'] = i_smu_corrected
                    
                    if self.abortRunFlag():
                        self.show_status("Run Aborted")
                    else:
                        self.show_status("Run finished")
                    
                    if self.saveDataAutomatic:
                        self.writeDataFile(self.data_MPP, self.username, self.MPP_Results)
                    
                    break #break out of infinite while loop
                    
            except ValueError as err:
                self.error_window(str(err))
                self.show_status("Run Aborted With Error")
                runError = True
            except Exception as err:
                print(err)
                self.error_window("Execution Error in measure_MPP_time_dependent().\nSee terminal for details.")
                self.show_status("Run Aborted With Error")
                runError = True
        
        self.show_status("Turning lamp off...")
                    
        lampError = self.turn_lamp_off()
        
        if runError:
            self.show_status("Run Aborted With Error")
        elif self.abortRunFlag():
            self.show_status("Run Aborted")
        else:
            self.show_status("Run finished")
                            
        if self.win != None:
            self.win.runFinished() # also lowers abortRun flag
            #self.flag_abortRun = False  
         
    def calibrate(self):
        """
        """
        pass

    def run_reference_diode_calibration(self, param):
        # self.flag_abortRun = False
        if self.app != None:
            self.app.processEvents()
        
        dateTimeString = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        param['set_voltage'] = 0.0
        #param['Dwell'] = 5.0
        #param['interval'] = 0.2
        #param['duration'] = 15.0
        
        #param: light int, set voltage, time, interval
        #try:
        if True:
            self.show_status("Turning lamp on...")
            
            lampError = self.turn_lamp_on(param['light_int'])
            param['light_int_meas'] = 100.
            
            #if using system 'IV_Old', the reference diode has to be moved into the light beam first
            #to accomplish this we will do two separate CV runs and then load the data into the calibration plot
            if self.parameters.IVsys['sysName'] == 'IV_Old':
                self.show_status("Moving Reference Diode Into Measurement Position...")
                self.arduino.select_reference_cell()        
                
                if self.app != None:
                    self.win.menuSelectMeasurement.setCurrentIndex(1) #set gui to display CV
                    self.app.processEvents()
                
                t_ref, i_corr_ref, i_ref = self.smu.measure_I_time_dependent(param)
                
                if len(t_ref) == 0:
                    t_ref.append(1)
                    i_ref.append(1)
                
                if not self.abortRunFlag():                    
                    self.show_status("Moving Control Diode Into Measurement Position...")
                    self.arduino.select_test_cell()        
                    
                    t, i_corr, i_smu = self.smu.measure_I_time_dependent(param)
                else: 
                    t = []
                    i_smu = []
                
                if len(t) == 0:
                    t.append(1)
                    i_smu.append(1)
                
                i_smu_ma = []
                for i in i_smu:
                    i_smu_ma.append(i*1000.)
                    
                i_ref_ma = []
                for i in i_ref:
                    i_ref_ma.append(i*1000.)
            
                if self.app != None:
                    self.win.updatePlotCalibration(t, i_smu_ma, t_ref, i_ref_ma)
                    self.win.menuSelectMeasurement.setCurrentIndex(4) #set gui back to display calibration panel
                    self.app.processEvents()
                
            else:
                self.show_status("Running Reference Diode Calibration...")
                
                t, i_smu, i_ref = self.smu.measure_reference_calibration(param)
                
            self.show_status("Turning lamp off...")
            
            self.lamp.light_off()  
            
            #process data and set reference diode calibration
            #Average all current values for both diodes
            averageMeasCurrent = sum(i_smu)/len(i_smu)
            averageRefCurrent = sum(i_ref)/len(i_ref)
            calFactor = (param['reference_current'] / averageMeasCurrent)*(100./param['light_int'])
            
            #write the new photodiode calibration current to the gui.  The user
            #must click 'save calibration' to save this value to the config file.
            if self.app != None:
                win.setCalibrationReferenceCurrent(abs(averageRefCurrent * calFactor * 1000.))
            else:
                print("New Reference Diode Calibration Current: " + str(abs(averageRefCurrent * calFactor * 1000.)) + "mA")
            #self.fullSunReferenceCurrent = averageRefCurrent * calFactor
            #self.save_calibration_to_system_settings()
            
            if self.abortRunFlag():
                self.show_status("Calibration Aborted")
            else:
                self.show_status("Calibration finished")
        try:
            pass
        except ValueError as err:
            self.error_window(str(err))
            self.show_status("Calibration Aborted With Error")
        except Exception as err:
            print(err)
            self.error_window("Execution Error in run_Isc_Calibration().\nSee terminal for details.")
            self.show_status("Calibration Aborted With Error")
        finally:
            if self.win != None:
                self.win.runFinished() # also lowers abortRun flag
            #self.flag_abortRun = False        
    
    def toggleAutoSave(self,autoSave):
        self.saveDataAutomatic = autoSave
    
    def save_calibration_to_system_settings(self, calibration_params):
        dateTimeString = datetime.datetime.now().strftime("%c") #"%Y%m%d_%H%M%S")
        self.parameters.IVsys['fullSunReferenceCurrent'] = calibration_params['reference_current']
        self.smu.fullSunReferenceCurrent = calibration_params['reference_current']
        self.parameters.IVsys['calibrationDateTime'] = dateTimeString
        self.smu.calibrationDateTime = dateTimeString
        settingsFilePath = os.path.join(os.getcwd() , "system_settings.json")
        sys_params = {}
        sys_params['computer'] = self.parameters.computer
        sys_params['IVsys'] = self.parameters.IVsys
        sys_params['lamp'] = self.parameters.lamp
        sys_params['SMU'] = self.parameters.SMU
        with open(settingsFilePath, 'w') as outfile:
            json.dump(sys_params, outfile)                        

    def turn_off(self):
        self.smu.turn_off()
        self.lamp.turn_off()
        
    def abort_run(self):
        self.flag_abortRun = True
    
    def abortRunFlag(self):
        if self.win != None:
            return self.win.flag_abortRun
        else:
            return False
        
    def error_window(self,errorString):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Critical)
        
        msg.setText(errorString)
        #msg.setInformativeText("This is additional information")
        msg.setWindowTitle("IVlab Error")
        #msg.setDetailedText("The details are as follows:")
        msg.setStandardButtons(QMessageBox.Ok) # | QMessageBox.Cancel)
        #msg.buttonClicked.connect(msgbtn)
        
        retval = msg.exec_()
        #print("value of pressed message box button: " +  str(retval))
        
    def show_status(self,msg):
        if self.app != None:
            self.win.showStatus(msg)
            self.app.processEvents()
        else:
            print(msg)