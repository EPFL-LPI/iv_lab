from typing import Tuple
import socket
import logging

from iv_lab_controller.base_classes import Lamp


class WavelabsLamp(Lamp):
    """
    Wavelabs based lamps base class.
    """
    @staticmethod
    def extract_error_string(replyString: str) -> Tuple[bool, str]:
        errIndex = replyString.find("iEC='0'")
        if errIndex != -1:
            return (False,"No Error")
            
        startIndex = replyString.find('sError=')
        endIndex = replyString.find('\>')
        if startIndex == -1 or endIndex == -1:
            return (True, "Did not receive proper reply from Wavelabs")
        else:    
            return (True, replyString[startIndex+8:endIndex-1])

    def __init__(self, emulate: bool = False):
        """
        :param emulate: Whether to emulate the lamp or not. [Default: False]
        """
        super().__init__(emulate=emulate)

        self.sock = None
        self.connection = None
        self.server_address = None
        self.connection_open = False

        self.recipeDict = {} #hardware['recipeDict']

    def _connect(self, port: int, host: str = '127.0.0.1'):
        """
        Connect to the lamp.

        :param port: Port to connect to.
        :param host: Host to connect to. [Default: '127.0.0.1']
        """
        # Create a TCP/IP socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        # Bind the socket to the port
        self.server_address = (host, port)
        logging.debug('starting up on %s port %s' % self.server_address)
        self.sock.bind(self.server_address)
        
        self.sock.settimeout(5)
        
        # Listen for incoming connections
        self.sock.listen(1)
        
        # Wait for a connection
        logging.debug('waiting for a connection')
        
        self.connection, self.client_address = self.sock.accept()
        
        logging.debug("Got Connection from ")
        logging.debug(self.client_address)
        
        # set read-timeout for connection queries
        self.connection.settimeout(1)
        
        self.connection_open = True
        self.seqNum = 0
    
    def _disconnect(self):
        logging.debug('closing socket')
        if self.connection is not None:
            self.connection.close()
        
        if self.sock is not None:
            self.sock.close()
        
        self.connection_open = False

    def _turn_off(self):
        if self.connection_open:
            self._disconnect()        
