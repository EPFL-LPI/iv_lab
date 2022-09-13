import time
import datetime
import os
import json
import random
import math
# from Keithley26XX import SMU26xx # this is imported in the code if keithley not emulated
# from pymeasure.instruments.keithley import Keithley2400 # this is imported in the code if keithley not emulated
# import pyvisa #used for oriel lamp
from IV_gui import Window
from PyQt5.QtWidgets import QApplication, QMessageBox
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import socket
import sys
import bric_analysis_libraries.jv.jv_analysis as bric_jv


class syst_param:
    #This class contains all the system parameters, i.e. computer, operating system, lamp, SMU, filters, shutter...    
    def __init__(self, **kwargs):
    
        self.lamp = None
        self.arduino = None
        self.SMU = None
    
        for key, value in kwargs.items():
            if key == 'computer':
                self.computer = value
            elif key == 'IVsys':
                self.IVsys = value
            elif key == 'lamp':
                self.lamp = value
                #self.lamp['emulate'] = False
            elif key == 'arduino':
                self.arduino = value
                #self.arduino['emulate'] = False
            elif key == 'SMU':
                self.SMU = value
                #self.SMU['emulate'] = False
                
    def emulate_lamp_on(self):
        self.lamp['emulate'] = True
        
    def emulate_lamp_off(self):
        self.lamp['emulate'] = False
    
    def emulate_arduino_on(self):
        if self.arduino != None:
            self.arduino['emulate'] = True
        
    def emulate_arduino_off(self):
        if self.arduino != None:
            self.arduino['emulate'] = False
        
    def emulate_SMU_on(self):
        self.SMU['emulate'] = True

    def emulate_SMU_off(self):
        self.SMU['emulate'] = False
        
    def emulate_lamp_and_SMU_on(self):
        self.lamp['emulate'] = True
        self.SMU['emulate'] = True
        
    def emulate_lamp_and_SMU_off(self):
        self.lamp['emulate'] = False
        self.SMU['emulate'] = False

   
class arduino:
    def __init__(self, hardware,  **kwargs):  
        for key, value in kwargs.items():
            if key == 'app':
                self.app = value
            if key == 'gui':
                self.win = value
                
        self.brand = hardware['brand']
        self.model = hardware['model']
        self.emulate = hardware['emulate']
        
        self.cell_stage_settling_time = 5.0
        
        #import pyvisa
        self.visa_address = hardware['visa_address']
        #self.visa_library = hardware['visa_library']
        
        self.connected = False
           
    def show_status(self,msg):
        if self.app != None:
            self.win.showStatus(msg)
            self.app.processEvents()
        else:
            print(msg)
    
    def abortRunFlag(self):
        if self.win != None:
            return self.win.flag_abortRun
        else:
            return False
    
    def connect(self):
        if self.connected:
            self.disconnect()
        
        if not self.emulate:
            import pyvisa
            self.rm = pyvisa.ResourceManager() #visa_library = "C:\\Windows\\SysWOW64\\visa32.dll")
            # print(rm.list_resources())
            self.ard = self.rm.open_resource(self.visa_address)
            
            self.ard.baud_rate = 115200
            self.ard.read_termination = '\n'
            self.ard.write_termination = '\n'
            self.ard.send_end = True
            self.ard.query_delay = 0.05
            self.ard.timeout = 1000 
            
            #verify identifier to be sure we have a good connection
            ard_idn = self.ard.query("*IDN?")
            #expect response to be “Newport Corporation,LSS-7120,[sn#],[rev#]”
            if ard_idn[0:27] != "Newport Corporation,LSS-7120":
                raise ValueError("Oriel lamp IDN incorrect: " + ard_idn)
                
        
        self.connected = True
    
    def disconnect(self):
        self.connected = False
        
        if not self.emulate:
            self.ard.close()
                    
    def shutter_open(self):
        self.arduino_digital_command(2,1)

    def shutter_close(self):
        self.arduino_digital_command(2,0)
                
    def select_reference_cell(self):
        self.arduino_digital_command(4,0)
        time.sleep(self.cell_stage_settling_time)
    
    def select_test_cell(self):
        self.arduino_digital_command(4,1)
        time.sleep(self.cell_stage_settling_time)
    
    def arduino_digital_command(self,pin,value):
        if not self.emulate:
            self.ard.write("6," + str(int(pin)) + "," + str(int(value)))
        
   
