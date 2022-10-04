from abc import abstractmethod

from PyQt6.QtCore import pyqtSignal

from PyQt6.QtWidgets import (
    QVBoxLayout,
    QPushButton,
    QWidget,
)

from .measurement_parameters import MeasurementParameters


class MeasurementParametersWidget(QWidget):
    """
    Measurement parameters widget.
    """
    run = pyqtSignal()
    abort = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.init_ui()
        self.register_connections()

    @property
    @abstractmethod
    def value(self) -> MeasurementParameters:
        """
        :returns: Parameter values.
        """
        raise NotImplementedError()

    def init_ui(self):
        self.btn_run = QPushButton("Run")

        self.btn_abort = QPushButton("Abort")
        self.btn_abort.setEnabled(False)

        lo_main = QVBoxLayout()
        self.init_params_ui(lo_main)

        lo_main.addWidget(self.btn_run)
        lo_main.addWidget(self.btn_abort)

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
        raise NotImplementedError()

    def register_connections(self):
        self.btn_run.clicked.connect(self.run.emit)
        self.btn_abort.clicked.connect(self.abort.emit)
