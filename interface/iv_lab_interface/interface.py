import sys
from time import sleep
import os
import json
import unicodedata
import re

from PyQt5.QtCore import (
    Qt,
    QSettings,
    QObject,
    QThread,
    pyqtSignal,
    QRectF
)

from PyQt5.QtGui import QIntValidator, QDoubleValidator
from PyQt5.QtWidgets import (
    QApplication,
    QLabel,
    QMainWindow,
    QPushButton,
    QComboBox,
    QLineEdit,
    QCheckBox,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QGroupBox,
    QFrame,
    QSplitter,
    QStackedWidget,
    QWidget,
    QFrame,
    QFileDialog,
    QMessageBox,
    QStatusBar,
)
from pyqtgraph import PlotWidget, plot
import pyqtgraph as pg
import numpy as np

from iv_lab_controller import controller as GuiCtrl

from .measurement import MeasurementFrame
from .plot import PlotFrame


class IVLabInterface(QWidget):
    """
    Main desktop interface for EPFL LPI IV Lab.
    """
    signal_initialize_hardware = pyqtSignal()
    signal_log_out = pyqtSignal()
    signal_log_in = pyqtSignal(str,str)
    signal_runIV = pyqtSignal(object)
    signal_runConstantV = pyqtSignal(object)
    signal_runConstantI = pyqtSignal(object)
    signal_runMaxPP = pyqtSignal(object)
    signal_runCalibration = pyqtSignal(object)
    signal_saveCalibration = pyqtSignal(object)
    signal_abortRun = pyqtSignal()
    signal_saveScanData = pyqtSignal(str, str)
    signal_toggleAutoSave = pyqtSignal(bool)
    progress = pyqtSignal(int)
    flag_abortRun = False

    # --- window close ---
    def closeEvent(self, event):
        self.__delete_controller()
        event.accept()

    def __del__(self):
        self.__delete_controller()

    def __init__(
        self,
        main_window=None,
        resources='resources/base',
        debug=False
    ):
        """
        :param main_window: QMainWindow of application.
        :param resources: Path to static app resources.
        :param debug: Debug mode. [Defualt: False]
        """
        super().__init__()
        self.__debug = debug

        # --- instance variables ---
        self.clicksCount = 0
        self.flag_abortRun = False

        # self.window = None
        self.settings = QSettings()
        self._app_resources = resources

        # --- init UI ---
        self.init_window(main_window)
        self.init_ui()
        self.register_connections()

    @property
    def debug(self):
        """
        :returns: Debug mode.
        """
        return self.__debug

    def init_window(self, window):
        """
        :param window: QWindow to initialize.
        """
        self.window = window
        self.window.setGeometry(100, 100, 1200, 600)
        self.window.setWindowTitle('IV Lab')

        self.statusBar = QStatusBar()
        window.setStatusBar(self.statusBar)
        self.statusBar.showMessage("Please Log In")

    def init_ui(self):
        """
        Initialize UI.
        """
        self.measurementFrame = MeasurementFrame()
        self.plotFrame = PlotFrame()

        layout = QHBoxLayout()
        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.addWidget(self.measurementFrame)
        self.splitter.addWidget(self.plotFrame)
        self.splitter.setStretchFactor(1,10)
        layout.addWidget(self.splitter)
        
        layout.setContentsMargins(10,10,10,10)
        
        self.setLayout(layout)
        
    def register_connections(self):
        """
        Register top level connections.
        """
        pass

    def __delete_controller(self):
        """
        Delete GUI controller.
        """
        pass