class SMU:
    def __init__(self, SMU_details, **kwargs):
        self.app = None
        self.win = None
        for key, value in kwargs.items():
            if key == 'app':
                self.app = value
            if key == 'gui':
                self.win = value

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
        self.measSpeed = "normal"
        self.useReferenceDiode = True
        # these three are overwritten from config file values in the 'system' initialization 
        self.fullSunReferenceCurrent = 1.0
        self.referenceDiodeImax = 0.005
        self.calibrationDateTime = 'Mon, Jan 01 00:00:00 1900'
        
        self.meas_period_min = 1/16 # this value is overwritten in 'connect' based on the type of SMU selected

        if "senseMode" in SMU_details:
            self.senseMode = SMU_details["senseMode"]
        if "autorange" in SMU_details:
            self.autorange = SMU_details["autorange"]
        if "measSpeed" in SMU_details:
            self.measSpeed = SMU_details["measSpeed"]
        if "useReferenceDiode" in SMU_details:
            self.useReferenceDiode = SMU_details["useReferenceDiode"]
        
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
        
    def show_status(self,msg):
        if self.app != None:
            self.win.showStatus(msg)
            self.app.processEvents()
        else:
            print(msg)
            
    def abortRunFlag(self):
        if self.win != None:
            self.app.processEvents()
            return self.win.flag_abortRun
        else:
            return False
    
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
                
                if self.measSpeed == 'fast':
                    self.k.set_measurement_speed_fast() # 200µs integration time
                    self.kb.set_measurement_speed_fast() # 200µs integration time
                    self.meas_period_min = 1/65 # measured value
                elif self.measSpeed == 'medium':
                    self.k.set_measurement_speed_med() # 2ms integration time
                    self.kb.set_measurement_speed_med() # 2ms integration time
                    self.meas_period_min = 1/50 # measured value
                else : # self.measSpeed == 'normal':
                    self.k.set_measurement_speed_normal() # 20ms integration time
                    self.kb.set_measurement_speed_normal() # 20ms integration time
                    self.meas_period_min = 1/16 # measured value
                
                #self.set_measurement_speed_hi_accuracy() #10 50Hz periods - 5 measurements/sec
                
                #these are all in the programming manual for the 2600 series but all give errors on the 2602 used for testing.
                #self.smu.write_lua("smua.source.delay = smua.DELAY_OFF")
                #self.smu.write_lua("smua.measure.delay = smua.DELAY_OFF")
                #self.smu.write_lua("trigger.timer[1].delay = 0.0")
            
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
                
                if self.measSpeed == 'fast':
                    self.smu.voltage_nplc = 0.01 #average voltage measurements over 0.01 power line cycle
                    self.smu.current_nplc = 0.01 #average current measurements over 0.01 power line cycle
                elif self.measSpeed == 'medium':
                    self.smu.voltage_nplc = 0.1 #average voltage measurements over 0.1 power line cycle
                    self.smu.current_nplc = 0.1 #average current measurements over 0.1 power line cycle
                else : # self.measSpeed == 'normal':
                    self.smu.voltage_nplc = 1 #average voltage measurements over 1 power line cycle
                    self.smu.current_nplc = 1 #average current measurements over 1 power line cycle
                
                #measurement speed is limited by the interface for keithley 2400.
                #all 3 speeds were measured for the 2 interfaces and gave the same max rate.
                if self.visa_address[0:4] == 'ASRL':
                    self.meas_period_min = 1/6 # measured value
                else:
                    self.meas_period_min = 1/8.5 # measured value
                
                self.smu.source_current_range = 0.01
                self.smu.compliance_current = 0.01
                self.smu.source_voltage_range = 2.0
                self.smu.compliance_voltage = 2.0
                self.smu.trigger_delay = 0.0
                self.smu.source_delay = 0.0
                
                #disable beep sound when output enabled
                self.smu.write(":SYST:BEEP:STAT OFF")
                
                
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
        #function calls will not re-call this function.
        self.smu_current_channel = channel
                
        self.set_voltage_limit(channel,self.smu_v_limit[channel])
        self.set_current_limit(channel,self.smu_i_limit[channel])
        
        if self.smu_curr_autorange_mode[channel]:
            self.enable_current_autorange(channel)
        else:
            self.set_current_range(channel,self.smu_i_range[channel]) #disables autorange
        
        if self.smu_volt_autorange_mode[channel]:
            self.enable_voltage_autorange(channel)
        else:
            self.set_voltage_range(channel,self.smu_v_range[channel]) #disables autorange
        
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
                if self.emulate_source_mode[ch] == 'voltage':
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
        # self.flag_abortRun = False
        if self.app != None:
            self.app.processEvents()
        
        #flag to indicate if the scan should be aborted when it reaches Voc
        #this is only to be used for positive-going scans.
        stop_at_voc = False
        
        if IV_param['start_V'] == 'Voc':
            #automatic voltage limits now start at the positive current limit.
            #this has to be measured on-the-fly at the start of the scan to avoid
            #polarization effects in the solar cell.
            if self.app != None:
                self.app.processEvents()
            #IV_param['start_V'] = IV_param['Vmax'] #self.measureVFwd(IV_param,5)
        elif IV_param['stop_V'] == 'Voc':
            stop_at_voc = True
            IV_param['stop_V'] = IV_param['Vmax']
        else:
            if abs(IV_param['start_V']) > abs(IV_param['Vmax']):
                raise ValueError("ERROR: measure_IVcurve start voltage outside of compliance range")
            if abs(IV_param['stop_V']) > abs(IV_param['Vmax']):
                raise ValueError("ERROR: measure_IVcurve stop voltage outside of compliance range")
        
        #measurement interval
        interval = abs(IV_param['dV'])/IV_param['sweep_rate']
        
        self.show_status("Running J-V Scan...")
        
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
            
            if self.abortRunFlag():
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
                if self.abortRunFlag():
                    break
                    
                if self.useReferenceDiode and self.referenceDiodeParallel:
                    i, iref = self.measure_current("CHAN_BOTH")
                else:
                    i = self.measure_current("CHAN_A")
                    
                now = datetime.datetime.now()
                timeNow = datetime.datetime.timestamp(now)

            if self.useReferenceDiode and self.referenceDiodeParallel:
                i, iref = self.measure_current("CHAN_BOTH")
                dataIref.append(iref)
                if self.win != None:
                    self.win.updateMeasuredLightIntensity(abs(iref*100./self.fullSunReferenceCurrent))
            else:
                i = self.measure_current("CHAN_A")
                dataIref.append(0.)
                
            dataI.append(i)
            dataJ.append(i*1000./IV_param['active_area'])
            dataV.append(v)
            
            if self.win != None:
                self.win.updatePlotIV(dataV, dataJ)
                
            measTime = measTime + interval
            
            #if we're doing a positive scan to the Fwd current limit and the current is greater, end the scan.
            if stop_at_voc and i > IV_param['Fwd_current_limit']:
                break
            
            if self.abortRunFlag():
                break
            
        self.turn_off()
        
        return (dataV, dataI, dataIref)
                                
    def measure_V_time_dependent(self, param):
        # self.flag_abortRun = False
        if self.app != None:
            self.app.processEvents()
        dataX = []
        dataV = []
        #param: light int, set current, time, interval
        
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
            
            if self.abortRunFlag():
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
            
            if self.abortRunFlag():
                break
                    
            now = datetime.datetime.now()
            timeNow = datetime.datetime.timestamp(now)
            
        self.turn_off()
                
        return (dataX, dataV)

    def measure_I_time_dependent(self, param):
        # self.flag_abortRun = False
        if self.app != None:
            self.app.processEvents()
        dataX = []
        dataI = []
        dataIref = []
        dataJ = []
        #param: light int, set voltage, time, interval
        
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
            if self.useReferenceDiode and self.referenceDiodeParallel:
                i, iref = self.measure_current("CHAN_BOTH")
                if self.win != None:
                    self.win.updateMeasuredLightIntensity(abs(iref*100./self.fullSunReferenceCurrent))
            else:
                i = self.measure_current("CHAN_A")
                
            now = datetime.datetime.now()
            timeNow = datetime.datetime.timestamp(now)
            
            if self.abortRunFlag():
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
                
                if self.useReferenceDiode and self.referenceDiodeParallel:
                    i, iref = self.measure_current("CHAN_BOTH")
                    dataIref.append(iref)
                    if self.win != None:
                        self.win.updateMeasuredLightIntensity(abs(iref*100./self.fullSunReferenceCurrent))
                else:
                    i = self.measure_current("CHAN_A")
                    dataIref.append(0.)
                    
                dataI.append(i)
                dataJ.append(i*1000./param['active_area'])
                dataX.append(timeNow - startTime)
                
                if self.win != None:
                    self.win.updatePlotConstantV(dataX, dataJ)
                    
                measTime = measTime + param['interval']
            else:
                if self.useReferenceDiode and self.referenceDiodeParallel:
                    i, iref = self.measure_current("CHAN_BOTH")
                else:
                    i = self.measure_current("CHAN_A")
                
            if self.abortRunFlag():
                break
                    
            now = datetime.datetime.now()
            timeNow = datetime.datetime.timestamp(now)
        
        self.turn_off()
        
        return (dataX, dataI, dataIref)
    
    def measure_MPP_time_dependent(self, param):
        # self.flag_abortRun = False
        if self.app != None:
            self.app.processEvents()
            
        dataX = []
        dataW = []
        dataI = []
        dataIref = []
        dataJ = []
        dataV = []
        
        #if start voltage is auto, run a JV scan first to determine Vmpp
        if param['start_voltage'] == 'auto':
            
            self.show_status("Running reverse JV to find MPP starting voltage...")
            
            time.sleep(1)
            IV_params = {}
            IV_params['light_int'] = param['light_int']
            IV_params['start_V'] = 'Voc'
            IV_params['Fwd_current_limit'] = param['Imax']/10.
            IV_params['stop_V'] = 0
            IV_params['dV'] = 0.005
            IV_params['sweep_rate'] = 0.02
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
            
            if self.abortRunFlag():
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
                if self.useReferenceDiode and self.referenceDiodeParallel:
                    (i, v, i_ref, v_ref) = self.measure_current_and_voltage("CHAN_BOTH")
                    if self.win != None:
                        self.win.updateMeasuredLightIntensity(abs(i_ref*100./self.fullSunReferenceCurrent))
                    dataIref.append(i_ref)
                else:
                    (i, v) = self.measure_current_and_voltage("CHAN_A")
                    dataIref.append(0)
                
                w = i * v * -1000./param['active_area'] #cell voltage is positive, current is negative.
                    
                #append data and plot
                dataW.append(w)
                dataX.append(timeNow - startTime)
                dataI.append(i)
                dataJ.append(i*1000./param['active_area'])
                dataV.append(v)
                
                if self.win != None:
                    self.win.updatePlotMPP(dataX, dataW)
                    self.win.updatePlotMPPIV(dataX, dataV, dataJ)
                    
                #increment the next measurement time
                measTime = measTime + param['interval']
                
                #MPP Algorithm (perturb-and-observe)
                #a simple MPP algoithm that constantly moves the voltage by a certain step size
                #and observes if the power increases or decreases.  Here we use
                #adaptive voltage stepping based on the trend of the last 8 steps.
                #the sum of the trend can be either +/-8, +/-6, +/-4, +/-2, or 0.
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
                if len(steps) >= 8:
                    trend = sum(steps[len(steps)-8:])
                    #increase the step size if there is a noticeable trend to get there faster.
                    if abs(trend) >= 3:
                        v_step *= 2
                        steps = [] #reset steps history when changing scale
                        if v_step > v_step_max:
                            v_step = v_step_max
                    #if there is no trend and we are not yet at the minimum, decrease the step size.
                    elif abs(trend) == 0 and v_step > v_step_min:
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
                if self.useReferenceDiode and self.referenceDiodeParallel:
                    (i, v, i_ref, v_ref) = self.measure_current_and_voltage("CHAN_BOTH")
                else:
                    i = self.measure_current("CHAN_A") #to keep the keithley display current...
            
            if self.abortRunFlag():
                break

            now = datetime.datetime.now()
            timeNow = datetime.datetime.timestamp(now)
            
        self.turn_off()

        return (dataX, dataV, dataI, dataIref)
    
    def measure_reference_calibration(self, param):
        # self.flag_abortRun = False
        if self.app != None:
            self.app.processEvents()
            
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
                    
                    if self.abortRunFlag():
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
                    
                    if self.abortRunFlag():
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
            
            if self.abortRunFlag():
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
            
            if self.abortRunFlag():
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
            
            if self.abortRunFlag():
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
                    
    
class lamp:
    def __init__(self, hardware,  **kwargs):  
        for key, value in kwargs.items():
            if key == 'app':
                self.app = value
            if key == 'gui':
                self.win = value
            if key == 'smu':
                self.smu = value
                
        self.brand = hardware['brand']
        self.model = hardware['model']
        self.emulate = hardware['emulate']
        #dictionary of recipies must be loaded if using wavelabs.  Currently set at top level.
        self.recipeDict = {} #hardware['recipeDict'] 
        self.light_int = 100
        self.connection_open = False
        self.connected = False
        #if (self.brand == 'Wavelabs') and (self.model == 'Sinus70'):
            #if not self.emulate:
            
        if self.brand == 'Oriel' and self.model == 'LSS-7120':
            #import pyvisa
            self.visa_address = hardware['visa_address']
            #self.visa_library = hardware['visa_library']
               
    def show_status(self,msg):
        if self.app != None:
            self.win.showStatus(msg)
            self.app.processEvents()
        else:
            print(msg)
    
    def abortRunFlag(self):
        if self.win != None:
            return self.win.flag_abortRun
        else:
            return False
    
    def connect(self):
        if self.connected:
            self.disconnect()
        
        if not self.emulate:
            if self.brand == 'keithley' and self.model == 'filter wheel':
                self.light_off()
                #pass #lamp filter wheel is controlled by SMU.  no ititialization to do here.
            
            if self.brand == 'Oriel' and self.model == 'LSS-7120':
                import pyvisa
                self.rm = pyvisa.ResourceManager() #visa_library = "C:\\Windows\\SysWOW64\\visa32.dll")
                # print(rm.list_resources())
                self.lss = self.rm.open_resource(self.visa_address)
                
                self.lss.read_termination = '\n\003'
                self.lss.write_termination = '\n'
                self.lss.send_end = True
                self.lss.query_delay = 0.05
                self.lss.timeout = 1000 
                
                #verify identifier to be sure we have a good connection
                lss_idn = self.lss.query("*IDN?")
                #expect response to be “Newport Corporation,LSS-7120,[sn#],[rev#]”
                if lss_idn[0:27] != "Newport Corporation,LSS-7120":
                    raise ValueError("Oriel lamp IDN incorrect: " + lss_idn)
            
            if self.brand == 'Trinamic' and self.model == 'TMCM-3110':
                from PyTrinamic.connections.ConnectionManager import ConnectionManager
                from PyTrinamic.modules.TMCM3110.TMCM_3110 import TMCM_3110
                
                connectionManager = ConnectionManager()
                myInterface = connectionManager.connect()
                self.motor = TMCM_3110(myInterface)
                
                self.motor.setMaxAcceleration(0,1000)
                self.motor.setMaxVelocity(0,1000)
                self.motor.setMaxCurrent(0,50)
                self.microstepResolution = 8
                self.stepsPerRevolution = 200
                self.motor.setAxisParameter(self.motor.APs.MicrostepResolution,0,self.microstepResolution)
            
            if self.brand == 'Trinamic' and self.model == 'TMCM-1260':
                from PyTrinamic.connections.ConnectionManager import ConnectionManager
                from PyTrinamic.modules.TMCM1260.TMCM_1260 import TMCM_1260

                connectionManager = ConnectionManager()
                self.myInterface = connectionManager.connect()
                self.motor = TMCM_1260(self.myInterface)
                
                self.motor.setMaxAcceleration(40000)
                self.motor.setMaxVelocity(20000)
                self.motor.setMaxCurrent(50)
                self.microstepResolution = 8
                self.stepsPerRevolution = 200
                self.motor.setAxisParameter(self.motor.APs.MicrostepResolution,self.microstepResolution)
                
            if self.brand == 'Manual':
                pass
        
        self.connected = True
    
    def disconnect(self):
        self.connected = False
        
        if not self.emulate:
            if self.brand == 'keithley' and self.model == 'filter wheel':
                pass
            
            if self.brand == 'Oriel' and self.model == 'LSS-7120':
                self.lss.close()
                
            if self.brand == 'Trinamic' and self.model == 'TMCM-3110':
                self.myInterface.close()
                
            if self.brand == 'Trinamic' and self.model == 'TMCM-1260':
                self.myInterface.close()
                
    #helper function for use with trinamic motors
    def convert_angle_to_microsteps(self,angle):
        microstepsPerFullStep = 2**self.microstepResolution
        targetPosition = int(angle*(self.stepsPerRevolution/360)*microstepsPerFullStep)
        return targetPosition
    
    def wavelabs_connect(self):
        # Create a TCP/IP socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        # Bind the socket to the port
        self.server_address = ('127.0.0.1', 55555)
        print ('starting up on %s port %s' % self.server_address)
        self.sock.bind(self.server_address)
        
        self.sock.settimeout(5)
        
        # Listen for incoming connections
        self.sock.listen(1)
        
        # Wait for a connection
        print ('waiting for a connection')
        
        self.connection, self.client_address = self.sock.accept()
        
        print ("Got Connection from ")
        print(self.client_address)
        
        #set read-timeout for connection queries
        self.connection.settimeout(1)
        
        self.connection_open = True
        self.seqNum = 0
    
    def wavelabs_disconnect(self):
        print ('closing socket')
        self.connection.close()
        self.sock.close()
        self.connection_open = False
    
    def wavelabs_extract_error_string(self, replyString):
        errIndex = replyString.find("iEC='0'")
        if errIndex != -1:
            return (False,"No Error")
            
        startIndex = replyString.find('sError=')
        endIndex = replyString.find('\>')
        if startIndex == -1 or endIndex == -1:
            return (True, "Did not receive proper reply from Wavelabs")
        else:    
            return (True, replyString[startIndex+8:endIndex-1])
    
    def light_on(self,light_int = 100):
        #light_int: float, units: mW/cm2, pre-defined = 100 mW/cm2, i.e. 1 sun
        self.light_is_on = False
        
        if self.brand == 'Manual':
            pass
        
        if self.brand == 'keithley' and self.model == 'filter wheel':
            angle_code = self.filterWheelDict[light_int]
            self.smu.set_TTL_level(angle_code)
            time.sleep(12.0) #wait 8 seconds for filter wheel to reach position
        
        if self.brand == 'Trinamic' and self.model == 'TMCM-3110':
            if not self.emulate:
                angle = self.filterWheelDict[light_int]
                self.motor.moveTo(0,self.convert_angle_to_microsteps(angle))

                while not(self.motor.positionReached(0)):
                    if self.abortRunFlag():
                        break

                
        if self.brand == 'Trinamic' and self.model == 'TMCM-1260':
            if not self.emulate:
                angle = self.filterWheelDict[light_int]
                self.motor.moveTo(self.convert_angle_to_microsteps(angle))

                while not(self.motor.positionReached()):
                    if self.abortRunFlag():
                        break

        
        if self.brand == 'Oriel' and self.model == 'LSS-7120':
            if not self.emulate:
                self.lss.write("AMPL " + str(light_int/100))
                
                #query the setpoint to verify that it was properly set
                light_setp_string = self.lss.query("AMPL?")
                light_setp = float(light_setp_string)
                #set value might not precisely match, but should be within +/-0.5%
                if abs(light_setp - light_int) > 0.5:
                    raise ValueError("ERROR: Oriel Light intensity not properly set")
                
                #enable the output
                self.lss.write("OUTP ON")
                
                #query the output state to verify that the lamp was truly turned on-the-fly
                lamp_outp_string = self.lss.query("OUTP?")
                if lamp_outp_string != 'ON':
                    raise ValueError("ERROR: Oriel lamp did not turn on when requested")
                
        
        if (self.brand == 'Wavelabs') and (self.model == 'Sinus70'):
            if not self.emulate:
                light_int_defined = False
                if light_int in self.recipeDict:
                    recipeName = self.recipeDict[light_int]
                    light_int_defined = True                    
                    
                if not light_int_defined:
                    
                    raise ValueError(f'Light intensity "{light_int} mW/cm2" is not defined.')
                
                elif light_int == 0:
                    
                    pass #do nothing - light is not turned on
                    
                else:
                    #connect to the lamp
                    self.wavelabs_connect()
                    
                    # Send data
                    message = "<WLRC><ActivateRecipe iSeq='" + str(self.seqNum) + "' sRecipe='" + recipeName + "'/></WLRC>"
                    #message = "<WLRC><StartRecipe iSeq='" + str(seqNum) + "'/></WLRC>"
                    #print (message)
                    self.connection.sendall(bytes(message, 'utf-8'))
                    self.seqNum+= 1
                    
                    # Look for the response
                    amount_received = 0
                    
                    replyString = ""
                    while True : #amount_received < amount_expected:
                        try:
                            data = self.connection.recv(16)
                            replyString += str(data, 'utf-8')
                            if len(data) < 16 : 
                                break
                            amount_received += len(data)
                            #print ("received " + str(data) )
                        except:
                            break
                    #print(replyString)
                    (err, errString) = self.wavelabs_extract_error_string(replyString)
                    if err:
                        self.wavelabs_disconnect()
                        raise ValueError("Error from Wavelabs Activate Recipe:\n" + errString)
                    
                    message = "<WLRC><StartRecipe iSeq='" + str(self.seqNum) + "'/></WLRC>"
                    #print (message)
                    self.connection.sendall(bytes(message, 'utf-8'))
                    self.seqNum+= 1
                    
                    # Look for the response
                    amount_received = 0
                    
                    replyString = ""
                    while True : #amount_received < amount_expected:
                        try:
                            data = self.connection.recv(16)
                            replyString += str(data, 'utf-8')
                            if len(data) < 16 : 
                                break
                            amount_received += len(data)
                            #print ("received " + str(data) )
                        except:
                            break
                    #print(replyString)
                    
                    self.wavelabs_disconnect()
                    
                    (err, errString) = self.wavelabs_extract_error_string(replyString)
                    if err:
                        raise ValueError("Error from Wavelabs Start Recipe:\n" + errString)
        
        #if we get here without error then the light was properly turned on
        self.light_is_on = True

    
    def light_off(self):
        if self.brand == 'Manual':
            pass
        
        if self.brand == 'keithley' and self.model == 'filter wheel':
            angle_code = self.filterWheelDict[0]
            self.smu.set_TTL_level(angle_code)
            time.sleep(8.0) #wait 8 seconds for filter wheel to reach position
        
        if self.brand == 'Trinamic' and self.model == 'TMCM-3110':
            angle = self.filterWheelDict[0]
            if not self.emulate and self.light_is_on:
                self.motor.moveTo(0,self.convert_angle_to_microsteps(angle))

                while not(self.motor.positionReached(0)):
                    if self.abortRunFlag():
                        break

                
        if self.brand == 'Trinamic' and self.model == 'TMCM-1260':
            angle = self.filterWheelDict[0]
            if not self.emulate and self.light_is_on:
                self.motor.moveTo(self.convert_angle_to_microsteps(angle))

                while not(self.motor.positionReached()):
                    if self.abortRunFlag():
                        break

        
        if self.brand == 'Oriel' and self.model == 'LSS-7120':
            if not self.emulate and self.light_is_on:
                #disable the output
                self.lss.write("OUTP OFF")
                
                #query the output state to verify that the lamp was truly turned on-the-fly
                lamp_outp_string = self.lss.query("OUTP?")
                if lamp_outp_string != 'OFF':
                    raise ValueError("ERROR: Oriel lamp did not turn off when requested")
        
        if (self.brand == 'Wavelabs') and (self.model == 'Sinus70'):

            if not self.emulate and self.light_is_on:
                self.wavelabs_connect()
                
                message = "<WLRC><CancelRecipe iSeq='" + str(self.seqNum) + "'/></WLRC>"
                #print (message)
                self.connection.sendall(bytes(message, 'utf-8'))
                self.seqNum+= 1
                
                # Look for the response
                amount_received = 0
                
                replyString = ""
                while True : #amount_received < amount_expected:
                    try:
                        data = self.connection.recv(16)
                        replyString += str(data, 'utf-8')
                        if len(data) < 16 : 
                            break
                        amount_received += len(data)
                        #print ("received " + str(data) )
                    except:
                        break
                
                #print(replyString)
                self.wavelabs_disconnect()
                
                #do this last of all because ValueError will abort execution of anything after it in the function.
                (err, errString) = self.wavelabs_extract_error_string(replyString)
                if err:
                    raise ValueError("Error from Wavelabs Cancel Recipe:\n" + errString)
                
        self.light_is_on = False
                    
                
    def turn_off(self):
        if self.brand == 'Trinamic' and self.model == 'TMCM-3110':
            if not self.emulate:
                if self.connection_open :
                    self.disconnect()
                
        if self.brand == 'Trinamic' and self.model == 'TMCM-1260':
            if not self.emulate:
                if self.connection_open :
                    self.disconnect()
    
        if self.brand == 'Oriel' and self.model == 'LSS-7120':
            if not self.emulate:
                if self.connection_open :
                    self.disconnect()
                    
        if (self.brand == 'Wavelabs') and (self.model == 'Sinus70'):
            if not self.emulate:
                if self.connection_open :
                    self.wavelabs_disconnect()
                
