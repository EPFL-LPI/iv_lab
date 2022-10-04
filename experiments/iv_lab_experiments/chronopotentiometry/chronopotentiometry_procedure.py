from datetime import datetime

from iv_lab_controller.base_classes.experiment import Experiment

class Chronopotentiometry(Experiment):
    """
    Run a chronopotentiometry experiment.
    """
    def execute(self, param):
        """
        Runs a chrono-potentiometry measurement.
            Holds the potential constant, and measures the current.
        """
        # self.flag_abortRun = False
        if self.app != None:
            self.app.processEvents()
        
        dateTimeString = datetime.now().strftime("%Y%m%d_%H%M%S")
        
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


