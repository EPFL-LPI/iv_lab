from iv_lab_controller.base_classes.Experiment import Experiment

class IVCurve(Experiment):
    """
    Run an IV curve sweep.
    """
    def __init__(self):
        super().__init__()


    def execute(self):
        """
        Runs a chrono-amperometry measurement.
            Holds the current constant, and measures the potential.
        """
        dateTimeString = datetime.now().strftime("%Y%m%d_%H%M%S")
        
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
        
        # turn the lamp on
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
    