class system:
    def __init__(self, sp, **kwargs):
        self.sp = sp
        self.app = None
        self.win = None
        for key, value in kwargs.items():
            if key == 'whatever':
                self.whatever = value
            if key == 'app':
                self.app = value
            if key == 'gui':
                self.win = value
                
        #Default Preferences.  Can be overridden by entries in the system parameters file.
        self.saveDataAutomatic = False #automatically save every scan upon completion
        self.checkVOCBeforeScan = True #check Voc polarity before each run and warn user if incorrect
        self.firstPointDwellTime = 5.0 #allow the cell to stabilize at the initial setting for this many seconds before starting a scan
        self.MPPVoltageStepInitial = 0.002 #initial step size for MPP algorithm
        self.MPPVoltageStepMax = 0.002 #maximum step size for MPP algorithm
        self.MPPVoltageStepMin = 0.001 #minimum step size for MPP algorithm
        
        if "saveDataAutomatic" in self.sp.IVsys:
            self.saveDataAutomatic = self.sp.IVsys["saveDataAutomatic"]
        if "checkVOCBeforeScan" in self.sp.IVsys:
            self.checkVOCBeforeScan = self.sp.IVsys["checkVOCBeforeScan"]
        if "firstPointDwellTime" in self.sp.IVsys:
            self.firstPointDwellTime = self.sp.IVsys["firstPointDwellTime"]
        if "MPPVoltageStepInitial" in self.sp.IVsys:
            self.MPPVoltageStepInitial = self.sp.IVsys["MPPVoltageStepInitial"]
        if "MPPVoltageStepMax" in self.sp.IVsys:
            self.MPPVoltageStepMax = self.sp.IVsys["MPPVoltageStepMax"]
        if "MPPVoltageStepMin" in self.sp.IVsys:
            self.MPPVoltageStepMin = self.sp.IVsys["MPPVoltageStepMin"]
        
        #read in user table from scrambled users json file.  read the scrambled string,
        #unscramble the contents and load the table.
        #self.users = {"username":"Sciper", "legeyt":"180578" }
        try:
            users_filename = os.path.join(os.getcwd(), "users.txt")
            f = open(users_filename, "r")
            scrambled_string = f.read()
            f.close()
            json_string = self.unscramble_string(scrambled_string)
            json_data = json.loads(json_string)
            #force all usernames to be lowercase
            self.users = {}
            for key,value in json_data.items():
                self.users[key.lower()] = value
        except:
            self.error_window("ERROR: User table corrupted or absent.  Please contact an administrator.")
            self.users = None
            
        self.username = None
        
        self.data_IV = None
        self.IV_Results = None
        self.data_CC = None
        self.CC_Results = None
        self.data_CV = None
        self.CV_Results = None
        self.data_MPP = None
        self.MPP_Results = None
        
        #instatiate the class instance.  use smu.connect() to initialize the hardware
        self.SMU = SMU(sp.SMU, app=app, gui=win)
        self.SMU.fullSunReferenceCurrent = self.sp.IVsys['fullSunReferenceCurrent']
        self.SMU.calibrationDateTime = self.sp.IVsys['calibrationDateTime']
        self.SMU.referenceDiodeImax = self.sp.IVsys['referenceDiodeImax']
        
        #if the SMU can read both channels in parallel, set referenceDiodeParallel to True
        #However, if the system name is IV_Old we must do it in series because the reference diode is
        #mounted on a stage in that setup and is not in the light at the same time as the sample.
        if (self.sp.SMU['model'] == '2600' or self.sp.SMU['model'] == '2602') and self.sp.IVsys['sysName'] != 'IV_Old':
            self.SMU.referenceDiodeParallel = True
        else:
            self.SMU.referenceDiodeParallel = False
                
        self.lamp = lamp(sp.lamp, app=app, gui=win, smu=self.SMU)
        
        if self.sp.IVsys['sysName'] == 'IV_Old':
            #arduino is not present in all systems.  
            #Check that its parameters have been loaded from the system settings file before trying to access
            if self.sp.arduino != None:
                self.arduino = arduino(sp.arduino, app=app, gui=win)
            else:
                raise ValueError("ERROR: System name is set to 'IV_Old' but no arduino settings dictionary is present")
        
        #self.flag_abortRun = False
        
        
    def hardware_init(self):
        #SMU initialization
        
        try:
            self.SMU.connect()
            SMU_OK = True
        except ValueError as err:
            self.error_window("Error initializing keithley sourcemeter: \n\n" + str(err))
            SMU_OK = False
            return
        except Exception as err:
            print(err)
            self.error_window("Error initializing keithley sourcemeter")
            SMU_OK = False
            return
            #raise ValueError("Error initializing keithley sourcemeter")
        
        #lamp initialization
        try:
            self.lamp.connect()
            LAMP_OK = True
        except ValueError as err:
            self.error_window("Error initializing lamp: \n\n" + str(err))
            LAMP_OK = False
            return
        except Exception as err:
            print(err)
            self.error_window("Error initializing lamp")
            #raise ValueError("Error initializing lamp")
            LAMP_OK = False
            return

        #optional arduino initialization
        if self.sp.IVsys['sysName'] == 'IV_Old':
            try:
                self.arduino.connect()
                ARDUINO_OK = True
            except ValueError as err:
                self.error_window("Error initializing arduino: \n\n" + str(err))
                ARDUINO_OK = False
                return
            except Exception as err:
                print(err)
                self.error_window("Error initializing lamp")
                ARDUINO_OK = False
                return

        #if we got here then all of the above initializations were successful.
        if self.win != None:
            self.win.setHardwareActive(True)
    
    def user_login(self, username, pwd):
        #verify if username and password match
        if username.lower() in self.users:
            if self.users[username.lower()] == pwd:
                
                if self.win != None:
                    # tell the gui it has a valid user
                    self.win.logInValid(username)
                    
                self.username = username.lower()
                
                if self.win != None:
                    self.win.showStatus("User set to: " + self.username)
                    #only allow calibration measurement for certain users.
                    if self.username == 'felix' or self.username == 'legeyt':
                        self.win.enableCalibration()
                    else:
                        self.win.disableCalibration()
                    # user-specific configuration files should be located here:
                    configFilePath = os.path.join(self.sp.computer['basePath'] , self.username , 'IVLab_config.json')
                    # tell the gui to load the configuration file
                    self.win.loadSettingsFile(configFilePath)
            else:
                self.error_window("Sciper not valid for user " + username)
        else:
            self.error_window("Username not valid")
            
    
    def user_logout(self):
        
        if self.win != None:
            # user-specific configuration files should be located here:
            configFilePath = os.path.join(self.sp.computer['basePath'] , self.username , 'IVLab_config.json')
            # tell the gui to save the current settings to the user's configuration file
            self.win.saveSettingsFile(configFilePath)
            # clear the previous values from the gui
            self.win.setAllFieldsToDefault()
            
            #clear out scan data and results
            self.data_IV = None
            self.IV_Results = None
            self.data_CC = None
            self.CC_Results = None
            self.data_CV = None
            self.CV_Results = None
            self.data_MPP = None
            self.MPP_Results = None
            
            self.win.showStatus("Please Log In")

        self.username = None
        #disconnect the hardware
        try:
            self.SMU.disconnect()
            self.lamp.disconnect()
        except:
            #nothing to do here
            pass


    def turn_lamp_on(self,light_int):
            lampError = True
            try:
                #turn the lamp on, or set the filter wheel to the right position
                self.lamp.light_on(light_int)
                
                #for system IV_Old, have to open the shutter as well when light level not zero
                if self.sp.IVsys['sysName'] == 'IV_Old' and light_int > 0.:
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
            if self.sp.IVsys['sysName'] == 'IV_Old':
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
        if self.sp.IVsys['sysName'] == 'IV_Old':
            self.show_status("Moving Reference Diode Into Measurement Position...")
            self.arduino.select_reference_cell()
        
        self.show_status("Measuring Light Intensity on Reference Diode...")
        
        lightIntensity = self.SMU.measureLightIntensity(5.0)
        
        #move back to the test cell if using IV_Old
        if self.sp.IVsys['sysName'] == 'IV_Old':
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
        
        #check that the SMU can handle the requested measurement interval
        interval = abs(IV_param['dV'])/IV_param['sweep_rate']
        if interval < self.SMU.meas_period_min:
            IV_param['dV'] = self.SMU.meas_period_min * IV_param['sweep_rate']
            errorMsg = "WARNING: the SMU is unable to provide the requested measurement rate.\n"
            errorMsg += "The voltage step size has been adjusted to assure the requested sweep rate is respected."
            self.error_window(errorMsg)
            if self.win != None:
                win.fieldIVVStep.setText("{:5.2f}".format(IV_param['dV']*1000.))
            
        #turn the lamp on
        self.show_status("Turning lamp on...")
            
        lampError = self.turn_lamp_on(IV_param['light_int']) #True
        
        if not lampError:
            try:
                while(True): #use while loop to be able to break out at any time if run aborted.
                    #measure light intensity on the reference diode if configured
                    if self.SMU.useReferenceDiode:
                        
                        lightIntensity = self.measure_light_intensity() #status messages set internally
                        
                        if self.abortRunFlag() :
                            self.show_status("Run Aborted")
                            break
                        if (IV_param['light_int'] > 1.0) and abs((lightIntensity - IV_param['light_int'])/IV_param['light_int']) > 0.1 :
                            self.error_window("WARNING: Light level measured by reference diode is more than 10% off from requested level")
                            
                    VocPolarityOK = True
                    if self.checkVOCBeforeScan and IV_param['light_int']  > 0: #check Voc polarity only when light is on
                        self.show_status("Checking Voc Polarity...")
                        VocPolarityOK = self.SMU.checkVOCPolarity(IV_param)
                        
                    if self.abortRunFlag():
                        self.SMU.turn_off()
                        self.show_status("Run Aborted")
                        break
                    if not VocPolarityOK:
                        self.SMU.turn_off()
                        self.show_status("ERROR: Wrong Voc Polarity...")
                        self.error_window("Error: Incorrect polarity detected for Voc.  This could be due to wires plugged incorrectly or light source not turning on.  Aborting Scan")
                        self.show_status("Run Aborted (Wrong Voc Polarity)")
                        break
                        
                    self.show_status("Running J-V Scan...")
                    
                    (v_smu, i_smu, i_ref) = self.SMU.measure_IV_point_by_point(IV_param) #measure_IVcurve(IV_param)
                    
                    if self.SMU.useReferenceDiode:
                        if self.SMU.referenceDiodeParallel: #light level was measured real-time during scan
                            avgRefCurrent = sum(i_ref)/len(i_ref)
                            avgLightLevel = abs(100. * avgRefCurrent / self.SMU.fullSunReferenceCurrent)
                            if self.app != None:
                                self.win.updateMeasuredLightIntensity(avgLightLevel)
                                self.app.processEvents()
                            
                        else: #light level was only measured once at the beginning
                            avgLightLevel = lightIntensity
                            
                    else:
                        avgLightLevel = IV_param['light_int']
                    
                    if len(v_smu) > 1:
                        self.IV_Results = {}
                        self.IV_Results['active_area'] = IV_param['active_area']
                        self.IV_Results['cell_name'] = IV_param['cell_name']
                        self.IV_Results['light_int'] = IV_param['light_int']
                        if self.SMU.useReferenceDiode:
                            self.IV_Results['light_int_meas'] = avgLightLevel
                        self.IV_Results['Imax'] = IV_param['Imax']
                        self.IV_Results['Dwell'] = IV_param['Dwell']
                        
                        if IV_param['light_int'] > 0 and not self.abortRunFlag(): #don't analyze dark or aborted runs
                            pairs = []
                            dataJ = []
                            for v, i in zip(v_smu, i_smu):
                                pairs.append((v, i / IV_param['active_area']))
                                dataJ.append(i * 1000. / IV_param['active_area'])
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

                            jv_metrics = bric_jv.get_metrics(df, generator=False, fit_window=4)
                            
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
                    
            except ValueError as err:
                self.error_window(str(err))
            except Exception as err:
                print(err)
                self.error_window("Execution Error in system.measure_IVcurve().\nSee terminal for details.")
                
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
        
        #check that the SMU can handle the requested measurement interval
        if param['interval'] < self.SMU.meas_period_min:
            param['interval'] = self.SMU.meas_period_min
            errorMsg = "WARNING: the SMU is unable to provide the requested measurement rate.\n"
            errorMsg += "The measurement interval has been set to the maximum allowed by the SMU."
            self.error_window(errorMsg)
            if self.win != None:
                win.fieldConstantIInterval.setText("{:5.2f}".format(param['interval']))
                
        #param: light int, set current, time, interval
        self.show_status("Turning lamp on...")
            
        #self.lamp.light_on(param['light_int'])
        lampError = self.turn_lamp_on(param['light_int']) #True
        runError = False

        if not lampError:
            try:
                while(True):
                    if self.SMU.useReferenceDiode:
                        lightIntensity = self.measure_light_intensity() #status messages set internally
                        
                        if self.abortRunFlag() :
                            break
                                
                        elif (param['light_int'] > 1.0) and abs((lightIntensity - param['light_int'])/param['light_int']) > 0.1 :
                            self.error_window("WARNING: Light level measured by reference diode is more than 10% off from requested level")
                                
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
        
        #check that the SMU can handle the requested measurement interval
        if param['interval'] < self.SMU.meas_period_min:
            param['interval'] = self.SMU.meas_period_min
            errorMsg = "WARNING: the SMU is unable to provide the requested measurement rate.\n"
            errorMsg += "The measurement interval has been set to the maximum allowed by the SMU."
            self.error_window(errorMsg)
            if self.win != None:
                win.fieldConstantVInterval.setText("{:5.2f}".format(param['interval']))
                
        #param: light int, set voltage, time, interval
        self.show_status("Turning lamp on...")
        lampError = self.turn_lamp_on(param['light_int']) #True
        runError = False

        if not lampError:
            try:
                while(True):
                    if self.SMU.useReferenceDiode :
                        lightIntensity = self.measure_light_intensity() #status messages set internally
                        
                        param['light_int_meas'] = lightIntensity
                        
                        if self.abortRunFlag() :
                            #break out directly if run aborted during setup - don't even start the measurement
                            break
                            
                        elif (param['light_int'] > 1.0) and abs((lightIntensity - param['light_int'])/param['light_int']) > 0.1 :
                            self.error_window("WARNING: Light level measured by reference diode is more than 10% off from requested level")
                                
                    self.show_status("Running Constant Voltage Measurement...")
                    
                    t, i_smu, i_ref = self.SMU.measure_I_time_dependent(param)
                    
                    v_smu = []
                    for i in i_smu:
                        v_smu.append(param['set_voltage'])
                    
                    if self.SMU.useReferenceDiode:
                        if self.SMU.referenceDiodeParallel: #light level was measured real-time during scan
                            avgRefCurrent = sum(i_ref)/len(i_ref)
                            avgLightLevel = abs(100. * avgRefCurrent / self.SMU.fullSunReferenceCurrent)
                            if self.app != None:
                                self.win.updateMeasuredLightIntensity(avgLightLevel)
                                self.app.processEvents()
                            
                        else: #light level was only measured once at the beginning
                            avgLightLevel = lightIntensity
                            
                    else:
                        avgLightLevel = IV_param['light_int']
                    
                    self.CV_Results = {}
                    self.CV_Results['active_area'] = param['active_area']
                    self.CV_Results['cell_name'] = param['cell_name']
                    self.CV_Results['light_int'] = param['light_int']
                    if self.SMU.useReferenceDiode:
                        self.CV_Results['light_int_meas'] = avgLightLevel
                    self.CV_Results['set_voltage'] = param['set_voltage']
                    self.CV_Results['interval'] = param['interval']
                    self.CV_Results['duration'] = param['duration']

                    self.data_CV = {}
                    self.data_CV['scanType'] = 'CV'
                    self.data_CV['start_time'] = dateTimeString
                    self.data_CV['t'] = t
                    self.data_CV['v'] = v_smu
                    self.data_CV['i_ref'] = i_ref
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
        
        #check that the SMU can handle the requested measurement interval
        if param['interval'] < self.SMU.meas_period_min:
            param['interval'] = self.SMU.meas_period_min
            errorMsg = "WARNING: the SMU is unable to provide the requested measurement rate.\n"
            errorMsg += "The measurement interval has been set to the maximum allowed by the SMU."
            self.error_window(errorMsg)
            if self.win != None:
                win.fieldMaxPPInterval.setText("{:5.2f}".format(param['interval']))
                
        param['voltage_step'] = self.MPPVoltageStepInitial
        param['voltage_step_max'] = self.MPPVoltageStepMax
        param['voltage_step_min'] = self.MPPVoltageStepMin
        
        #param: light int, start voltage, time, interval
        self.show_status("Turning lamp on...")
        lampError = self.turn_lamp_on(param['light_int']) #True
        runError = False

        if not lampError:
            try:
                while(True):
            
                    if self.SMU.useReferenceDiode :
                        lightIntensity = self.measure_light_intensity() #status messages set internally
                        
                        param['light_int_meas'] = lightIntensity
                        if self.abortRunFlag() :
                            #break out directly if run aborted during setup - don't even start the measurement
                            break
                            
                        elif (param['light_int'] > 1.0) and abs((lightIntensity - param['light_int'])/param['light_int']) > 0.1 :
                            self.error_window("WARNING: Light level measured by reference diode is more than 10% off from requested level")
                            
                    #check Voc polarity.  If it is ok and the run has not been aborted during the Voc check, run MPP
                    VocPolarityOK = True #variable must be defined in case Voc Polarity is not checked
                    if self.checkVOCBeforeScan and param['light_int']  > 0: #check Voc polarity when light greater than zero
                        self.show_status("Checking Voc Polarity...")
                        
                        VocPolarityOK = self.SMU.checkVOCPolarity(param)
                        
                        if self.abortRunFlag() :
                            #break out directly if run aborted during Voc check
                            self.SMU.turn_off()
                            break
                            
                        if not VocPolarityOK :
                            self.SMU.turn_off()
                            self.show_status("ERROR: Wrong Voc Polarity.")
                            self.error_window("Error: Incorrect polarity detected for Voc.  This could be due to wires plugged incorrectly.  Aborting Scan")
                            self.show_status("Run Aborted")
                            break
                        
                    #if we get this far then the setup was all ok and we can start the measurement
                    self.show_status("Running MPP Measurement...")
                    
                    t, v_smu, i_smu, i_ref = self.SMU.measure_MPP_time_dependent(param)
                    
                    if self.SMU.useReferenceDiode:
                        if self.SMU.referenceDiodeParallel: #light level was measured real-time during scan
                            avgRefCurrent = sum(i_ref)/len(i_ref)
                            avgLightLevel = abs(100. * avgRefCurrent / self.SMU.fullSunReferenceCurrent)
                            if self.app != None:
                                self.win.updateMeasuredLightIntensity(avgLightLevel)
                                self.app.processEvents()
                            
                        else: #light level was only measured once at the beginning
                            avgLightLevel = lightIntensity
                            
                    else:
                        avgLightLevel = IV_param['light_int']
                    
                    self.MPP_Results = {}
                    self.MPP_Results['active_area'] = param['active_area']
                    self.MPP_Results['cell_name'] = param['cell_name']
                    self.MPP_Results['light_int'] = param['light_int']
                    if self.SMU.useReferenceDiode:
                        self.MPP_Results['light_int_meas'] = avgLightLevel
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
                    self.data_MPP['i_ref'] = i_ref
                    
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
        try:
            self.show_status("Turning lamp on...")
            
            lampError = self.turn_lamp_on(param['light_int'])
            param['light_int_meas'] = 100.
            
            #if using system 'IV_Old', the reference diode has to be moved into the light beam first
            #to accomplish this we will do two separate CV runs and then load the data into the calibration plot
            if self.sp.IVsys['sysName'] == 'IV_Old':
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
            
            if self.abortRunFlag():
                self.show_status("Calibration Aborted")
            else:
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
            
                self.show_status("Calibration finished")
        
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
        dataFilePath = os.path.join(self.sp.computer['basePath'] , uname , 'data' , filename)
        pdfFilePath = os.path.join(self.sp.computer['basePath'] , uname , 'data' , pdfFileName)
        scrambled_filename = self.scramble_string(uname + "_" + os.path.splitext(filename)[0])
        sdFilePath = os.path.join(self.sp.computer['sdPath'] , scrambled_filename)
        
        basePath, filename = os.path.split(dataFilePath)
        if (not os.path.exists(basePath)):
            os.makedirs(basePath)
            
        f = open(dataFilePath, "w")
        fileString = ""
        
        # prepare header content
        headerLines = []
        headerLines.append("Measurement System," + self.sp.IVsys['sysName'])
        headerLines.append("Scan Start Time," + data['start_time'])
        headerLines.append("Sourcemeter Brand," + self.sp.SMU['brand'])
        headerLines.append("Sourcemeter Model," + self.sp.SMU['model'])
        headerLines.append("Lamp Brand," + self.sp.lamp['brand'])
        headerLines.append("Lamp Model," + self.sp.lamp['model'])
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
                headerLines.append("Voltage(V),Current(A),light intensity (mW/cm^2)")
            else:
                headerLines.append("Voltage(V),Current(A)")
        elif data['scanType'] == 'CV':
            headerLines.append("Set Voltage," + str(IV_Results['set_voltage']) + ",V")
            headerLines.append("Measurement Interval," + str(IV_Results['interval']) + ",sec")
            headerLines.append("Measurement Duration," + str(IV_Results['duration'] ) + ",sec")
            headerLines.append("Constant Voltage Results")
            if self.SMU.useReferenceDiode:
                headerLines.append("Time(s),Voltage(V),Current(A),light intensity (mW/cm^2)")
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
                headerLines.append("Time(s),Voltage(V),Current (A),Power(mW/cm2),light intensity (mW/cm^2)")
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
            for v,i,i_ref in zip(data['v'], data['i'], data['i_ref']):
                fileLine = str(round(v,12)) + "," + str(round(i,12))
                if self.SMU.useReferenceDiode:
                    light_intensity = -100.0 * i_ref / self.SMU.fullSunReferenceCurrent
                    fileLine += "," + str(round(light_intensity,12))
                fileLine += "\n"
                f.write(fileLine)
                fileString += fileLine
        elif data['scanType'] == 'CV':
            for t,v,i_ref,i in zip(data['t'], data['v'], data['i_ref'], data['i']):
                fileLine = str(round(t,6)) + "," + str(round(v,12)) + "," + str(round(i,12))
                if self.SMU.useReferenceDiode:
                    light_intensity = -100.0 * i_ref / self.SMU.fullSunReferenceCurrent
                    fileLine += "," + str(round(light_intensity,12))
                fileLine += "\n"
                f.write(fileLine)
                fileString += fileLine
        elif data['scanType'] == 'CC':
            for t,v,i in zip(data['t'], data['v'], data['i']):
                fileLine = str(round(t,6)) + "," + str(round(v,12)) + "," + str(round(i,12)) + "\n"
                f.write(fileLine)
                fileString += fileLine
        elif data['scanType'] == 'MPP':
            for t,v,i_ref,i in zip(data['t'], data['v'], data['i_ref'], data['i']):
                w = abs(i*v*1000./IV_Results['active_area'])
                fileLine = str(round(t,6)) + "," + str(round(v,12)) + "," + str(round(i,12)) + "," + str(round(w,12))
                if self.SMU.useReferenceDiode:
                    light_intensity = -100.0 * i_ref / self.SMU.fullSunReferenceCurrent
                    fileLine += "," + str(round(light_intensity,12))
                fileLine += "\n"
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
        logoPath = os.path.join(os.getcwd(),"EPFL_Logo.png")
        logo = plt.imread(logoPath)

        dataJ = []
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
        params_text.append(("Light Source",self.sp.lamp['brand'] + " ",self.sp.lamp['model']))
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
        plt.figtext(0.05,0.05,"Measured by: " + uname + " on " + self.sp.IVsys['sysName'], fontsize = 10, ha = 'left')
        plt.figtext(0.75,0.05,"Date: " + dateTimeString, fontsize = 10, ha = 'left')
            
        plt.savefig(pdfFilePath)
    
    def save_calibration_to_system_settings(self, calibration_params):
        dateTimeString = datetime.datetime.now().strftime("%c") #"%Y%m%d_%H%M%S")
        self.sp.IVsys['fullSunReferenceCurrent'] = calibration_params['reference_current']
        self.SMU.fullSunReferenceCurrent = calibration_params['reference_current']
        self.sp.IVsys['calibrationDateTime'] = dateTimeString
        self.SMU.calibrationDateTime = dateTimeString
        settingsFilePath = os.path.join(os.getcwd() , "system_settings.json")
        sys_params = {}
        sys_params['computer'] = self.sp.computer
        sys_params['IVsys'] = self.sp.IVsys
        sys_params['lamp'] = self.sp.lamp
        sys_params['SMU'] = self.sp.SMU
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
            
