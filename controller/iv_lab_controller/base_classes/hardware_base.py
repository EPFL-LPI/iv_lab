import logging
from abc import ABC, abstractmethod

from pyee import EventEmitter
from pymeasure.instruments.instrument import Instrument


class HardwareBase(ABC, EventEmitter, Instrument):
    """
    Base class for hardware devices.

    :param emulate: Whether to emulate the hardware or not. [Default: False]
    """
    def __init__(self, emulate: bool = False):
        super().__init__()
        self._should_abort = False
        self._emulate = emulate
        self._connected = False

    @property
    @abstractmethod
    def name(self) -> str:
        """
        :returns: Name of the hardware.
            The name should be a unique static string that references the particular class.
        """
        raise NotImplementedError()

    # @todo: See pymeasure.experiment.procedure#Procedure.should_stop() 
    # https://github.com/pymeasure/pymeasure/blob/4770fe54be14b2c1618df9711b197330dbd3f262/pymeasure/experiment/procedure.py#L204
    @property
    def should_abort(self) -> bool:
        """
        :returns: If measurement should be aborted
        """
        return self._should_abort

    @property
    def emulate(self) -> bool:
        """
        :returns: Whether the hardware is running in emulation mode or not.
        """
        return self._emulate

    @property
    def connected(self) -> bool:
        """
        :returns: Whether or not the hardware is connected.
        """
        return self._connected

    @abstractmethod
    def _connect(self):
        """
        Connect to the hardware.
        """
        raise NotImplementedError()

    @abstractmethod
    def _disconnect(self):
        """
        Disconnect from the hardware.
        """
        raise NotImplementedError()

    def connect(self):
        """
        Connects to the hardware.
        """
        if (not self.emulate) and (not self.connected):
            self._connect()
            
        self._connected = True
    
    def disconnect(self):
        """
        Disconnects from the hardware.
        """
        if (not self.emulate) and self.connected:
            self._disconnect()

        self._connected = False

    def shutdown(self):
        """
        Shutdown the hardware.
        """
        raise NotImplementedError()

    def update_status(self, msg: str):
        """
        Emits a `status_update` event with a message indicating the status.
        Logs a debug message with the message.

        :param msg: Message to be emitted and logged.
        """
        self.emit('status_update', msg)
        logging.debug(msg)

