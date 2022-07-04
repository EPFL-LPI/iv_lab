import pyvisa

from ...base_classes.lamp import Lamp


class OrielLSS7120(Lamp):
    """
    An Oriel LSS 7120 lamp.
    """
    def __init__(self, visa_address: str, emulate: bool = False):
        """
        :param visa_address: VISA port to connect with.
        :param emulate: Whether to emulate the lamp or not. [Default: False]
        """
        super().__init__(emulate=emulate)

        self._visa_address = visa_address

    @property
    def visa_address(self) -> str:
        return self._visa_address

    def _connect(self):
        """
        :raises ValueError: If lamp id is invalid.
        """
        self.rm = pyvisa.ResourceManager() #visa_library = "C:\\Windows\\SysWOW64\\visa32.dll")
        # print(rm.list_resources())
        self.lss = self.rm.open_resource(self.visa_address)
        
        self.lss.read_termination = '\n\003'
        self.lss.write_termination = '\n'
        self.lss.send_end = True
        self.lss.query_delay = 0.05
        self.lss.timeout = 1000 
        
        # verify identifier to be sure we have a good connection
        lss_idn = self.lss.query("*IDN?")
        
        # expect response to be “Newport Corporation,LSS-7120,[sn#],[rev#]”
        if lss_idn[0:27] != "Newport Corporation,LSS-7120":
            raise ValueError("Oriel lamp IDN incorrect: " + lss_idn)

    def _light_on(self):
        """
        Turn on the lamp.
        
        :raises RuntimeError: If lamp intensity is not within 0.5% of set point.
        :raises RuntimeError: If lamp could not be turned on.
        """
        self.lss.write(f'AMPL {self.intensity/100}')
        
        # query the setpoint to verify that it was properly set
        light_setp_string = self.lss.query("AMPL?")
        light_setp = float(light_setp_string)
        
        # set value might not precisely match, but should be within +/-0.5%
        if abs(light_setp - self.intensity) > 0.5:
            raise RuntimeError("Light intensity not properly set")
        
        # enable the output
        self.lss.write("OUTP ON")
        
        # query the output state to verify that the lamp was truly turned on-the-fly
        lamp_outp_string = self.lss.query("OUTP?")
        if lamp_outp_string != 'ON':
            raise RuntimeError("Could not turn on lamp")


    def _light_off(self):
        """
        Turn off the lamp.

        :raises RuntimeError: If lamp could not be turned off.
        """
        self.lss.write("OUTP OFF")
        
        # query the output state to verify that the lamp was truly turned on-the-fly
        lamp_outp_string = self.lss.query("OUTP?")
        if lamp_outp_string != 'OFF':
            raise RuntimeError('Could not turn off lamp')


    def _turn_off(self):
        if self.connection_open:
            self.disconnect()