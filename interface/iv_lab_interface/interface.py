import json
from typing import Union, List

from PyQt6.QtCore import (
    Qt,
    QSettings,
    pyqtSignal
)

from PyQt6.QtWidgets import (
    QMainWindow,
    QHBoxLayout,
    QSplitter,
    QWidget,
    QStatusBar,
    QMessageBox,
    QMenuBar
)
from pymeasure.experiment.procedure import Procedure

from iv_lab_controller import gui as GuiCtrl
from iv_lab_controller import system as SystemCtrl
from iv_lab_controller import common as ctrl_common
from iv_lab_controller.user import User, Permission
from iv_lab_controller.system_parameters import SystemParameters
from iv_lab_controller.base_classes.system import System
from iv_lab_controller.base_classes.results import Results
from iv_lab_controller.base_classes.experiment import Experiment

from . import common
from .measurement import MeasurementFrame
from .plot import PlotFrame
from .admin.systems import SystemsDialog
from .admin.locations import ApplicationLocationsDialog
from .admin.users import UsersDialog


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
        # self.clicksCount = 0
        self.flag_abortRun: bool = False
        self.system: Union[System, None] = None
        self._system_name: Union[str, None] = None

        # self.window = None
        self.settings = QSettings()
        self._app_resources = resources

        # --- init UI ---
        self.init_window(main_window)
        self.init_ui()
        self.register_connections()

        # signal all listeners of initial user
        self.user: Union[User, None] = None

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

    @property
    def system_name(self) -> Union[str, None]:
        """
        :returns: Name of the loaded system or None if not loaded.
        """
        return self._system_name

    def init_window(self, window):
        """
        :param window: QWindow to initialize.
        """
        self.window = window
        self.window.setGeometry(100, 100, 1200, 600)
        self.window.setWindowTitle('IV Lab')

        self.statusBar = QStatusBar()
        window.setStatusBar(self.statusBar)
        common.StatusBar(self.statusBar)  # intialize status bar interface

    def init_ui(self):
        """
        Initialize UI.
        """
        self.measurement_frame = MeasurementFrame()
        self.plot_frame = PlotFrame()
        self.authentication = self.plot_frame.authentication

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.measurement_frame)
        splitter.addWidget(self.plot_frame)
        splitter.setStretchFactor(1, 10)
        
        layout = QHBoxLayout()
        layout.addWidget(splitter)
        layout.setContentsMargins(10, 10, 10, 10)
        self.setLayout(layout)

        # main menu bar
        self.mb_main = QMenuBar()
        self.window.setMenuBar(self.mb_main)

    def register_connections(self):
        """
        Register top level connections.
        """
        self.authentication.user_authenticated.connect(self.set_user)
        self.authentication.user_logged_out.connect(self.on_log_out)
        self.measurement_frame.initialize_hardware.connect(self.initialize_system)
        self.measurement_frame.run_procedure.connect(self.run_procedure)

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
        enable_user_ui = (user is not None)
        self.toggle_user_ui(enable=enable_user_ui)
        is_admin = (
            (user is not None) and
            (Permission.Admin in user.permissions)
        )

        self.toggle_admin_ui(enable=is_admin)

    def set_user(self, user: Union[User, None]):
        """
        Delegator for `self.user = user`
        """
        self.user = user

    def on_log_out(self):
        """
        Set user to None.
        """
        self.user = None

    def toggle_user_ui(self, enable: Union[bool, None] = None):
        """
        Toggles the user UI state.

        :param enabled: Whether to enable or disable the UI.
            None to toggle to current user state.
            [Default: None]
        """
        if enable == None:
            enable = (self.user is not None)

        if enable:
            self.enable_user_ui()

        else:
            self.disable_user_ui()

    def enable_user_ui(self):
        """
        Enables UI elements for logged in users.
        """
        username = 'guest' if (self.user is None) else self.user.username

        # subcomponents
        self.measurement_frame.enable_ui()

        # user-specific configuration files should be located here:
        # configFilePath = os.path.join(self.sp.computer['basePath'] , self.username , 'IVLab_config.json')

        # tell the gui to load the configuration file
        # self.win.loadSettingsFile(configFilePath)

    def disable_user_ui(self):
        """
        Disables logged in user UI elements.
        """
        self.clear_results()
        self.measurement_frame.disable_ui()

    def toggle_admin_ui(self, enable: bool = False):
        """
        Initialize admin UI.

        :param enable: Whether to enable or diable the UI.
        """
        if enable:
            self.enable_admin_ui()

        else:
            self.disable_admin_ui()

    def enable_admin_ui(self):
        """
        Enable the admin UI.
        """
        self.mn_admin = self.mb_main.addMenu('Admin')
        
        act_set_system = self.mn_admin.addAction('Set system')
        act_set_system.triggered.connect(self.admin_set_system)

        act_locations = self.mn_admin.addAction('Application locations')
        act_locations.triggered.connect(self.admin_locations)

        act_users = self.mn_admin.addAction('Users')
        act_users.triggered.connect(self.admin_users)

    def disable_admin_ui(self):
        """
        Disables the admin UI.
        """
        self.mb_main.clear()
        
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

    def initialize_system(self):
        """
        Create system controller if not already.
        Initialize hardware.
        """
        # load system files
        if self.system is None:
            # load system
            try:
                system_file = ctrl_common.system_path()
                self._system_name, system_cls = SystemCtrl.load_system(system_file, emulate=self.emulate)
            
            except FileNotFoundError:
                common.show_message_box(
                    'Could not load System',
                    f'Could not find System file\nPlease contact an administrator.',
                    icon=QMessageBox.Icon.Critical
                )
                return

            except RuntimeError as err:
                common.show_message_box(
                    'Could not load System',
                    f'Could not load System due to the following error:\n{err}\nPlease contact an administrator.',
                    icon=QMessageBox.Icon.Critical
                )
                return

            self.system = system_cls(emulate=self.emulate)
            self.system.smu.add_listener('status_update', common.StatusBar().showMessage)
            self.system.lamp.add_listener('status_update', common.StatusBar().showMessage)

            experiments: List[Experiment] = []
            for perm in self.user.permissions:
                experiments += self.system.experiments_for_permission(perm)

            self.measurement_frame.experiments = experiments

        # initialize hardware
        common.StatusBar().showMessage('Initializing hardware...')
        try:
            self.system.connect()

        except Exception as err:
            common.show_message_box(
                'Could not initialize hardware',
                f'Could not initialize hardware due to the following error.\n{err}',
                icon=QMessageBox.Icon.Critical
            )
            common.StatusBar().showMessage('Error initializing hardware')

        else:
            self.measurement_frame.system = self.system
            common.StatusBar().showMessage('Hardware initialized')

    # @todo
    def run_procedure(self, procedure: Procedure):
        """
        Runs a procedure.

        :param procedure: The procedure to run.
            The `lamp` and `smu` will be set from the system.
        """
        procedure.lamp = self.system.lamp
        procedure.smu = self.system.smu
        results = Results(procedure, data_filename)

        cell_name = self.plot_frame.plotHeader.cell_name
        cell_name = GuiCtrl.sanitize_cell_name(cell_name)

    # ---------------------
    # --- admin actions ---
    # ---------------------

    def admin_set_system(self):
        """
        Open the system setup dialog.
        """
        dlg_system = SystemsDialog()
        dlg_system.exec()

    def admin_locations(self):
        """
        Open the application location dialog.
        """
        dlg_locations = ApplicationLocationsDialog()
        dlg_locations.exec()

    def admin_users(self):
        """
        Open the user editing dialog.
        """
        dlg_users = UsersDialog()
        dlg_users.exec()
