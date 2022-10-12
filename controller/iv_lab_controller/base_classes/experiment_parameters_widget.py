from abc import abstractmethod

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QVBoxLayout

from .experiment_parameters import ExperimentParametersInterface
from .value_widget import ValueWidget


# @note: Queueing functionality commented out for easy implentation
#   later on, if desired.
class ExperimentParametersWidget(ValueWidget):
    """
    Measurement parameters widget.
    """
    queue = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.init_ui()
        self.register_connections()

    @property
    @abstractmethod
    def value(self) -> ExperimentParametersInterface:
        """
        :returns: Parameter values.
        """
        raise NotImplementedError()

    @value.setter
    def value(self, value: ExperimentParametersInterface):
        """
        Sets the widget's value to match those given.
        """
        raise NotImplementedError()

    def init_ui(self):
        # self.btn_queue = QPushButton("Queue")

        lo_main = QVBoxLayout()
        self.init_params_ui(lo_main)
        # lo_main.addWidget(self.btn_queue)
        self.setLayout(lo_main)

    @abstractmethod
    def init_params_ui(self, lo_main: QVBoxLayout):
        """
        Adds parameter elements to the main layout.

        :param lo_main: Main layout.
        """
        raise NotImplementedError()

    @abstractmethod
    def reset_fields():
        """
        Set field values to default value.
        """
        raise NotImplementedError('`reset_fields` should be implemented by subclass')

    def register_connections(self):
        # self.btn_queue.clicked.connect(lambda: self.queue.emit())
        pass
