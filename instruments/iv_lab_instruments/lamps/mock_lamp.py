import logging

from iv_lab_controller.base_classes import HardwareBase, Lamp


class MockLamp(Lamp):
    """
    Mock lamp controller used for testing.
    """
    @HardwareBase.name.getter
    def name(self) -> str:
        """
        :returns: 'mock lamp'.
        """
        return 'mock lamp'

    def _connect(self):
        """
        Connect to the lamp.
        """
        logging.debug('connect')

    def _disconnect(self):
        """
        Disconnect from the lamp.
        """
        logging.debug('disconnect')

    def _light_on(self):
        """
        Turn light on.
        """
        logging.debug('light on')

    def _light_off(self):
        """
        Turn light off.
        """
        logging.debug('light off')
                
    def _turn_off(self):
        """
        Turn off system.
        """
        logging.debug('turn off')
