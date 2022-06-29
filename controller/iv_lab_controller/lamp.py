    
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
            time.sleep(8.0) #wait 8 seconds for filter wheel to reach position
        
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
        