if __name__ == "__main__":
    
    #check command-line arguments for --nogui option
    if len(sys.argv) > 1 and sys.argv[1] == '--nogui':
        app = None
        win = None        
    else:
        #Must instantiate the application first before the rest...
        app = QApplication(sys.argv)
        
        #declare gui window object
        win = Window()
    
    #No system
    sp_no_system = dict()
    
    #System parameters of the Wavelabs1 system are loaded from a json file.  They take the form of a dictionary like this:
    """
    sp_wavelabs1 = dict(computer = dict(hardware = "PC", os = "Windows 10", basePath = "C:\\Users\\Public\\Documents\\IVLab", sdPath = "C:\\Users\\Public\\Documents\\IVLab\\sd"),
                    IVsys = dict(sysName = "IV_Old", fullSunReferenceCurrent = 0.000145, calibrationDateTime = "Wed Feb 16 16:55:17 2022"),
                    lamp = dict(brand = "Trinamic", model = "TMCM-3110", visa_address = "ASRL1::INSTR", visa_library = "C:\\Windows\\System32\\visa32.dll"),
                    arduino = dict(brand = "Arduino", model = "Uno", visa_address = "ASRL1::INSTR", visa_library = "C:\\Windows\\System32\\visa32.dll"),
                    SMU = dict(brand = "Keithley", model = "2602", visa_address = "GPIB0::24::INSTR", visa_library = "C:\\Windows\\System32\\visa32.dll"))
    """
    
    systemSettingsFilePath = os.path.join(os.getcwd() , "system_settings.json")
    with open(systemSettingsFilePath) as json_file:
        sp_wavelabs1 = json.load(json_file)
    
    #System initialization
    sp = syst_param(**sp_wavelabs1)
    #sp.emulate_lamp_on()
    sp.emulate_arduino_on()
    #sp.emulate_SMU_on()
    
    s = system(sp, app=app, gui=win)
    
    #system preferences - have been moved into the system parameters file.
    # default values are set in the system and SMU object initialization routines
    """
    s.saveDataAutomatic = False #automatically save every scan upon completion
    s.checkVOCBeforeScan = True #check Voc polarity before each run and warn user if incorrect
    s.firstPointDwellTime = 5.0 #allow the cell to stabilize at the initial setting for this many seconds before starting a scan
    s.MPPVoltageStepInitial = 0.005    #initial step size for MPP algorithm
    s.MPPVoltageStepMax = 0.01 #maximum step size for MPP algorithm
    s.MPPVoltageStepMin = 0.001 #minimum step size for MPP algorithm
    s.SMU.sense_mode = '2wire'
    s.SMU.autorange = True #False
    s.SMU.useReferenceDiode = True
    #if the SMU can read both channels in parallel, set referenceDiodeParallel to True
    #However, if the system name is IV_Old we must do it in parallel because the reference diode is
    #mounted on a stage in that setup and is not in the light at the same time as the sample.
    if (sp_wavelabs1['SMU']['model'] == '2600' or sp_wavelabs1['SMU']['model'] == '2602') and sp_wavelabs1['IVsys']['sysName'] != 'IV_Old':
        s.SMU.referenceDiodeParallel = True
    else:
        s.SMU.referenceDiodeParallel = False
    
    s.SMU.referenceDiodeImax = 0.010
    """
    
    s.lamp.recipeDict = {100 : "1 sun, 1 h", 50 : "0.5 sun, 1 h", 20 : "0.2 sun, 1 h", 10 : "0.1 sun, 1 h",  0 : "dummy"}
    #filter wheel dictionary key is light level, value is filter wheel angle
    #s.lamp.filterWheelDict = {100 : 60, 50 : 120, 20 : 180, 10 : 240,  0 : 300} 
    #for main IV setup, filter wheel dictionary key is light level, value is filter digital code
    s.lamp.filterWheelDict = {100 : 0, 50 : 5, 20 : 4, 10 : 3,  0 : 2} 
    #the 'lightIntensities' dictionary is loaded into the gui and controls which light levels can be selected in the drop-down menu.
    #care must be taken that there is a valid recipe defined in s.lamp.recipeDict for each of the light levels in this list.
    lightIntensities = {'1 Sun' : 100, '0.5 Sun' : 50, '0.2 Sun' : 20, '0.1 Sun' : 10, 'Dark' : 0}
    
    if win != None:
        if s.lamp.brand.lower() == 'manual':
            win.setLightLevelModeManual()
        else:
            win.setLightLevelModeMenu()
            win.setLightLevelList(lightIntensities)
        
        #Connect Gui callback signals to appropriate functions
        win.signal_runIV.connect(s.measure_IVcurve)
        win.signal_runConstantI.connect(s.measure_V_time_dependent)
        win.signal_runConstantV.connect(s.measure_I_time_dependent)
        win.signal_runMaxPP.connect(s.measure_MPP_time_dependent)
        win.signal_runCalibration.connect(s.run_reference_diode_calibration)
        win.signal_abortRun.connect(s.abort_run)
        win.signal_saveScanData.connect(s.saveData)
        win.signal_saveCalibration.connect(s.save_calibration_to_system_settings)
        win.signal_toggleAutoSave.connect(s.toggleAutoSave)
        win.signal_initialize_hardware.connect(s.hardware_init)
        win.signal_log_in.connect(s.user_login)
        win.signal_log_out.connect(s.user_logout)
        
        win.show()
        sys.exit(app.exec())
    
    else:  #command-line operation
        #log in user
        #s.user_login('Username', 'Sciper')
        
        #alternately prompt user for log-in details
        username = input("Username: ")
        sciper = input("Sciper: ")
        s.user_login(username, sciper)
    
        #initialize hardware
        s.hardware_init()
        
        #define common params
        params = {}
        params['light_int'] = lightIntensities['1 Sun']
        params['Dwell'] = 5.0 #sec to wait at start of scan
        params['Imax'] = 0.005 #A
        params['Vmax'] = 2.0 #V
        params['active_area'] = 0.16 #cm^2
        params['cell_name'] = "test cell foo bar"
        
        #define scan-specific params and run the scan (uncomment one group only)
        #"""
        scanType = 'J-V Scan'
        params['limits_mode'] = 'Manual' #'Manual' or 'Automatic'
        params['Fwd_current_limit'] = 0.2 #mA - only used in Automatic limits mode
        params['start_V'] = 0.0 #V - set to 'Voc' to start scan at Voc
        params['stop_V'] = 0.6 #V - set to 'Voc' to stop scan at Voc
        params['dV'] = 0.02 #V
        params['sweep_rate'] = 0.05 #V/sec
        
        s.measure_IVcurve(params)
        #"""
        
        """
        scanType = 'Constant Voltage, Measure J'
        params['set_voltage'] = 0.0
        params['interval'] = 0.25
        params['duration'] = 30.0
        
        s.measure_I_time_dependent(params)
        """
        
        """
        scanType = 'Constant Current, Measure V'
        params['set_current'] = 0.0
        params['interval'] = 0.25
        params['duration'] = 30.0
        
        s.measure_V_time_dependent(params)
        """
        
        """
        scanType = 'Maximum Power Point'
        params['start_voltage'] = 'auto' #does a J-V scan if set to 'auto'.  Can also specify a manual start voltage
        params['interval'] = 0.25
        params['duration'] = 30.0
        
        s.measure_MPP_time_dependent(params)
        """
        
        #scan data and any pre-processed results can be accessed from the following dictionaries:
        #s.data_IV
        #s.data_CV
        #s.data_CC
        #s.data_MPP
        #s.IV_Results
        #s.CV_Results
        #s.CC_Results
        #s.MPP_Results
        
        #save the data
        s.saveData(scanType,params['cell_name']) 
        
        #log out
        s.user_logout()