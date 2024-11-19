# -*- coding: utf-8 -*-
"""
Created on Wed Oct 30 10:36:18 2024

@author: dreickem
"""

# Import necessary packages
import logging
log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())

import sys
import tempfile
import random
import time
from time import sleep
import datetime
from pymeasure.log import console_log
from pymeasure.display.Qt import QtWidgets
from pymeasure.display.windows import ManagedWindow
from pymeasure.experiment import Procedure, Results, Worker
from pymeasure.experiment import IntegerParameter, FloatParameter, Parameter
from pymeasure.instruments.keithley import Keithley2400
import numpy as np
from pymeasure.log import log, console_log

com_port = 10
save_dir = r'C:\Users\labo\Documents\Felix\electrical_measurements\data'

class IVProcedure(Procedure):

    scan_rate = FloatParameter('Scan rate', units='A/s', default=-0.1)
    averages = IntegerParameter('Averages', default=8)
    max_current = FloatParameter('Maximum Current', units='A', default=0.0)
    min_current = FloatParameter('Minimum Current', units='A', default=0.0)
    min_voltage = FloatParameter('Minimum Voltage', units='V', default=0.2) 
    current_multiplication_factor = IntegerParameter('Current multiplication factor', default=10000)

    DATA_COLUMNS = ['Time (s)', 'Current (A)', 'Voltage (V)', 'Voltage Std (V)', 'Power (W)']

    def startup(self):
        log.info("Connecting and configuring the instrument")
        self.sourcemeter = Keithley2400('ASRL'+str(com_port))
        self.sourcemeter.reset()
        self.sourcemeter.wires = 4
        self.sourcemeter.use_front_terminals()
        self.sourcemeter.apply_current(current_range=None, compliance_voltage=2.0)
        self.sourcemeter.measure_voltage(nplc=0.01, voltage=2.0, auto_range=True)  # Voltage: upper limit
        sleep(0.1)  # wait here to give the instrument time to react
        self.sourcemeter.stop_buffer()
        self.sourcemeter.disable_buffer()
        #disable beep sound when output enabled
        self.sourcemeter.write(":SYST:BEEP:STAT OFF")

    def execute(self):

        if self.max_current >= self.min_current:
            if self.scan_rate > 0:
                start_current = self.min_current / self.current_multiplication_factor
            else:
                start_current = self.max_current / self.current_multiplication_factor
                
            self.sourcemeter.enable_source()
            
            def current_range_exceeded(current):
                if self.max_current == self.min_current:
                    return False
                if self.scan_rate > 0:
                    return current > self.max_current / self.current_multiplication_factor
                else:
                    return current < self.min_current / self.current_multiplication_factor
    
            # Loop through each current point, measure and record the voltage
    
            current = start_current
            now = datetime.datetime.now()
            startTime = datetime.datetime.timestamp(now) #s
            nowTime = startTime
            #Dummy start value > 0
            voltage = 1.
    
            while (voltage > self.min_voltage) and not(current_range_exceeded(current)):
                            
                self.sourcemeter.config_buffer(IVProcedure.averages.value)
                log.info("Setting the current to %g A" % current)
                self.sourcemeter.source_current = current
                self.sourcemeter.start_buffer()
                log.info("Waiting for the buffer to fill with measurements")
                self.sourcemeter.wait_for_buffer()
                voltage = self.sourcemeter.means[0]
                data = {
                    'Time (s)': nowTime-startTime,
                    'Current (A)': current*self.current_multiplication_factor,
                    'Voltage (V)': voltage,
                    'Voltage Std (V)': self.sourcemeter.standard_devs[0],
                    'Power (W)': current*self.current_multiplication_factor*voltage
                }
                self.emit('results', data)
                
                sleep(0.01)
                now = datetime.datetime.now()
                nowTime = datetime.datetime.timestamp(now) #s
                current = start_current + self.scan_rate * (nowTime-startTime) / self.current_multiplication_factor
                
                if self.should_stop():
                    log.info("User aborted the procedure")
                    break
                
        else:
            log.info("max_current is not equal or larger than min_current, measurement cannot start.")

    def shutdown(self):
        self.sourcemeter.shutdown()
        log.info("Finished measuring")
        
class MainWindow(ManagedWindow):

    def __init__(self):
        super().__init__(
            procedure_class=IVProcedure,
            inputs=['scan_rate', 'averages', 'max_current', 'min_current', 'min_voltage', 'current_multiplication_factor'],
            displays=['scan_rate', 'averages', 'max_current', 'min_current', 'min_voltage', 'current_multiplication_factor'],
            y_axis='Voltage (V)',
            x_axis='Current (A)'
        )
        self.setWindowTitle('GUI Example')
        
        self.filename = 'IV_2paper_50mLmin'   # Sets default filename
        self.directory = save_dir            # Sets default directory
        self.store_measurement = True                               # Controls the 'Save data' toggle
        self.file_input.extensions = ["csv", "txt", "data"]         # Sets recognized extensions, first entry is the default extension
        self.file_input.filename_fixed = False                      # Controls whether the filename-field is frozen (but still displayed)


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
    
    