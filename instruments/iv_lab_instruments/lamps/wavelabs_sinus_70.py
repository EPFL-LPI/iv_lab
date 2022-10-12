from .wavelabs_base import WavelabsLamp


class WavelabsSinus70(WavelabsLamp):
    """
    A Wavelabs Sinus 70 lamp.
    """
    def __init__(self, emulate: bool = False):
        """
        :param emulate: Whether to emulate the lamp or not. [Default: False]
        """
        super().__init__(emulate=emulate)

        self.port = 55555
        self.intensity_recipes = {
            100: "1 sun, 1 h",
            50: "0.5 sun, 1 h",
            20: "0.2 sun, 1 h",
            10: "0.1 sun, 1 h",
            0: "dummy"
        }

    @property
    def name(self) -> str:
        """
        :returns: 'wavelabs sinus 70'
        """
        return 'wavelabs sinus 70'

    def _connect(self):
        super._connect(self.port)

    def _light_on(self):
        """
        Turn light on.

        :raises ValueError: Light intensity is not a valid value.
        """
        if self.intensity not in self.intensity_recipes:
            raise ValueError(f'Light intensity "{self.intensity} mW/cm2" is not defined.')

        if self.intensity == 0:
            return
        
        int_recipe = self.intensity_recipes[self.intensity]
        light_int_defined = True                    
        #connect to the lamp
        self.wavelabs_connect()
        
        # Send data
        message = "<WLRC><ActivateRecipe iSeq='" + str(self.seqNum) + "' sRecipe='" + int_recipe + "'/></WLRC>"
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
        (err, errString) = self.extract_error_string(replyString)
        if err:
            self.disconnect()
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
        
        self.disconnect()
        
        (err, errString) = self.extract_error_string(replyString)
        if err:
            raise ValueError("Error from Wavelabs Start Recipe:\n" + errString)


    def _light_off(self):
        """
        Turn off light.
        """
        self.connect()
        
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
        self.disconnect()
        
        #do this last of all because ValueError will abort execution of anything after it in the function.
        (err, errString) = self.extract_error_string(replyString)
        if err:
            raise ValueError("Error from Wavelabs Cancel Recipe:\n" + errString)