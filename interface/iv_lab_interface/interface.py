import sys
from time import sleep
import os
import json
import unicodedata
import re
from typing import Union

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
    QStatusBar,
    QMessageBox
)

import numpy as np
import pyqtgraph as pg
from pyqtgraph import PlotWidget, plot

from iv_lab_controller import gui as GuiCtrl
from iv_lab_controller.user import User
from iv_lab_controller.system import System
from iv_lab_controller.system_parameters import SystemParameters

from . import common
from .measurement import MeasurementFrame
from .plot import PlotFrame


class IVLabInterface(QWidget):
    """
    Main desktop interface for EPFL LPI IV Lab.
    """
    progress = pyqtSignal(int)

    # --- window close ---
    def closeEvent(self, event):
        self.__delete_controller()
        event.accept()

    def __del__(self):
        self.__delete_controller()

    def __init__(
        self,
        main_window: QMainWindow = None,
        resources: str = 'resources/base',
        debug: bool = False,
        emulate: bool = False
    ):
        """
        :param main_window: QMainWindow of application.
        :param resources: Path to static app resources.
        :param debug: Debug mode. [Defualt: False]
        :param emulate: Run application in emulation mode. [Default: False]
        """
        super().__init__()
        self._emulate = emulate
        self.__debug = debug

        # --- instance variables ---
        self.clicksCount = 0
        self.flag_abortRun = False
        self.system = None

        # self.window = None
        self.settings = QSettings()
        self._app_resources = resources

        # --- init UI ---
        self.init_window(main_window)
        self.init_ui()
        self.register_connections()

        # signal all listeners of initial user
        self.user = None

    @property
    def debug(self) -> bool:
        """
        :returns: Debug mode.
        """
        return self.__debug

    @property
    def emulate(self) -> bool:
        """
        :returns: Emulation mode.
        """
        return self._emulate

    def init_window(self, window):
        """
        :param window: QWindow to initialize.
        """
        self.window = window
        self.window.setGeometry(100, 100, 1200, 600)
        self.window.setWindowTitle('IV Lab')

        self.statusBar = QStatusBar()
        window.setStatusBar(self.statusBar)

    def init_ui(self):
        """
        Initialize UI.
        """
        self.measurementFrame = MeasurementFrame()
        self.plotFrame = PlotFrame()
        self.authentication = self.plotFrame.authentication

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self.measurementFrame)
        splitter.addWidget(self.plotFrame)
        splitter.setStretchFactor(1,10)
        
        layout = QHBoxLayout()
        layout.addWidget(splitter)
        layout.setContentsMargins(10,10,10,10)
        
        self.setLayout(layout)
        
    def register_connections(self):
        """
        Register top level connections.
        """
        self.authentication.user_authenticated.connect(self.set_user)
        self.measurementFrame.signal_initialize_hardware.connect(self.initializeHardware)

    def __delete_controller(self):
        """
        Delete GUI controller.
        """
        pass

    @property
    def user(self) -> Union[User, None]:
        return self._user

    @user.setter
    def user(self, user: Union[User, None]):
        self._user = user
        enable_ui = user is not None
        self.enable_user_ui(enable_ui)

    def set_user(self, user: Union[User, None]):
        """
        Delegator for self.user = user
        """
        self.user = user

    def enable_user_ui(self, enabled: bool = True):
        """
        Enables UI elements for logged in users.

        :param enabled: Whether to enable or disable the UI. [Default: True]
        """
        username = 'guest' if self.user is None else self.user.username

        # subcomponents
        self.authentication.set_username(username)
        self.authentication.setCurrentIndex(0 if self.user is None else 1)
        self.measurementFrame.enable_ui(enabled)

        # status bar
        status_msg = (
            f'Logged in as {username}'
            if enabled else
            "Logged out"
        )
        self.statusBar.showMessage(status_msg)

        # clean up
        if not enabled:
            self.clear_results()

        # user-specific configuration files should be located here:
        # configFilePath = os.path.join(self.sp.computer['basePath'] , self.username , 'IVLab_config.json')

        # tell the gui to load the configuration file
        # self.win.loadSettingsFile(configFilePath)


    def clear_results(self):
        """
        Disables UI elements that only logged in users can access.
        """
        # user-specific configuration files should be located here:
        # configFilePath = os.path.join(self.sp.computer['basePath'] , self.username , 'IVLab_config.json')
        # tell the gui to save the current settings to the user's configuration file
        # self.win.saveSettingsFile(configFilePath)
        # clear the previous values from the gui
        # self.win.setAllFieldsToDefault()
        
        # clear out scan data and results
        self.data_IV = None
        self.IV_Results = None
        self.data_CC = None
        self.CC_Results = None
        self.data_CV = None
        self.CV_Results = None
        self.data_MPP = None
        self.MPP_Results = None
        
        # disconnect the hardware
        try:
            self.SMU.disconnect()
            self.lamp.disconnect()

        except:
            # nothing to do here
            pass


    def initializeHardware(self):
        """
        Create System contorller if not already.
        Initialize hardware.
        """
        if self.system is None:
            try:
                sys_params = SystemParameters.from_file()
            
            except FileNotFoundError:
                common.show_message_box(
                    'Missing system parameters file',
                    'System parameters file could not be found. Please contact an administrator.',
                    icon=QMessageBox.Critical
                )
                return


            except json.JSONDecodeError:
                common.show_message_box(
                    'System parameters file corrupted',
                    'System parameters file is corrupted. Please contact an administrator.',
                    icon=QMessageBox.Critical
                )
                return

            self.system = System(sys_params)
            self.system.SMU.on('status_update', self.statusBar.showMessage)
            self.system.lamp.on('status_update', self.statusBar.showMessage)

        self.system.hardware_init()