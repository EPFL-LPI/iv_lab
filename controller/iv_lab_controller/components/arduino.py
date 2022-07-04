import pyvisa

from ..base_classes.hardware_base import HardwareBase

   
class Arduino(HardwareBase):
    def __init__(self, hardware: dict, emulate: bool = False):
        """
        :param hardware: Dictionary of hardware parameters.
        :param emulate: Run in emulation mode. [Default: False]
        """  
        self.brand = hardware['brand']
        self.model = hardware['model']
        self._emulate = emulate

        self.cell_stage_settling_time = 5.0
        
        self.visa_address = hardware['visa_address']
        #self.visa_library = hardware['visa_library']
        
        self._connected = False
           
    @property
    def emulate(self) -> bool:
        """
        :returns: Emulation mode.
        """
        return self._emulate

    @property
    def connected(self) -> bool:
        """
        :returns: If Arduino is connected.
        """
        return self._connected
    
    def connect(self):
        if self.emulate:
            return

        if self.connected:
            return

        self.rm = pyvisa.ResourceManager() # visa_library = "C:\\Windows\\SysWOW64\\visa32.dll"
        # print(rm.list_resources())
        self.ard = self.rm.open_resource(self.visa_address)
        
        self.ard.baud_rate = 115200
        self.ard.read_termination = '\n'
        self.ard.write_termination = '\n'
        self.ard.send_end = True
        self.ard.query_delay = 0.05
        self.ard.timeout = 1000 
        
        # verify identifier to be sure we have a good connection
        ard_idn = self.ard.query("*IDN?")
        
        # expect response to be “Newport Corporation,LSS-7120,[sn#],[rev#]”
        if ard_idn[0:27] != "Newport Corporation,LSS-7120":
            raise ValueError("Oriel lamp IDN incorrect: " + ard_idn)
                
        self._connected = True
    
    def disconnect(self):
        if not self.emulate:
            self.ard.close()

        self._connected = False
                    
    def shutter_open(self):
        self.arduino_digital_command(2, 1)

    def shutter_close(self):
        self.arduino_digital_command(2, 0)
                
    def select_reference_cell(self):
        self.arduino_digital_command(4, 0)
        time.sleep(self.cell_stage_settling_time)
    
    def select_test_cell(self):
        self.arduino_digital_command(4, 1)
        time.sleep(self.cell_stage_settling_time)
    
    def arduino_digital_command(self, pin: int, value):
        if self.emulate:
            return

        self.ard.write("6," + str(int(pin)) + "," + str(int(value)))
