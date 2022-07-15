from iv_lab_controller.base_classes.computer_parameters import ComputerParameters


class MockComputerParameters(ComputerParameters):
    """
    Mock computer parameters used for testing.
    """
    def __init__(self):
        self._name = 'mock computer parameters'
        self._os = 'mock os'
        self._data_path = 'Downloads'