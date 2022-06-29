   
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
