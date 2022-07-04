from ..base_classes.hardware_base import HardwareBase


class SMU(HardwareBase):

    def __init__(self, SMU_details):
        super().__init__()

        self.brand = SMU_details['brand']
        self.model = SMU_details['model']
        self.emulate = SMU_details['emulate']
        self.emulate_v_limit = dict(CHAN_A = 1.0, CHAN_B = 1.0)
        self.emulate_i_limit = dict(CHAN_A = 0.005, CHAN_B = 0.005)
        self.emulate_source_mode = dict(CHAN_A = 'voltage', CHAN_B = 'voltage')
        self.emulate_v_set = dict(CHAN_A = 0.0, CHAN_B = 0.0)
        self.emulate_i_set = dict(CHAN_A = 0.0, CHAN_B = 0.0)
        self.visa_address = SMU_details['visa_address']
        self.visa_library = SMU_details['visa_library']
        
        #configuration variable forward declarations.
        #These should all be overwritten during initialization.
        self.autorange = True 
        self.senseMode = '2wire'
        self.fullSunReferenceCurrent = 1.0
        self.referenceDiodeImax = 0.005
        self.calibrationDateTime = 'Mon, Jan 01 00:00:00 1900'
        
        #data structure to save all current settings for both channels.
        #this is particularly important for the 2400 series sourcemeter which does
        #not actually have two channels but can switch between front and back connectors
        self.smu_v_limit = dict(CHAN_A = 1.0, CHAN_B = 1.0)
        self.smu_i_limit = dict(CHAN_A = 0.005, CHAN_B = 0.005)
        self.smu_v_range = dict(CHAN_A = 5.0, CHAN_B = 5.0)
        self.smu_i_range = dict(CHAN_A = 0.01, CHAN_B = 0.01)
        self.smu_source_mode = dict(CHAN_A = 'voltage', CHAN_B = 'voltage')
        self.smu_display_mode = dict(CHAN_A = 'current', CHAN_B = 'current')
        self.smu_v_set = dict(CHAN_A = 0.0, CHAN_B = 0.0)
        self.smu_i_set = dict(CHAN_A = 0.0, CHAN_B = 0.0)
        self.smu_sense_mode = dict(CHAN_A = "2_wire", CHAN_B = "2_wire")
        self.smu_volt_autorange_mode = dict(CHAN_A = True, CHAN_B = True)
        self.smu_curr_autorange_mode = dict(CHAN_A = True, CHAN_B = True)
        self.smu_output = dict(CHAN_A = 'OFF', CHAN_B = 'OFF')
        self.smu_current_channel = 'CHAN_A'
        
        #IV Params
        self.start_V = -1.
        self.stop_V = 1.
        self.dV = 0.1
        self.sweep_rate = 1 #V/sec
        self.Imax = 0.01
        self.connected = False

    def connect(self):
        if not self.emulate:
            # if we're already connected, treat this as a re-connect.
            # must first disconnect the visa connection before re-connecting.
            try:
                if self.connected: 
                    self.disconnect()
            except:
                #do nothing here.
                pass
                
            if (self.brand == 'Keithley') and (self.model == '2602'):  
                from Keithley26XX import SMU26xx
                
                self.smu = SMU26xx(self.visa_address)
                self.k = self.smu.get_channel(SMU26xx.CHANNEL_A)
                self.kb = self.smu.get_channel(SMU26xx.CHANNEL_B)
                #initial voltage and current range settings.  used if autoranging is off
                self.k.set_voltage_range(2)
                self.k.set_current_range(0.01)
                
                self.kb.set_voltage_range(2)
                self.kb.set_current_range(0.01)
                
                #2nd channel (reference diode) is always used in 2-wire mode.
                self.kb.set_sense_2wire()
                if self.senseMode == '4wire':
                    self.k.set_sense_4wire()
                else:
                    self.k.set_sense_2wire()
                
                self.k.set_measurement_speed_normal() #1 50Hz period - 50 measurements/sec
                self.kb.set_measurement_speed_normal() #1 50Hz period - 50 measurements/sec
                #self.set_measurement_speed_hi_accuracy() #10 50Hz periods - 5 measurements/sec
            
            if (self.brand == 'Keithley') and (self.model == '2400' or self.model == '2401'):
                from pymeasure.instruments.keithley import Keithley2400
                
                # Set the input parameters
                data_points = 50
                averages = 50
                max_current = 0.01
                min_current = -max_current

                # Connect and configure the instrument
                self.smu = Keithley2400(self.visa_address)
                self.smu.reset()
                self.smu.use_front_terminals()
                
                if self.senseMode == '4wire':
                    self.smu.wires = 4
                else:
                    self.smu.wires = 2
                
                self.smu.voltage_nplc = 1 #average voltage measurements over 1 power line cycle
                self.smu.current_nplc = 1 #average current measurements over 1 power line cycle
                
                self.smu.source_current_range = 0.01
                self.smu.compliance_current = 0.01
                self.smu.source_voltage_range = 2.0
                self.smu.compliance_voltage = 2.0
                
                
        self.connected = True
                
    def disconnect(self):
        if not self.emulate:
            if (self.brand == 'Keithley') and (self.model == '2602'):  
                self.smu.disconnect()
                
            if (self.brand == 'Keithley') and (self.model == '2400' or self.model == '2401'):
                #no explicit 'disconnect' function in pymeasure.  disable SMU output in case it is enabled.
                self.smu.disable_source()
                
        self.connected = False
            
                
    def set_IVparams(self, IV_param):
        
        if IV_param['start_V'] != 'Voc':
            self.start_V = IV_param['start_V']
        else:
            self.start_V = 1 # Here a function will be implemented that determines the Voc

        if IV_param['stop_V'] != 'Voc':
            self.stop_V = IV_param['stop_V']
        else: self.stop_V = 0 # Here a function will be implemented that determines the Voc
        

        if self.start_V < self.stop_V:
            self.dV = abs(IV_param['dV'])
        else:
            self.dV = -abs(IV_param['dV'])

        self.sweep_rate = IV_param['sweep_rate']
        self.Imax = IV_param['Imax']

    
    def measure_IVcurve(self, IV_param):
        #IV_param = dict(light_int: float, in mW/cm2, start_V: float, starting voltage or 'Voc', stop_V: float, stop voltage, dV: float, delta V in V, sweep_rate: float in V/s, Imax: float in A)
                
        if (self.brand == 'Keithley') and (self.model == '2602'):

            points = int(abs(((IV_param['stop_V']+IV_param['dV'])-IV_param['start_V'])/IV_param['dV']))
            #Settling time in s
            settling_time = abs(IV_param['dV'])/IV_param['sweep_rate'] - 0.02

            #From the IV parameters, determin a sweep list with Voltages
            #v_smu = np.linspace(self.start_V, self.stop_V, int(abs(((self.stop_V+self.dV)-self.start_V)/self.dV)))
            #smu_sweeplist = np.arange(start_V, stop_V+dV, dV) # np.linspace is better

            #Integration time per data point. Must be between 0.001 to 25 times the power line frequency (50Hz or 60Hz), Switzerland: 50 Hz
            #t_int = 0.1 #s = 5 * 1/(50 Hz)
           
            if not self.emulate:
                
                # Set the current compliance limit
                #self.k.smua.source.limiti = self.Imax
                self.k.set_current_limit(IV_param['Imax'])
                
                #self.k.set_measurement_speed_normal() #1 50Hz period - 50 measurements/sec
                #self.set_measurement_speed_hi_accuracy() #10 50Hz periods - 5 measurements/sec

                (i_smu, v_smu) = self.k.measure_voltage_sweep(IV_param['start_V'], IV_param['stop_V'], settling_time, points)
                
                self.k.disable_output()
                
            else:
                v_smu = np.linspace(IV_param['start_V'], IV_param['stop_V'], int(abs(((IV_param['stop_V']+IV_param['dV'])-IV_param['start_V'])/IV_param['dV'])))
                i_smu = v_smu * 0.1 # This should be a sample curve

            return (v_smu, i_smu)
    
    def set_TTL_level(self,angle_code):
        if not self.emulate:
            if (self.brand == 'Keithley') and (self.model == '2400' or self.model == '2401'):
                self.smu.write(":SOUR2:TTL:LEV " + str(int(angle_code)))
            else:
                raise ValueError("ERROR: smu.set_TTL_level(..) only available for 2400 series sourcemeters")
            
    def set_current_limit(self,channel,Imax):
        if self.emulate:
            self.emulate_i_limit[channel] = Imax
        else:
            if (self.brand == 'Keithley') and (self.model == '2602'):
                if channel == 'CHAN_A' or channel == 'CHAN_BOTH':
                    self.k.set_current_limit(Imax)
                if channel == 'CHAN_B' or channel == 'CHAN_BOTH':
                    self.kb.set_current_limit(Imax)
                    
            if (self.brand == 'Keithley') and (self.model == '2400' or self.model == '2401'):
                if channel != self.smu_current_channel:
                    self.smu_current_channel = channel
                    self.toggle_output_2400(channel)
                    
                self.smu.compliance_current = Imax
                self.smu_i_limit[channel] = Imax
    
    def set_voltage_limit(self,channel,Vmax):
        if self.emulate:
            self.emulate_v_limit[channel] = Vmax
        else:
            if (self.brand == 'Keithley') and (self.model == '2602'):
                if channel == 'CHAN_A' or channel == 'CHAN_BOTH':
                    self.k.set_voltage_limit(Vmax)
                if channel == 'CHAN_B' or channel == 'CHAN_BOTH':
                    self.kb.set_voltage_limit(Vmax)
                    
            if (self.brand == 'Keithley') and (self.model == '2400' or self.model == '2401'):
                if channel != self.smu_current_channel:
                    self.smu_current_channel = channel
                    self.toggle_output_2400(channel)
                    
                self.smu.compliance_voltage = Vmax
                self.smu_v_limit[channel] = Vmax
    
    def enable_current_autorange(self,channel):
        if not self.emulate:
            if (self.brand == 'Keithley') and (self.model == '2602'):
                if channel == 'CHAN_A' or channel == 'CHAN_BOTH':
                    self.k.enable_current_autorange()
                if channel == 'CHAN_B' or channel == 'CHAN_BOTH':
                    self.kb.enable_current_autorange()
                    
            if (self.brand == 'Keithley') and (self.model == '2400' or self.model == '2401'):
                if channel != self.smu_current_channel:
                    self.smu_current_channel = channel
                    self.toggle_output_2400(channel)
                    
                self.smu.write(":CURR:RANG:AUTO ON")
                self.smu_curr_autorange_mode[channel] = True
    
    def enable_voltage_autorange(self,channel):
        if not self.emulate:
            if (self.brand == 'Keithley') and (self.model == '2602'):
                if channel == 'CHAN_A' or channel == 'CHAN_BOTH':
                    self.k.enable_voltage_autorange()
                if channel == 'CHAN_B' or channel == 'CHAN_BOTH':
                    self.kb.enable_voltage_autorange()
                    
            if (self.brand == 'Keithley') and (self.model == '2400' or self.model == '2401'):
                if channel != self.smu_current_channel:
                    self.smu_current_channel = channel
                    self.toggle_output_2400(channel)
                    
                self.smu.write(":VOLT:RANG:AUTO ON")
                self.smu_volt_autorange_mode[channel] = True
    
    def disable_current_autorange(self,channel):
        if not self.emulate:
            if (self.brand == 'Keithley') and (self.model == '2602'):
                if channel == 'CHAN_A' or channel == 'CHAN_BOTH':
                    self.k.disable_current_autorange()
                if channel == 'CHAN_B' or channel == 'CHAN_BOTH':
                    self.kb.disable_current_autorange()
            
            if (self.brand == 'Keithley') and (self.model == '2400' or self.model == '2401'):
                if channel != self.smu_current_channel:
                    self.smu_current_channel = channel
                    self.toggle_output_2400(channel)
                    
                self.smu.write(":CURR:RANG:AUTO OFF")
                self.smu_curr_autorange_mode[channel] = False
    
    def disable_voltage_autorange(self,channel):
        if not self.emulate:
            if (self.brand == 'Keithley') and (self.model == '2602'):
                if channel == 'CHAN_A' or channel == 'CHAN_BOTH':
                    self.k.disable_voltage_autorange()
                if channel == 'CHAN_B' or channel == 'CHAN_BOTH':
                    self.kb.disable_voltage_autorange()
                    
            if (self.brand == 'Keithley') and (self.model == '2400' or self.model == '2401'):
                if channel != self.smu_current_channel:
                    self.smu_current_channel = channel
                    self.toggle_output_2400(channel)
                    
                self.smu.write(":VOLT:RANG:AUTO OFF")
                self.smu_volt_autorange_mode[channel] = False
    
    def set_current_range(self,channel,Irange):
        if not self.emulate:
            if (self.brand == 'Keithley') and (self.model == '2602'):
                if channel == 'CHAN_A' or channel == 'CHAN_BOTH':
                    self.k.set_current_range(Irange)
                if channel == 'CHAN_B' or channel == 'CHAN_BOTH':
                    self.kb.set_current_range(Irange)
                    
            if (self.brand == 'Keithley') and (self.model == '2400' or self.model == '2401'):
                if channel != self.smu_current_channel:
                    self.smu_current_channel = channel
                    self.toggle_output_2400(channel)
                    
                self.smu.current_range = Irange
                self.smu_i_range[channel] = Irange
    
    def set_voltage_range(self,channel,Vrange):
        if not self.emulate:
            if (self.brand == 'Keithley') and (self.model == '2602'):
                if channel == 'CHAN_A' or channel == 'CHAN_BOTH':
                    self.k.set_voltage_range(Vrange)
                if channel == 'CHAN_B' or channel == 'CHAN_BOTH':
                    self.kb.set_voltage_range(Vrange)
                    
            if (self.brand == 'Keithley') and (self.model == '2400' or self.model == '2401'):
                if channel != self.smu_current_channel:
                    self.smu_current_channel = channel
                    self.toggle_output_2400(channel)
                    
                self.smu.voltage_range = Vrange
                self.smu_v_range[channel] = Vrange
    
    def set_mode_current_source(self,channel):
        if self.emulate:
            self.emulate_source_mode[channel] = 'current'
        else:
            if (self.brand == 'Keithley') and (self.model == '2602'):
                if channel == 'CHAN_A' or channel == 'CHAN_BOTH':
                    self.k.set_mode_current_source()
                if channel == 'CHAN_B' or channel == 'CHAN_BOTH':
                    self.kb.set_mode_current_source()
                    
            if (self.brand == 'Keithley') and (self.model == '2400' or self.model == '2401'):
                if channel != self.smu_current_channel:
                    self.smu_current_channel = channel
                    self.toggle_output_2400(channel)
                    
                #2400 series can't change between voltage and current mode while output is on.
                #if the output is on, turn it off during the change and then turn it back on.
                if self.smu_output[channel] == 'ON':
                    self.smu.disable_source()
                self.smu.source_mode = 'current'
                self.smu.measure_voltage(1,self.smu_v_range,self.smu_volt_autorange_mode)
                #output should be on, so turn it back on.
                if self.smu_output[channel] == 'ON':
                    self.smu.enable_source()
                self.smu_source_mode[channel] = 'current'
                
            self.display_voltage(channel)
    
    def set_mode_voltage_source(self,channel):
        if self.emulate:
            self.emulate_source_mode[channel] = 'voltage'
        else:
            if (self.brand == 'Keithley') and (self.model == '2602'):
                if channel == 'CHAN_A' or channel == 'CHAN_BOTH':
                    self.k.set_mode_voltage_source()
                if channel == 'CHAN_B' or channel == 'CHAN_BOTH':
                    self.kb.set_mode_voltage_source()
            
            if (self.brand == 'Keithley') and (self.model == '2400' or self.model == '2401'):
                if channel != self.smu_current_channel:
                    self.smu_current_channel = channel
                    self.toggle_output_2400(channel)
                    
                #2400 series can't change between voltage and current mode while output is on.
                #if the output is on, turn it off during the change and then turn it back on.
                if self.smu_output[channel] == 'ON':
                    self.smu.disable_source()
                self.smu.source_mode = 'voltage'
                self.smu.measure_current(1,self.smu_i_range,self.smu_curr_autorange_mode)
                #output should be on, so turn it back on.
                if self.smu_output[channel] == 'ON':
                    self.smu.enable_source()
                self.smu_source_mode[channel] = 'voltage'
                
            self.display_current(channel)
    
    def display_voltage(self,channel):
        if not self.emulate:
            if (self.brand == 'Keithley') and (self.model == '2602'):
                if channel == 'CHAN_A' or channel == 'CHAN_BOTH':
                    self.k.display_voltage()
                if channel == 'CHAN_B' or channel == 'CHAN_BOTH':
                    self.kb.display_voltage()
            
            if (self.brand == 'Keithley') and (self.model == '2400' or self.model == '2401'):
                if channel != self.smu_current_channel:
                    self.smu_current_channel = channel
                    self.toggle_output_2400(channel)
                    
                self.smu.write("SYST:KEY 15") #set voltage display
                self.smu_display_mode[channel] = 'voltage'
        
    def display_current(self,channel):
        if not self.emulate:
            if (self.brand == 'Keithley') and (self.model == '2602'):
                if channel == 'CHAN_A' or channel == 'CHAN_BOTH':
                    self.k.display_current()
                if channel == 'CHAN_B' or channel == 'CHAN_BOTH':
                    self.kb.display_current()
            
            if (self.brand == 'Keithley') and (self.model == '2400' or self.model == '2401'):
                if channel != self.smu_current_channel:
                    self.smu_current_channel = channel
                    self.toggle_output_2400(channel)
                    
                self.smu.write("SYST:KEY 22") #set current display
                self.smu_display_mode[channel] = 'current'
        
    def set_voltage(self,channel,v):
        if self.emulate:
            self.emulate_v_set[channel] = v
        else:
            if (self.brand == 'Keithley') and (self.model == '2602'):
                if channel == 'CHAN_A' or channel == 'CHAN_BOTH':
                    self.k.set_voltage(v)
                if channel == 'CHAN_B' or channel == 'CHAN_BOTH':
                    self.kb.set_voltage(v)
            
            if (self.brand == 'Keithley') and (self.model == '2400' or self.model == '2401'):
                if channel != self.smu_current_channel:
                    self.smu_current_channel = channel
                    self.toggle_output_2400(channel)
                    
                self.smu.source_voltage = v
                self.smu_v_set[channel] = v
    
    def set_current(self,channel,i):
        if self.emulate:
            self.emulate_i_set[channel] = i
        else:
            if (self.brand == 'Keithley') and (self.model == '2602'):
                if channel == 'CHAN_A' or channel == 'CHAN_BOTH':
                    self.k.set_current(i)
                if channel == 'CHAN_B' or channel == 'CHAN_BOTH':
                    self.kb.set_current(i)
            
            if (self.brand == 'Keithley') and (self.model == '2400' or self.model == '2401'):
                if channel != self.smu_current_channel:
                    self.smu_current_channel = channel
                    self.toggle_output_2400(channel)
                    
                self.smu.source_current = i
                self.smu_i_set[channel] = i
    
    def enable_output(self,channel):
        if not self.emulate:
            if (self.brand == 'Keithley') and (self.model == '2602'):
                if channel == 'CHAN_A' or channel == 'CHAN_BOTH':
                    self.k.enable_output()
                if channel == 'CHAN_B' or channel == 'CHAN_BOTH':
                    self.kb.enable_output()
            
            if (self.brand == 'Keithley') and (self.model == '2400' or self.model == '2401'):
                if channel != self.smu_current_channel:
                    self.smu_current_channel = channel
                    self.toggle_output_2400(channel)
                    
                self.smu.enable_source()
                self.smu_output[channel] = 'ON'
    
    def disable_output(self,channel):
        if not self.emulate:
            if (self.brand == 'Keithley') and (self.model == '2602'):
                if channel == 'CHAN_A' or channel == 'CHAN_BOTH':
                    self.k.disable_output()
                if channel == 'CHAN_B' or channel == 'CHAN_BOTH':
                    self.kb.disable_output()
            
            if (self.brand == 'Keithley') and (self.model == '2400' or self.model == '2401'):
                if channel != self.smu_current_channel:
                    self.smu_current_channel = channel
                    self.toggle_output_2400(channel)
                
                self.smu.disable_source()
                self.smu_output[channel] = 'OFF'
    
    #this function is only intended to be used with keithley 2400 sourcemeters.
    #it handles the change from front to back inputs, allowing them to be implemented in 
    #software as 2 separate channels.
    def toggle_output_2400(self,channel):
        #first disable the sourcemeter output
        self.smu.disable_source()
        #apply the relevant settings
        if channel == 'CHAN_A':
            self.smu.use_front_terminals()
            if self.senseMode == '4wire':
                self.smu.wires = 4
            else:
                self.smu.wires = 2
        else:
            self.smu.use_rear_terminals()
            self.smu.wires = 2 #rear terminal always uses 2-wire
        
        #set the current channel to the new one so that the following
        #function calls will no re-call this function.
        self.smu_current_channel = channel
                
        self.set_voltage_limit(channel,self.smu_v_limit[channel])
        self.set_current_limit(channel,self.smu_i_limit[channel])
        
        if self.smu_curr_autorange_mode[channel]:
            self.enable_current_autorange(channel)
        else:
            self.smu.set_current_range(self.smu_i_range[channel]) #disables autorange
        
        if self.smu_volt_autorange_mode[channel]:
            self.enable_voltage_autorange(channel)
        else:
            self.smu.set_voltage_range(self.smu_v_range[channel]) #disables autorange
        
        self.set_current(channel,self.smu_i_set[channel])
        self.set_voltage(channel,self.smu_v_set[channel])
        
        if self.smu_source_mode[channel] == 'current':
            self.set_mode_current_source(channel)
            self.display_voltage(channel)
        else:
            self.set_mode_voltage_source(channel)
            self.display_current(channel)
            
        #re-enable the output if it was on before
        if self.smu_output[channel] == 'ON':
            self.enable_output(channel)
            
    
    def measure_voltage(self,channel):
        if self.emulate:
            Isc = -1*self.fullSunReferenceCurrent #-0.0016
            Voc = 0.55
            tau = 10
            K = Isc * -1 / np.exp(tau * Voc - 1) #calculate K to get the Voc value we want.
            channelList = ["CHAN_A","CHAN_B"]
            outval = []
            for ch in channelList:
                if self.emulate_source_mode[channel] == 'voltage':
                    outval.append(self.emulate_v_set[ch])
                else:
                    v_out = (np.log((self.emulate_i_set[ch] - Isc) / K) + 1) / tau
                    if v_out < self.emulate_v_limit[ch]*-1:
                        v_out = self.emulate_v_limit[ch]*-1
                    if v_out > self.emulate_v_limit[ch]:
                        v_out = self.emulate_v_limit[ch]
                    outval.append(v_out)
            time.sleep(0.02) #insert 20ms deadtime to simulate keithley integation time
            if channel == "CHAN_A":
                return outval[0]
            if channel == "CHAN_B":
                return outval[1]
            if channel == "CHAN_BOTH":
                return (outval[0], outval[1])
        else:
            if (self.brand == 'Keithley') and (self.model == '2602'):
                if channel == 'CHAN_A':
                    return self.k.measure_voltage()
                elif channel == 'CHAN_B':
                    return self.kb.measure_voltage()
                elif channel == 'CHAN_BOTH':
                    return self.smu.measure_voltage()
            
            if (self.brand == 'Keithley') and (self.model == '2400' or self.model == '2401'):
                return self.smu.voltage
    
    def measure_current(self,channel):
        if self.emulate:
            Isc = -1*self.fullSunReferenceCurrent #-0.0016
            Voc = 0.55
            tau = 10
            K = Isc * -1 / np.exp(tau * Voc - 1) #calculate K to get the Voc value we want.
            channelList = ["CHAN_A","CHAN_B"]
            outval = []
            for ch in channelList:
                if self.emulate_source_mode[ch] == 'current':
                    outval.append(self.emulate_i_set[ch])
                else:
                    i_out = Isc + K*np.exp(tau * self.emulate_v_set[ch] - 1)
                    if i_out < self.emulate_i_limit[ch]*-1:
                        i_out = self.emulate_i_limit[ch]*-1
                    if i_out > self.emulate_i_limit[ch]:
                        i_out = self.emulate_i_limit[ch]
                    outval.append(i_out)
            time.sleep(0.02) #insert 20ms deadtime to simulate keithley integation time
            if channel == "CHAN_A":
                return outval[0]
            if channel == "CHAN_B":
                return outval[1]
            if channel == "CHAN_BOTH":
                return (outval[0], outval[1])
                
        else:
            if (self.brand == 'Keithley') and (self.model == '2602'):
                if channel == 'CHAN_A':
                    return self.k.measure_current()
                elif channel == 'CHAN_B':
                    return self.kb.measure_current()
                elif channel == 'CHAN_BOTH':
                    return self.smu.measure_current()
            
            if (self.brand == 'Keithley') and (self.model == '2400' or self.model == '2401'):
                return self.smu.current
    
    def measure_current_and_voltage(self,channel):
        if self.emulate:
            if channel == "CHAN_BOTH":
                ia, ib = self.measure_current(channel)
                va, vb = self.measure_voltage(channel)
                return (ia, va, ib, vb)
            else: 
                return (self.measure_current(channel), self.measure_voltage(channel))
        else:
            if (self.brand == 'Keithley') and (self.model == '2602'):
                if channel == "CHAN_A":
                    return self.k.measure_current_and_voltage()
                if channel == "CHAN_B":
                    return self.kb.measure_current_and_voltage()
                if channel == "CHAN_BOTH":
                    return self.smu.measure_current_and_voltage()
            
            if (self.brand == 'Keithley') and (self.model == '2400' or self.model == '2401'):
                return [self.smu.current, self.smu_v_set[channel]] #2400 doesn't like to read voltage in voltage mode
    
    def setup_voltage_output(self,channel,Ilimit):
        self.set_current_limit(channel,Ilimit)
        if self.autorange:
            self.enable_current_autorange(channel)
        else:
            self.disable_current_autorange(channel)
            self.set_current_range(channel,Ilimit)
        self.set_mode_voltage_source(channel)
        
    def setup_current_output(self,channel,Vlimit):
        self.set_voltage_limit(channel,Vlimit)
        if self.autorange:
            self.enable_voltage_autorange(channel)
        else:
            self.disable_voltage_autorange(channel)
            self.set_voltage_range(channel,Vlimit)
        self.set_mode_current_source(channel)
        
    def setup_reference_diode(self):
        self.setup_voltage_output("CHAN_B",self.referenceDiodeImax)
        self.set_voltage("CHAN_B",0)
        self.enable_output("CHAN_B")
    
    def measure_IV_point_by_point(self, IV_param):
        self._should_abort = False
        
        #flag to indicate if the scan should be aborted when it reaches Voc
        #this is only to be used for positive-going scans.
        stop_at_voc = False
        
        if IV_param['start_V'] == 'Voc':
            #automatic voltage limits now start at the positive current limit.
            #this has to be measured on-the-fly at the start of the scan to avoid
            #polarization effects in the solar cell.
            #IV_param['start_V'] = IV_param['Vmax'] #self.measureVFwd(IV_param,5)
            pass
        elif IV_param['stop_V'] == 'Voc':
            stop_at_voc = True
            IV_param['stop_V'] = IV_param['Vmax']
        else:
            if abs(IV_param['start_V']) > abs(IV_param['Vmax']):
                raise ValueError("ERROR: measure_IVcurve start voltage outside of compliance range")
            if abs(IV_param['stop_V']) > abs(IV_param['Vmax']):
                raise ValueError("ERROR: measure_IVcurve stop voltage outside of compliance range")
        
        self.emit('status_update', 'Running J-V Scan...')
        logging.debug("Running J-V Scan...")
        
        #measurement interval
        interval = abs(IV_param['dV'])/IV_param['sweep_rate']
        
        #if not self.emulate:
        if True:
            dataV = []
            dataI = []
            dataIref = []
            dataJ = []
            
            if self.useReferenceDiode and self.referenceDiodeParallel:
                self.setup_reference_diode() #This will probably have already been called before during the 
                                         #light level check but we don't lose anything by calling it again.
            
            if IV_param['start_V'] == 'Voc':
                self.setup_current_output("CHAN_A",IV_param['Vmax'])
                self.set_current("CHAN_A",IV_param['Fwd_current_limit'])
                
                #need minimum Dwell time to measure starting point
                if IV_param['Dwell'] < 1.0:
                    IV_param['Dwell'] = 1.0    
            else:
                self.setup_voltage_output("CHAN_A",IV_param['Imax'])
                self.set_voltage("CHAN_A",IV_param['start_V'])
                
            #start the scan
            self.enable_output("CHAN_A")
            
            self.show_status("Stabilizing at initial operating point for " + str(IV_param['Dwell']) + " seconds")
                
            #grab the current timestamp as starting point for dwell period.
            now = datetime.datetime.now()
            timeNow = datetime.datetime.timestamp(now)
            measTime = timeNow + IV_param["Dwell"]
            
            while (timeNow < measTime):
                if IV_param['start_V'] == 'Voc':
                    v = self.measure_voltage("CHAN_A")
                else:
                    i = self.measure_current("CHAN_A")
                if self.useReferenceDiode and self.referenceDiodeParallel:
                    iref = self.measure_current("CHAN_B") #not strictly necessary.  only useful to be sure the current value appears on the potentiostat's screen.
                now = datetime.datetime.now()
                timeNow = datetime.datetime.timestamp(now)
                if self.app != None:
                    self.app.processEvents()
                
                if self.should_abort:
                    break
            
            #if the start voltage is 'Voc', measure the voltage at the current limit and then switch to voltage mode.
            if IV_param['start_V'] == 'Voc':
                IV_param['start_V'] = self.measure_voltage("CHAN_A")
                self.set_voltage("CHAN_A",IV_param['start_V'])
                self.setup_voltage_output("CHAN_A",IV_param['Imax'])
                
            #we finally know all the scan parameters, so generate the voltage list.
            v_smu = np.linspace(IV_param['start_V'], IV_param['stop_V'], int(abs((IV_param['stop_V']-IV_param['start_V'])/abs(IV_param['dV'])) + 1))
            
            self.show_status("Running J-V Scan...")
            
            #grab the current timestamp as starting point for sample timing.
            now = datetime.datetime.now()
            timeNow = datetime.datetime.timestamp(now)
            startTime = datetime.datetime.timestamp(now)
            measTime = startTime #first measurement at time zero
            
            for v in v_smu:
                self.set_voltage("CHAN_A",v)
                now = datetime.datetime.now()
                timeNow = datetime.datetime.timestamp(now)
                
                while (timeNow < measTime):
                    if self.should_abort:
                        break
                        
                    if self.useReferenceDiode and self.referenceDiodeParallel:
                        i, iref = self.measure_current("CHAN_BOTH")
                    else:
                        i = self.measure_current("CHAN_A")
                        
                    now = datetime.datetime.now()
                    timeNow = datetime.datetime.timestamp(now)

                if self.useReferenceDiode and self.referenceDiodeParallel:
                    i, iref = self.measure_current("CHAN_BOTH")
                    if self.win != None:
                        self.win.updateMeasuredLightIntensity(abs(iref*100./self.fullSunReferenceCurrent))
                else:
                    i = self.measure_current("CHAN_A")
                    
                dataI.append(i)
                if self.useReferenceDiode and self.referenceDiodeParallel:
                    dataIref.append(iref)
                    if IV_param['light_int'] > 1.0: #don't correct measurements made in dark or very low light levels
                        lightLevelFactor = abs((iref / self.fullSunReferenceCurrent) * (100.0 / IV_param['light_int']))
                    else:
                        lightLevelFactor = 1.0
                else:
                    dataIref.append(0.)
                    lightLevelFactor = 1.0
                dataJ.append(i*1000./(IV_param['active_area']*lightLevelFactor))
                dataV.append(v)
                
                if self.win != None:
                    self.win.updatePlotIV(dataV, dataJ)
                    
                measTime = measTime + interval
                
                #if we're doing a positive scan to the Fwd current limit and the current is greater, end the scan.
                if stop_at_voc and i > IV_param['Fwd_current_limit']:
                    break
                
                if self.should_abort():
                    break
                
            self.turn_off()
            
        else: #old code for emulate smu mode.  makes a linear curve.
            if IV_param['stop_V'] == 'Voc':
                IV_param['stop_V'] = 0.6
            if IV_param['start_V'] == 'Voc':
                IV_param['start_V'] = 0.6
            v_smu = np.linspace(IV_param['start_V'], IV_param['stop_V'], int(abs((IV_param['stop_V']-IV_param['start_V'])/abs(IV_param['dV'])) + 1))
            dataI = v_smu * 0.1 # This should be a sample curve
            dataIref = v_smu * 0.1 # This should be a sample curve
            dataV = v_smu
            
            if self.win != None:
                self.win.updatePlotIV(v_smu, dataI)
        
        return (dataV, dataI, dataIref)
                                
    def measure_V_time_dependent(self, param):
        self._should_abort = False
        if self.app != None:
            self.app.processEvents()
        dataX = []
        dataV = []
        #param: light int, set current, time, interval
        
        #if not self.emulate:
        if True:
            if abs(param['set_current']) > abs(param['Imax']):
                raise ValueError("ERROR: measure_V_time_dependent set voltage outside of compliance range")
                
            self.setup_current_output("CHAN_A",param['Vmax'])
            self.set_current("CHAN_A",param['set_current'])
            self.enable_output("CHAN_A")
            
            self.show_status("Stabilizing at initial operating point for " + str(param['Dwell']) + " seconds")
                
            #grab the current timestamp as starting point for dwell period.
            now = datetime.datetime.now()
            timeNow = datetime.datetime.timestamp(now)
            measTime = timeNow + param["Dwell"]
            
            while (timeNow < measTime):
                v = self.measure_voltage("CHAN_A")
                now = datetime.datetime.now()
                timeNow = datetime.datetime.timestamp(now)
                
                if self.should_abort():
                    break
            
            self.show_status("Running Constant Current Measurement...")
                
            #grab the current timestamp as starting point for sample timing.
            now = datetime.datetime.now()
            timeNow = datetime.datetime.timestamp(now)
            startTime = datetime.datetime.timestamp(now)
            measTime = startTime #first measurement at time zero
            #run for the prescribed duration, or until abort is pressed.
            while (timeNow - startTime) < param['duration']:
                if timeNow >= measTime:
                    v = self.measure_voltage("CHAN_A")
                    dataV.append(v)
                    dataX.append(timeNow - startTime)
                    
                    if self.win != None:
                        self.win.updatePlotConstantI(dataX, dataV)
                        
                    measTime = measTime + param['interval']
                else:
                    v = self.measure_voltage("CHAN_A")
                
                if self.should_abort():
                    break
                        
                now = datetime.datetime.now()
                timeNow = datetime.datetime.timestamp(now)
                
            self.turn_off()
        else:
            dataX = np.linspace(0, param['duration'], int((param['duration']/param['interval']) + 1))
            dataV = dataX * 0.1 # This should be a sample curve
            
            if self.win != None:
                self.win.updatePlotConstantI(dataX, dataV)
                
        return (dataX, dataV)

    def measure_I_time_dependent(self, param):
        self._should_abort = False

        dataX = []
        dataI = []
        dataIcorr = []
        dataJ = []
        #param: light int, set voltage, time, interval
        #if not self.emulate:
        if True:
            if abs(param['set_voltage']) > abs(param['Vmax']):
                raise ValueError("ERROR: measure_I_time_dependent set voltage outside of compliance range")
                
            self.setup_voltage_output("CHAN_A",param['Imax'])
            self.set_voltage("CHAN_A",param['set_voltage'])
            self.enable_output("CHAN_A")
            
            self.show_status("Stabilizing at initial operating point for " + str(param['Dwell']) + " seconds")
                
            #grab the current timestamp as starting point for dwell period.
            now = datetime.datetime.now()
            timeNow = datetime.datetime.timestamp(now)
            measTime = timeNow + param["Dwell"]
            
            while (timeNow < measTime):
                i = self.measure_current("CHAN_A")
                now = datetime.datetime.now()
                timeNow = datetime.datetime.timestamp(now)
                
                if self.should_abort():
                    break
            
            self.show_status("Running Constant Voltage Measurement...")
            
            #grab the current timestamp as starting point for sample timing.
            now = datetime.datetime.now()
            timeNow = datetime.datetime.timestamp(now)
            startTime = datetime.datetime.timestamp(now)
            measTime = startTime #first measurement at time zero
            #run for the prescribed duration, or until abort is pressed.
            while (timeNow - startTime) < param['duration']:
                if timeNow >= measTime:
                    i = self.measure_current("CHAN_A")
                    dataI.append(i)
                    if self.useReferenceDiode and self.referenceDiodeParallel:
                        i_corr = i * param['light_int'] / param['light_int_meas']
                        dataIcorr.append(i_corr)
                        dataJ.append(i_corr*1000./param['active_area'])
                    else:
                        dataIcorr.append(0.0)
                        dataJ.append(i*1000./param['active_area'])
                    
                    dataX.append(timeNow - startTime)
                    
                    if self.win != None:
                        self.win.updatePlotConstantV(dataX, dataJ)
                        
                    measTime = measTime + param['interval']
                else:
                    i = self.measure_current("CHAN_A")
                    
                if self.should_abort():
                    break
                        
                now = datetime.datetime.now()
                timeNow = datetime.datetime.timestamp(now)
            
            self.turn_off()
        else:
            dataX = np.linspace(0, param['duration'], int((param['duration']/param['interval']) + 1))
            dataI = dataX * 0.1 # This should be a sample curve
            dataIcorr = dataX * 0.1 # This should be a sample curve
            
            if self.win != None:
                self.win.updatePlotConstantV(dataX, dataI)
        
        return (dataX, dataIcorr, dataI)
    
    def measure_MPP_time_dependent(self, param):
        self._should_abort = False
            
        dataX = []
        dataW = []
        dataI = []
        dataIcorr = []
        dataJ = []
        dataV = []
        
        #if not self.emulate:    
        if True:
            #if start voltage is auto, run a JV scan first to determine Vmpp
            if param['start_voltage'] == 'auto':
                
                self.show_status("Running reverse JV to find MPP starting voltage...")
                
                time.sleep(1)
                IV_params = {}
                IV_params['light_int'] = param['light_int']
                IV_params['start_V'] = 'Voc'
                IV_params['Fwd_current_limit'] = param['Imax']/10.
                IV_params['stop_V'] = 0
                IV_params['dV'] = 0.02
                IV_params['sweep_rate'] = 0.1
                IV_params["Dwell"] = param['Dwell']
                IV_params['Imax'] = param['Imax']
                IV_params['Vmax'] = param['Vmax']
                IV_params['active_area'] = param['active_area']
                IV_params['cell_name'] = param['cell_name']
                
                if self.win != None:
                    self.win.menuSelectMeasurement.setCurrentIndex(0) #set gui to display JV
                    
                (v_smu, i_smu, i_ref) = self.measure_IV_point_by_point(IV_params)
                
                if self.win != None:
                    self.win.menuSelectMeasurement.setCurrentIndex(3) #set gui to display MPP
                    
                p_smu = []
                for v, i in zip(v_smu, i_smu):
                    p_smu.append(v*i*-1)
                max_power = max(p_smu)
                max_power_index = p_smu.index(max_power)
                V_MPP = v_smu[max_power_index]
            else:    #manual start voltage
                V_MPP = param['start_voltage']
                if abs(param['start_voltage']) > abs(param['Vmax']):
                    raise ValueError("ERROR: measure_MPP_time_dependent start voltage outside of compliance range")
                    
            v_step = param['voltage_step']
            step_direction = 1
            v_step_max = param['voltage_step_max']
            v_step_min = param['voltage_step_min']
            MPPStepGain = param['MPP_step_gain']
            steps = []
            last_power = 0.0
            #param: light int, start voltage, time, interval
        
            self.setup_voltage_output("CHAN_A",param['Imax'])
            self.set_voltage("CHAN_A",V_MPP)
            self.enable_output("CHAN_A")
            
            self.show_status("Stabilizing at initial operating point for " + str(param['Dwell']) + " seconds")
            
            #grab the current timestamp as starting point for dwell period.
            now = datetime.datetime.now()
            timeNow = datetime.datetime.timestamp(now)
            measTime = timeNow + param["Dwell"]
            
            #stay on the initial setpoint for the specified time
            while (timeNow < measTime):
                i = self.measure_current("CHAN_A")
                now = datetime.datetime.now()
                timeNow = datetime.datetime.timestamp(now)
                
                if self.should_abort():
                    break
            
            #grab the current timestamp as starting point for sample timing.
            now = datetime.datetime.now()
            timeNow = datetime.datetime.timestamp(now)
            startTime = datetime.datetime.timestamp(now)
            measTime = startTime #first measurement at time zero
            #run for the prescribed duration, or until abort is pressed.
            while (timeNow - startTime) < param['duration']:
                if timeNow >= measTime:
                    #measure power
                    (i, v) = self.measure_current_and_voltage("CHAN_A")
                    if self.useReferenceDiode and self.referenceDiodeParallel: #correct measured current for actual light level
                        i_corr = i * param['light_int'] / param['light_int_meas']
                        w = i_corr * v * -1000./param['active_area'] #cell voltage is positive, current is negative.
                        dataIcorr.append(i_corr)
                        dataJ.append(i_corr*1000./param['active_area'])
                    else:
                        w = i * v * -1000./param['active_area'] #cell voltage is positive, current is negative.
                        dataIcorr.append(0)
                        dataJ.append(i*1000./param['active_area'])
                    #append data and plot
                    dataW.append(w)
                    dataX.append(timeNow - startTime)
                    dataI.append(i)
                    dataV.append(v)
                    
                    if self.win != None:
                        self.win.updatePlotMPP(dataX, dataW)
                        self.win.updatePlotMPPIV(dataX, dataV, dataJ)
                        
                    #increment the next measurement time
                    measTime = measTime + param['interval']
                    
                    #MPP Algorithm (perturb-and-observe)
                    #a simple MPP algoithm that constantly moves the voltage by a certain step size
                    #and observes if the power increases of decreases.  Here we use
                    #adaptive voltage stepping based on the trend of the last 6 steps.
                    #the sum of the trend can be either +/-6, +/-4, +/-2, or 0.
                    #in steady-state the sum of the trend should be 0. 
                    #if we are off the peak the trend will be going strongly in one direction
                    #and the algorithm will increase the step size to get there more quickly.
                    #once the tracking settles the step size will be decreased until it reaches
                    #the noise level.  Noise events will cause the step size to momentarily increase
                    #which is desireable as the algorithm is not reactive enough with a very small
                    #step size which is lost in the noise.
                    
                    if w < last_power:
                        #if the power is less than the last time then we're going the wrong way
                        step_direction *= -1
                    
                    
                    #adaptive step-size algorithm
                    steps.append(step_direction)
                    if len(steps) >= 6:
                        trend = sum(steps[len(steps)-6:])
                        #increase the step size if there is a noticeable trend to get there faster.
                        if abs(trend) >= 3:
                            v_step *= 2
                            steps = [] #reset steps history when changing scale
                            if v_step > v_step_max:
                                v_step = v_step_max
                        #if there is no trend and we are not yet at the minimum, decrease the step size.
                        elif v_step > v_step_min:
                            v_step /= 2
                            steps = [] #reset steps history when changing scale
                            if v_step < v_step_min:
                                v_step = v_step_min
                    
                    next_step = v_step * step_direction
                    
                    #step the MPP voltage by v_step and repeat
                    V_MPP = V_MPP + next_step
                    
                    #force V_MPP to stay within voltage compliance range§
                    if V_MPP > abs(param['Vmax']):
                        V_MPP = abs(param['Vmax'])
                    if V_MPP < -1*abs(param['Vmax']):
                        V_MPP = -1*abs(param['Vmax'])
                        
                    self.set_voltage("CHAN_A",V_MPP)
                    last_power = w
                    
                    self.show_status("Running MPP Measurement. v_step: " + str(v_step))
                        
                    dI = i - dataI[len(dataI)-1]
                    
                    
                else:
                    i = self.measure_current("CHAN_A") #to keep the keithley display current...
                
                if self.should_abort():
                    break

                now = datetime.datetime.now()
                timeNow = datetime.datetime.timestamp(now)
                
            self.turn_off()
        else:
            dataX = np.linspace(0, param['duration'], int((param['duration']/param['interval']) + 1))
            dataV = dataX * 0.1 # This should be a sample curve
            dataI = dataX * -0.1 # This should be a sample curve
            dataIcorr = dataX * -0.1 # This should be a sample curve
            dataW = []
            for v, i in zip(dataV, dataI):
                dataW.append(v*i)
            
            if self.win != None:
                self.win.updatePlotMPP(dataX, dataW)
                self.win.updatePlotMPPIV(dataX, dataV, dataI)

        return (dataX, dataV, dataIcorr, dataI)
    
    def measure_reference_calibration(self, param):
        self._should_abort = False
            
        dataXMeas = []
        dataMeas = []
        dataXRef = []
        dataRef = []
        dataMeasmA = []
        dataRefmA = []
        #param: light int, set voltage, time, interval
        
        if True:
            if self.referenceDiodeParallel:
                channelList = ['CHAN_BOTH']
            else:
                channelList = ['CHAN_A','CHAN_B']
            for measurement_channel in channelList:
                if abs(param['set_voltage']) > abs(param['Vmax']):
                    raise ValueError("ERROR: measure_I_time_dependent set voltage outside of compliance range")
                
                if measurement_channel == 'CHAN_A' or measurement_channel == 'CHAN_BOTH':
                    self.setup_voltage_output("CHAN_A",param['Imax'])
                    self.set_voltage("CHAN_A",0.0) #param['set_voltage'])
                if measurement_channel == 'CHAN_B' or measurement_channel == 'CHAN_BOTH':
                    self.setup_reference_diode()
                self.enable_output(measurement_channel)
                
                self.show_status("Stabilizing at initial operating point for " + str(param['Dwell']) + " seconds")
                    
                #grab the current timestamp as starting point for dwell period.
                now = datetime.datetime.now()
                timeNow = datetime.datetime.timestamp(now)
                measTime = timeNow + param["Dwell"]
                
                while (timeNow < measTime):
                    i = self.measure_current(measurement_channel)
                    now = datetime.datetime.now()
                    timeNow = datetime.datetime.timestamp(now)
                    
                    if self.should_abort():
                        break
                
                self.show_status("Running Constant Voltage Measurement...")
                    
                #grab the current timestamp as starting point for sample timing.
                now = datetime.datetime.now()
                timeNow = datetime.datetime.timestamp(now)
                startTime = datetime.datetime.timestamp(now)
                measTime = startTime #first measurement at time zero
                #run for the prescribed duration, or until abort is pressed.
                while (timeNow - startTime) < param['duration']:
                    if timeNow >= measTime:
                        if measurement_channel == 'CHAN_A':
                            i = self.measure_current(measurement_channel)
                        elif measurement_channel == 'CHAN_B':
                            i_ref = self.measure_current(measurement_channel)
                        elif measurement_channel == 'CHAN_BOTH':
                            i, i_ref = self.measure_current(measurement_channel)
                        
                        if measurement_channel == 'CHAN_A' or measurement_channel == 'CHAN_BOTH':
                            dataMeas.append(i)
                            dataMeasmA.append(i*1000.)
                            dataXMeas.append(timeNow - startTime)
                        if measurement_channel == 'CHAN_B' or measurement_channel == 'CHAN_BOTH':
                            dataRef.append(i_ref)
                            dataRefmA.append(i_ref*1000.)
                            dataXRef.append(timeNow - startTime)
                        
                        if self.win != None:
                            self.win.updatePlotCalibration(dataXMeas, dataMeasmA, dataXRef, dataRefmA)
                            
                        measTime = measTime + param['interval']
                    else: #make a dummy measurement to keep the display active
                        i = self.measure_current(measurement_channel)
                    
                    if self.should_abort():
                        break

                    now = datetime.datetime.now()
                    timeNow = datetime.datetime.timestamp(now)
                
                self.turn_off()
        else:
            dataX = np.linspace(0, param['duration'], int((param['duration']/param['interval']) + 1))
            dataMeas = dataX * 0.1 # This should be a sample curve
            dataRef = dataX * 0.11 # This should be a sample curve
            
            if self.win != None:
                self.win.updatePlotCalibration(dataXMeas, dataMeasmA, dataXRef, dataRefmA)
        
        #number of points could be different in meas and ref in the serial measurement case.
        #take the x array with the fewer number of points and take off the last value of the
        #larger data array if this is the case
        if len(dataXMeas) == len(dataXRef):
            dataX = dataXMeas
        elif len(dataXMeas) > len(dataXRef):
            dataX = dataXRef
            dataMeas = dataMeas[0:len(dataX)-1]
        elif len(dataXMeas) < len(dataXRef):
            dataX = dataXMeas
            dataRef = dataRef[0:len(dataX)-1]
        
        return (dataX, dataMeas, dataRef)
    
    def checkVOCPolarity(self, param):
        if not self.emulate:    
            v = self.measureVoc(param, 1)
            if v < 0.:
                return False
            else:
                return True
        else:
            return True
            
    def measureVoc(self, param, wait):
        #if not self.emulate:    
        self.setup_current_output("CHAN_A",param['Vmax'])
        self.set_current("CHAN_A",0)
        self.enable_output("CHAN_A")
        now = datetime.datetime.now()
        startTime = datetime.datetime.timestamp(now)
        # first measurement time is startTime plus initial dwell time
        measTime = startTime + wait
        now = datetime.datetime.now()
        timeNow = datetime.datetime.timestamp(now)
        while timeNow < measTime:
            v = self.measure_voltage("CHAN_A")
            time.sleep(0.1)
            
            if self.should_abort():
                return -1.

            now = datetime.datetime.now()
            timeNow = datetime.datetime.timestamp(now)
            
        v = self.measure_voltage("CHAN_A")
        self.disable_output("CHAN_A")
        return v
        #else:
            #return 1.2
            
    def measureVFwd(self, param, wait):
        #if not self.emulate:    
        self.setup_current_output("CHAN_A",param['Vmax'])
        self.set_current("CHAN_A",float(param['Fwd_current_limit']))
        self.enable_output("CHAN_A")
        now = datetime.datetime.now()
        startTime = datetime.datetime.timestamp(now)
        # first measurement time is startTime plus initial dwell time
        measTime = startTime + wait
        now = datetime.datetime.now()
        timeNow = datetime.datetime.timestamp(now)
        while timeNow < measTime:
            v = self.measure_voltage("CHAN_A")
            time.sleep(0.1)
            
            if self.should_abort():
                return -1.

            now = datetime.datetime.now()
            timeNow = datetime.datetime.timestamp(now)
            
        v = self.measure_voltage("CHAN_A")
        self.disable_output("CHAN_A")
        return v
        #else:
            #return 1.2
    
    def measureLightIntensity(self, wait):
        #if not self.emulate:
        self.setup_reference_diode()
        
        i_ref = []
        now = datetime.datetime.now()
        startTime = datetime.datetime.timestamp(now)
        # first measurement time is startTime plus initial dwell time
        measTime = startTime + wait
        now = datetime.datetime.now()
        timeNow = datetime.datetime.timestamp(now)
        while timeNow < measTime:
            i_ref.append(self.measure_current("CHAN_B"))
            time.sleep(0.1)
            
            if self.should_abort():
                return -1.

            now = datetime.datetime.now()
            timeNow = datetime.datetime.timestamp(now)
            
        self.disable_output("CHAN_B")
        averageCurrent = sum(i_ref)/len(i_ref)
        lightLevel = abs(100.0 * averageCurrent / self.fullSunReferenceCurrent)
        
        if self.win != None:
            self.win.updateMeasuredLightIntensity(lightLevel)
        else:
            print("Measured light intensity: " + str(lightLevel) + "mW/cm^2")
        
        return lightLevel
        #else:
            #return 100.0
            
    def turn_off(self):
        
        if self.brand == 'Keithley':
            if self.model == '2602':
                if not self.emulate:
                    #self.k.smua.source.output = self.k.smua.OUTPUT_OFF   # turn off SMUA
                    self.k.disable_output()
                    self.kb.disable_output()
            if self.model == '2400' or self.model == '2401':
                if not self.emulate:
                    #self.k.smua.source.output = self.k.smua.OUTPUT_OFF   # turn off SMUA
                    self.smu.disable_source()
      