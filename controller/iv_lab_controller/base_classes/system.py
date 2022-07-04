import os
import logging

from .system_parameters import SystemParameters
from .smu import SMU
from . import lamp
from .lamp import Lamp


class System:
    @staticmethod
    def from_parameters(parameters: SystemParameters, emulate: bool = False) -> 'System':
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
            self.lamp = lamp_ctrl(self.SMU, emulate=emulate)

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

    def __init__(
        self,
        computer,
        iv_system,
        lamp,
        smu,
        emulate: bool = False
    ):
        """
        :param computer:
        :param iv_system:
        :param lamp:
        :param smu:
        :param emulate: Run in emulation mode. [Default: emulate]
        """
        self._emulate = emulate
        self.parameters = parameters
                
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
        
        if self.parameters.IVsys['sysName'] == 'IV_Old':
            # arduino is not present in all systems.  
            # Check that its parameters have been loaded from the system settings file before trying to access
            if sp.arduino != None:
                self.arduino = arduino(sp.arduino)
            else:
                raise ValueError("System name is set to 'IV_Old' but no arduino settings dictionary is present")
        
    @property
    def emulate(self) -> bool:
        """
        :returns: If the system is running in emulation mode.
        """
        return self._emulate

    def hardware_init(self):
        self.SMU.connect()
        self.lamp.connect()

        #optional arduino initialization
        if self.parameters.IVsys['sysName'] == 'IV_Old':
            self.arduino.connect()

    def turn_lamp_on(self,light_int):
            lampError = True
            try:
                # turn the lamp on, or set the filter wheel to the right position
                self.lamp.light_on(light_int)
                
                # for system IV_Old, have to open the shutter as well when light level not zero
                if self.parameters.IVsys['sysName'] == 'IV_Old' and light_int > 0.:
                    self.arduino.shutter_open()
                lampError = False
            except ValueError as err:
                self.error_window(str(err))
                lampError = True
            except Exception as err:
                print(err)
                self.error_window("Execution Error in lamp.light_on().\nSee terminal for details.")    
                lampError = True
            
            return lampError
    
    def turn_lamp_off(self):
        lampError = True
        try:
            self.lamp.light_off()
            #for system IV_Old, have to close the shutter
            if self.parameters.IVsys['sysName'] == 'IV_Old':
                self.arduino.shutter_close()
            lampError = False
        except ValueError as err:
            self.error_window(str(err))
        except Exception as err:
            print(err)
            self.error_window("Execution Error in lamp.light_off().\nSee terminal for details.")
        
        return lampError
    
    def measure_light_intensity(self):
        #if using system 'IV_Old', the reference diode has to be moved into the light beam first
        if self.parameters.IVsys['sysName'] == 'IV_Old':
            self.show_status("Moving Reference Diode Into Measurement Position...")
            self.arduino.select_reference_cell()
        
        self.show_status("Measuring Light Intensity on Reference Diode...")
        
        lightIntensity = self.SMU.measureLightIntensity(5.0)
        
        #move back to the test cell if using IV_Old
        if self.parameters.IVsys['sysName'] == 'IV_Old':
            self.show_status("Moving Test Cell Into Measurement Position...")
            self.arduino.select_test_cell()
            
        return lightIntensity
    
    def measure_IVcurve(self, IV_param):
        if self.app != None:
            self.app.processEvents()
        # self.flag_abortRun = False
        
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
                if self.SMU.useReferenceDiode and (IV_param['light_int'] > 1.0):
                    
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
                    VocPolarityOK = self.SMU.checkVOCPolarity(IV_param)
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
                    (v_smu, i_smu, i_ref) = self.SMU.measure_IV_point_by_point(IV_param) #measure_IVcurve(IV_param)
                except ValueError as err:
                    self.error_window(str(err))
                    break
                except Exception as err:
                    print(err)
                    self.error_window("Execution Error in smu.measure_IVcurve().\nSee terminal for details.")
                    break
                
                if self.SMU.useReferenceDiode:
                    if self.SMU.referenceDiodeParallel: #light level was measured real-time during scan
                        avgRefCurrent = sum(i_ref)/len(i_ref)
                        avgLightLevel = abs(100. * avgRefCurrent / self.SMU.fullSunReferenceCurrent)
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
                    if self.SMU.useReferenceDiode:
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
    
    def measure_V_time_dependent(self, param):
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
                    if self.SMU.useReferenceDiode and (param['light_int'] > 1.0):
                        lightIntensity = self.measure_light_intensity() #status messages set internally
                        
                        if self.abortRunFlag() :
                            break
                                
                        elif abs((lightIntensity - param['light_int'])/param['light_int']) > 0.1 :
                            self.show_status("Run Aborted (Wrong Light Level)")
                            self.error_window("Error: Light level measured by reference diode is more than 10% off from requested level.  Aborting Scan")
                            break
                                
                    self.show_status("Running Constant Current Measurement...")
                    
                    t, v_smu = self.SMU.measure_V_time_dependent(param)
                    
                    i_smu = []
                    for v in v_smu:
                        i_smu.append(param['set_current'])
                    
                    self.CC_Results = {}
                    self.CC_Results['active_area'] = param['active_area']
                    self.CC_Results['cell_name'] = param['cell_name']
                    self.CC_Results['light_int'] = param['light_int']
                    if self.SMU.useReferenceDiode:
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
    
    def measure_I_time_dependent(self, param):
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
                    if self.SMU.useReferenceDiode and (param['light_int'] > 1.0):
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
                    
                    t, i_smu_corrected, i_smu = self.SMU.measure_I_time_dependent(param)
                    
                    v_smu = []
                    for i in i_smu:
                        v_smu.append(param['set_voltage'])
                    
                    self.CV_Results = {}
                    self.CV_Results['active_area'] = param['active_area']
                    self.CV_Results['cell_name'] = param['cell_name']
                    self.CV_Results['light_int'] = param['light_int']
                    if self.SMU.useReferenceDiode:
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
        
    
    def measure_MPP_time_dependent(self, param):
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
            
                    if self.SMU.useReferenceDiode and (param['light_int'] > 1.0):
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
                        
                        VocPolarityOK = self.SMU.checkVOCPolarity(param)
                        
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
                    
                    t, v_smu, i_smu_corrected, i_smu = self.SMU.measure_MPP_time_dependent(param)
                
                    self.MPP_Results = {}
                    self.MPP_Results['active_area'] = param['active_area']
                    self.MPP_Results['cell_name'] = param['cell_name']
                    self.MPP_Results['light_int'] = param['light_int']
                    if self.SMU.useReferenceDiode:
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
                
                t_ref, i_corr_ref, i_ref = self.SMU.measure_I_time_dependent(param)
                
                if len(t_ref) == 0:
                    t_ref.append(1)
                    i_ref.append(1)
                
                if not self.abortRunFlag():                    
                    self.show_status("Moving Control Diode Into Measurement Position...")
                    self.arduino.select_test_cell()        
                    
                    t, i_corr, i_smu = self.SMU.measure_I_time_dependent(param)
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
                
                t, i_smu, i_ref = self.SMU.measure_reference_calibration(param)
                
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
    
    def saveData(self,scanType, cellName):
        #cellName value is already set in the various results dictionaries.
        #overwrite the value with the value in the field at the moment 'save data' is pressed.
        #this gives a more intuitive functionality for the user.
        if scanType == 'J-V Scan':
            if self.data_IV != None and self.IV_Results != None:
                self.IV_Results['cell_name'] = cellName
                self.writeDataFile(self.data_IV, self.username, self.IV_Results)
            else:
                self.error_window("ERROR: No current J-V Data available to save.")
        elif scanType == 'Constant Voltage, Measure J':
            if self.data_CV != None and self.CV_Results != None:
                self.CV_Results['cell_name'] = cellName
                self.writeDataFile(self.data_CV, self.username, self.CV_Results)
            else:
                self.error_window("ERROR: No current Constant-Voltage Data available to save.")
        elif scanType == 'Constant Current, Measure V':            
            if self.data_CC != None and self.CC_Results != None:
                self.CC_Results['cell_name'] = cellName
                self.writeDataFile(self.data_CC, self.username, self.CC_Results)
            else:
                self.error_window("ERROR: No current Constant-Current Data available to save.")
        elif scanType == 'Maximum Power Point':
            if self.data_MPP != None and self.MPP_Results != None:
                self.MPP_Results['cell_name'] = cellName
                self.writeDataFile(self.data_MPP, self.username, self.MPP_Results)
            else:
                self.error_window("ERROR: No current MPP Data available to save.")
    
    def writeDataFile(self, data, uname, IV_Results):
        cell_name = IV_Results['cell_name']
        #dateTimeString = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        dateTimeString = data['start_time']
        filename = cell_name + "_" + data['scanType'] + '_' + dateTimeString + '.csv'
        pdfFileName = cell_name + "_" + data['scanType'] + '_' + dateTimeString + '.pdf'
        dataFilePath = os.path.join(self.parameters.computer['basePath'] , uname , 'data' , filename)
        pdfFilePath = os.path.join(self.parameters.computer['basePath'] , uname , 'data' , pdfFileName)
        scrambled_filename = self.scramble_string(uname + "_" + os.path.splitext(filename)[0])
        sdFilePath = os.path.join(self.parameters.computer['sdPath'] , scrambled_filename)
        
        basePath, filename = os.path.split(dataFilePath)
        if (not os.path.exists(basePath)):
            os.makedirs(basePath)
            
        f = open(dataFilePath, "w")
        fileString = ""
        
        # prepare header content
        headerLines = []
        headerLines.append("Measurement System," + self.parameters.IVsys['sysName'])
        headerLines.append("Scan Start Time," + data['start_time'])
        headerLines.append("Sourcemeter Brand," + self.parameters.SMU['brand'])
        headerLines.append("Sourcemeter Model," + self.parameters.SMU['model'])
        headerLines.append("Lamp Brand," + self.parameters.lamp['brand'])
        headerLines.append("Lamp Model," + self.parameters.lamp['model'])
        headerLines.append("Requested Light Intensity," + str(IV_Results['light_int']) + ',mW/cm^2')
        if self.SMU.useReferenceDiode:
            headerLines.append("Measured Light Intensity," + str(IV_Results['light_int_meas']) + ',mW/cm^2')
            headerLines.append("Reference Diode 1sun Current," + str(self.SMU.fullSunReferenceCurrent*1000.) + ',mA')
            headerLines.append("Reference Diode calibration date," + self.SMU.calibrationDateTime)
        headerLines.append("Cell Active Area," + str(IV_Results['active_area']) + ',cm^2')
        if data['scanType'] == 'JV':
            headerLines.append("Start Voltage," + str(self.IV_Results['start_V']) + ",V")
            headerLines.append("Stop Voltage," + str(self.IV_Results['stop_V']) + ",V")
            headerLines.append("Voltage Step," + str(self.IV_Results['dV']) + ",V")
            headerLines.append("Sweep Rate," + str(self.IV_Results['sweep_rate']) + ",V/sec")
            headerLines.append("J-V Results")
            if 'Jsc' in IV_Results:
                headerLines.append("Jsc," + str(IV_Results['Jsc']) + ",mA/cm^2")
            if 'Voc' in IV_Results:
                headerLines.append("Voc," + str(IV_Results['Voc']) + ",V")
            if 'FF' in IV_Results:
                headerLines.append("Fill Factor," + str(IV_Results['FF']))
            if 'PCE' in IV_Results:
                headerLines.append("PCE," + str(IV_Results['PCE']) + ",%")
            if 'Jmpp' in IV_Results:
                headerLines.append("Jmpp," + str(IV_Results['Jmpp']) + ",mA/cm^2")
            if 'Vmpp' in IV_Results:
                headerLines.append("Vmpp," + str(IV_Results['Vmpp']) + ",V")
            if 'Pmpp' in IV_Results:
                headerLines.append("Pmpp," + str(IV_Results['Pmpp']) + ",mW/cm^2")
            if self.SMU.useReferenceDiode:
                headerLines.append("Voltage(V),Normalized Current(A),Raw Current(A),light intensity (mW/cm^2)")
            else:
                headerLines.append("Voltage(V),Current(A)")
        elif data['scanType'] == 'CV':
            headerLines.append("Set Voltage," + str(IV_Results['set_voltage']) + ",V")
            headerLines.append("Measurement Interval," + str(IV_Results['interval']) + ",sec")
            headerLines.append("Measurement Duration," + str(IV_Results['duration'] ) + ",sec")
            headerLines.append("Constant Voltage Results")
            if self.SMU.useReferenceDiode:
                headerLines.append("Time(s),Voltage(V),Normalized Current(A), Raw Current(A)")
            else:
                headerLines.append("Time(s),Voltage(V),Current(A)")
        elif data['scanType'] == 'CC':
            headerLines.append("Set Current," + str(IV_Results['set_current']) + ",A")
            headerLines.append("Measurement Interval," + str(IV_Results['interval']) + ",sec")
            headerLines.append("Measurement Duration," + str(IV_Results['duration'] ) + ",sec")
            headerLines.append("Constant Current Results")
            headerLines.append("Time(s),Voltage(V),Current(A)")
        elif data['scanType'] == 'MPP':
            headerLines.append("Start Voltage," + str(IV_Results['start_voltage']) + ",V")
            headerLines.append("Measurement Interval," + str(IV_Results['interval']) + ",sec")
            headerLines.append("Measurement Duration," + str(IV_Results['duration'] ) + ",sec")
            headerLines.append("Maximum Power Point Results")
            if self.SMU.useReferenceDiode:
                headerLines.append("Time(s),Voltage(V),Normalized Current(A),Normalized Power(mW/cm2),Raw Current (A)")
            else:
                headerLines.append("Time(s),Voltage(V),Current(A),Power(mW/cm2)")
        else:
            raise ValueError("scanType entry in data dictionary must be JV, CV, CC, or MPP")

        nLines = len(headerLines) + 1
        f.write("nHeader," + str(nLines) + "\n")
        fileString += "nHeader," + str(nLines) + "\n"
        for line in headerLines:
            f.write(line + "\n")
            fileString += line + "\n"
        
        if data['scanType'] == 'JV':
            for v,i,ref in zip(data['v'], data['i'], data['i_ref']):
                if self.SMU.useReferenceDiode:
                    i_corr = i * IV_Results['light_int'] / IV_Results['light_int_meas']
                    light_intensity = 100.0 * ref / self.SMU.fullSunReferenceCurrent
                    fileLine = (str(round(v,12)) + "," + str(round(i_corr,12)) + "," + str(round(i,12)) + "," + str(round(light_intensity,12)) + "\n")
                else:
                    fileLine = str(round(v,12)) + "," + str(round(i,12)) + "\n"
                f.write(fileLine)
                fileString += fileLine
        elif data['scanType'] == 'CV':
            for t,v,i_corr,i in zip(data['t'], data['v'], data['i_corr'], data['i']):
                if self.SMU.useReferenceDiode:
                    fileLine = str(round(t,6)) + "," + str(round(v,12)) + "," + str(round(i_corr,12)) + "," + str(round(i,12)) + "\n"
                else:
                    fileLine = str(round(t,6)) + "," + str(round(v,12)) + "," + str(round(i,12)) + "\n"
                f.write(fileLine)
                fileString += fileLine
        elif data['scanType'] == 'CC':
            for t,v,i in zip(data['t'], data['v'], data['i']):
                fileLine = str(round(t,6)) + "," + str(round(v,12)) + "," + str(round(i,12)) + "\n"
                f.write(fileLine)
                fileString += fileLine
        elif data['scanType'] == 'MPP':
            for t,v,i_corr,i in zip(data['t'], data['v'], data['i_corr'], data['i']):
                if self.SMU.useReferenceDiode:
                    w = abs(i_corr*v*1000./IV_Results['active_area'])
                    fileLine = str(round(t,6)) + "," + str(round(v,12)) + "," + str(round(i_corr,12)) + "," + str(round(w,12)) + "," + str(round(i,12)) + "\n"
                else:
                    w = abs(i*v*1000./IV_Results['active_area'])
                    fileLine = str(round(t,6)) + "," + str(round(v,12)) + "," + str(round(i,12)) + "," + str(round(w,12)) + "\n"
                f.write(fileLine)
                fileString += fileLine
        
        f.close()
        
        if data['scanType'] == 'JV':
            self.generate_JV_Results_PDF(data, uname, IV_Results, filename, pdfFilePath)
        
        self.show_status("Saved data to: " + dataFilePath)
        
        #write copy into secret file
        try:
            basePath, filename = os.path.split(sdFilePath)
            if (not os.path.exists(basePath)):
                os.makedirs(basePath)
            s = open(sdFilePath, "w")
            s.write(self.scramble_string(fileString)) 
            s.close()
        except:
            pass
    
    def generate_JV_Results_PDF(self, data, uname, IV_Results, dataFileName, pdfFilePath):
        dateTimeString = datetime.datetime.now().strftime("%c") #"%Y%m%d_%H%M%S")

        A4SizeY = 8.25 #inches, for A4
        A4SizeX = 11.75 #inches, for A4
        
        #load EPFL logo png file
        basepath, trash = os.path.split(os.getcwd())
        logoPath = os.path.join(basepath,"IVLab Accessories","EPFL_Logo.png")
        logo = plt.imread(logoPath)

        dataJ = []
        if self.SMU.useReferenceDiode:
            for i in data['i']:
                #i_corr = i * IV_Results['light_int'] / IV_Results['light_int_meas']
                i_corr = i
                dataJ.append(i_corr*1000./IV_Results['active_area'])
        else:
            for i in data['i']:
                dataJ.append(i*1000./IV_Results['active_area'])
        
        #make plot of JV curve
        fig = plt.figure(figsize=(A4SizeX,A4SizeY))
        ax1 = fig.add_axes([0.5,0.4,0.4,0.4]) #x, y, width, height
        ax1.invert_yaxis()
        ax1.set_ylabel("Current density [mA/$cm^2$]")
        ax1.set_xlabel("Voltage [V]")
        ax1.grid(visible=True)
        ax1.axhline(color = 'k') #solid black line across x-axis at y=0
        ax1.plot(data['v'], dataJ, color='red')

        #report header - EPFL logo and cell name
        ax2 = fig.add_axes([0.04,0.80,0.15,0.15])
        ax2.axis('off')
        ax2.imshow(logo)

        #figtext is set relative to the figure.  'text' would be relative to an axis.
        headerText = "Cell Name: " + IV_Results['cell_name'];
        plt.figtext(0.20, 0.85, headerText, weight='bold', fontsize=12, ha='left') #, rotation=15, wrap=True)

        #couldn't find a clean and simple way to print tabular text onto a figure that preserves all the spacings correctly.
        #fill the data into a list of tuples with each tuple containing title, data, and unit strings.
        #then print everything out with a specified spacing.

        #coordinates of run param text columns
        rpX1 = 0.05
        rpX2 = 0.19
        rpY = 0.8
        rpSpace = 0.0225
        params_text = []
        params_text.append(("Measurement Date",dateTimeString, ""))
        params_text.append(("Cell Active Area",str(IV_Results['active_area'])," $cm^2$"))
        params_text.append(("Light Source",self.parameters.lamp['brand'] + " ",self.parameters.lamp['model']))
        if self.SMU.useReferenceDiode:
            params_text.append(("Reference Calibration","{:6.4f}".format(self.SMU.fullSunReferenceCurrent*1000.), " mA"))
            params_text.append(("Calibration Date", self.SMU.calibrationDateTime, ""))
        
        if len(dataFileName) < 35 :
            params_text.append(("Data File Name",dataFileName,""))
        else: # wrap text every 35 characters
            params_text.append(("Data File Name",dataFileName[0:30],""))
            dataFileNameWrap = dataFileName[30:]
            while len(dataFileNameWrap) > 35 :
                params_text.append(("",dataFileNameWrap[0:30],""))
                dataFileNameWrap = dataFileNameWrap[30:]
            #print out the remaining text
            params_text.append(("",dataFileNameWrap,""))
                
        params_text.append(("Current Compliance",str(IV_Results['Imax']*1000.)," mA"))
        #params_text.append(("Settling Time","{:5.3f}".format(IV_Results['dV']/IV_Results['sweep_rate'])," s"))
        params_text.append(("Sweep rate",f"{IV_Results['sweep_rate']*1000:.1f}"," mV/s"))
        params_text.append(("Voltage step",str(IV_Results['dV'])," V"))
        params_text.append(("Meas. Delay",str(IV_Results['Dwell'])," s"))
        for label, data, units in params_text:
            plt.figtext(rpX1, rpY, label, fontsize=10, ha='left')
            plt.figtext(rpX2, rpY, ": " + data + units, fontsize=10, ha='left')
            rpY -= rpSpace


        rtX1 = 0.05
        rtX2 = 0.19
        rtY = 0.45
        rtSpace = 0.0225
        results_text = []
        results_text.append(("Nominal Light Intensity",str(IV_Results['light_int'])," mW/$cm^2$"))
        nominalLightIntensityString = str(IV_Results['light_int']) + " mW/$cm^2$"
        if 'light_int_meas' in IV_Results:
            results_text.append(("Measured Intensity","{:6.2f}".format(IV_Results['light_int_meas'])," mW/$cm^2$"))
        if 'Jsc' in IV_Results:
            results_text.append(("Jsc","{:5.3f}".format(IV_Results['Jsc']), " mA/$cm^2$"))
        if 'Voc' in IV_Results:
            results_text.append(("Voc","{:6.4f}".format(IV_Results['Voc']),"V"))
        if 'FF' in IV_Results:
            results_text.append(("FF","{:6.4f}".format(IV_Results['FF']),""))
        if 'PCE' in IV_Results:
            results_text.append(("PCE","{:5.2f}".format(IV_Results['PCE']),"%"))
        if 'Jmpp' in IV_Results:
            results_text.append(("Jmpp","{:5.3f}".format(IV_Results['Jmpp'])," mA/$cm^2$"))
        if 'Vmpp' in IV_Results:
            results_text.append(("Vmpp","{:6.4f}".format(IV_Results['Vmpp']),"V"))
        if 'Pmpp' in IV_Results:
            results_text.append(("Pmpp","{:7.3f}".format(IV_Results['Pmpp'])," mW/$cm^2$"))
            
        for label, data, units in results_text:
            plt.figtext(rtX1, rtY, label, fontsize=10, ha='left')
            plt.figtext(rtX2, rtY, ": " + data + units, fontsize=10, ha='left')
            rtY -= rtSpace
            
        #footer - measured by and date
        plt.figtext(0.05,0.05,"Measured by: " + uname + " on " + self.parameters.IVsys['sysName'], fontsize = 10, ha = 'left')
        plt.figtext(0.75,0.05,"Date: " + dateTimeString, fontsize = 10, ha = 'left')
            
        plt.savefig(pdfFilePath)
    
    def save_calibration_to_system_settings(self, calibration_params):
        dateTimeString = datetime.datetime.now().strftime("%c") #"%Y%m%d_%H%M%S")
        self.parameters.IVsys['fullSunReferenceCurrent'] = calibration_params['reference_current']
        self.SMU.fullSunReferenceCurrent = calibration_params['reference_current']
        self.parameters.IVsys['calibrationDateTime'] = dateTimeString
        self.SMU.calibrationDateTime = dateTimeString
        settingsFilePath = os.path.join(os.getcwd() , "system_settings.json")
        sys_params = {}
        sys_params['computer'] = self.parameters.computer
        sys_params['IVsys'] = self.parameters.IVsys
        sys_params['lamp'] = self.parameters.lamp
        sys_params['SMU'] = self.parameters.SMU
        with open(settingsFilePath, 'w') as outfile:
            json.dump(sys_params, outfile)                        
    
    def scramble_string(self,name_to_scramble):
        bytename = bytearray(name_to_scramble.encode())
        #use single random byte to scramble the numeric filename.
        random.seed()
        randbyte = random.getrandbits(8)
        hashedBytes = []
        hashedBytes.append(randbyte)
        for i, b in enumerate(bytename):
            hashedBytes.append((hashedBytes[i] + b) % 256)

        numericHash = ''
        for b in hashedBytes:
            numericHash = numericHash + '{:02x}'.format(b)
        
        return numericHash
    
    def unscramble_string(self,string_to_unscramble):   
        #un-scramble the numeric string
        hashedBytesExtracted = []
        for i in range(int(len(string_to_unscramble)/2)):
            hashedBytesExtracted.append(int(string_to_unscramble[i*2:(i+1)*2],16))
            
        #loop through the reversed array and un-do the random convolution, starting from the end and working back.
        HBElen = len(hashedBytesExtracted)
        unHashedBytesReversed = []
        for i, b in enumerate(hashedBytesExtracted):
            if i < HBElen-1:
                unHashedBytesReversed.append((hashedBytesExtracted[HBElen-1-i] - hashedBytesExtracted[HBElen-1-(i+1)]) % 256)
            else:
                pass #The last (first) byte is the random seed.  throw it out.
        
        #this is the string in byte form
        unHashedBytes = bytearray(list(reversed(unHashedBytesReversed)))
    
        return unHashedBytes.decode()
    
    def turn_off(self):
        self.SMU.turn_off()
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