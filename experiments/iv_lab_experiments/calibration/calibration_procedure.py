import datetime.datetime

from iv_lab_controller.base_classes.experiment import Experiment


class Calibration(Procedure):
    """
    Runs a calibration measurement.
    """
    def execute(self, param):
        # self.flag_abortRun = False
        if self.app != None:
            self.app.processEvents()
        
        dateTimeString = datetime.now().strftime("%Y%m%d_%H%M%S")
        
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
    
