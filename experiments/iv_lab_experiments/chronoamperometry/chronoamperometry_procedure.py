from iv_lab_controller.base_classes.experiment import Experiment
 
class Chronoamperometry(Experiment)
    def execute(self, param):
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
         

