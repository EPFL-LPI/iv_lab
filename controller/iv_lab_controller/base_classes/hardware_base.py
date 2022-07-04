import logging

from pyee import EventEmitter

class HardwareBase(EventEmitter):
    """
    Base class for hardware devices.
    """
    def __init__(self):
        super().__init__()
        self._should_abort = False

    @property
    def should_abort(self) -> bool:
        """
        :returns: If measurement should be aborted
        """
        self._should_abort = True

    def show_status(self, msg: str):
        """
        Emits a `status_update` event with a message indicating the status.
        Logs a debug message with the message.

        :param msg: Message to be emitted and logged.
        """
        self.emit('status_update', msg)
        logging.debug(msg)