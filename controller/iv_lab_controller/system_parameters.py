

class syst_param:
    """
    Contains all the system parameters, i.e. computer, operating system, lamp, SMU, filters, shutter...
    """
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
                self.lamp['emulate'] = False
            elif key == 'arduino':
                self.arduino = value
                self.arduino['emulate'] = False
            elif key == 'SMU':
                self.SMU = value
                self.SMU['emulate'] = False
                
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