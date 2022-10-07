import os
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
from pymeasure.experiment import Procedure, Results

from iv_lab_controlelr import Store
from iv_lab_controller import system as SystemCtrl
from iv_lab_controller import common as ctrl_common
from iv_lab_controller.user import User, Permission
from iv_lab_controller.base_classes import (
    System,
    Experiment,
    ExperimentParameters,
)

from . import common
from .types import ExperimentQueue, ApplicationState, HardwareState
from .experiment import ExperimentFrame
from .plot import PlotFrame
from .admin import (
    SystemsDialog,
    ApplicationLocationsDialog,
    UsersDialog
)


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
        self._state: ApplicationState = ApplicationState.LoggedOut
        self._hardware_state: HardwareState = HardwareState.Standby

        self.system: Union[System, None] = None
        self._system_name: Union[str, None] = None

        self.settings = QSettings()
        self._app_resources = resources

        self._user_results: List[Results] = []

        # --- init UI ---
        self.init_window(main_window)
        self.init_ui()
        self.register_connections()

        # signal all listeners of initial user
        self._user: Union[User, None] = None

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
    def state(self) -> ApplicationState:
        """
        :returns: Current state of the application.
        """
        return self.state

    @state.setter
    def state(self, state: ApplicationState):
        """
        Sets the application state, updating fields as needed.

        :param state: Application state.
        """
        self._state = state
        if self.state == ApplicationState.LoggedOut:
            pass

        elif self.state == ApplicationState.Standby:
            pass

        elif self.state == ApplicationState.Running:
            pass

        elif self.state == ApplicationState.Error:
            pass

        else:
            # @unreachable
            raise ValueError('Unknown application state')

    @property
    def system_name(self) -> Union[str, None]:
        """
        :returns: Name of the loaded system or None if not loaded.
        """
        return self._system_name

    @property
    def user_results(self) -> List[Results]:
        """
        :returns: List of current results for the user.
        """
        return self._user_results

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
        self.experiment_frame = ExperimentFrame()
        self.plot_frame = PlotFrame()
        self.authentication = self.plot_frame.authentication

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.experiment_frame)
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
        self.experiment_frame.initialize_hardware.connect(self.initialize_system)
        self.experiment_frame.run_experiments.connect(self.run_experiments)

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

        # clear user results if needed
        if user is None:
            self.clear_results()

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
        # subcomponents
        self.experiment_frame.enable_ui()

    def disable_user_ui(self):
        """
        Disables logged in user UI elements.
        """
        self.clear_results()
        self.experiment_frame.disable_ui()
        self.plot_frame.disable_ui()

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
        Clears the user's results.
        """
        self._user_results = []

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

            self.experiment_frame.experiments = experiments

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
            self.experiment_frame.system = self.system
            common.StatusBar().showMessage('Hardware initialized')

        # enable plot ui
        self.plot_frame.enable_ui()

    def run_experiments(self, experiments: ExperimentQueue):
        """
        Runs an experiments queue.
        """
        for exp, params in experiments:
            self.run_experiment(exp, params)

    def run_experiment(self, exp: Experiment, params: ExperimentParameters):
        """
        Runs an experiment.
        """
        proc = exp.create_procedure(params.to_dict())
        self.run_procedure(exp.name, proc)

    def run_procedure(self, exp_name: str, procedure: Procedure):
        """
        Runs a procedure.

        :param exp_name: Experiment name.
        :param procedure: The procedure to run.
            The `lamp` and `smu` will be set from the system.
        """
        # data file
        cell_name = self.plot_frame.cell_name
        if not cell_name:
            common.show_message_box(
                'No cell name',
                'Please enter a name for your cell.'
            )
            return

        daily_dir = ctrl_common.get_user_daily_data_directory(self.user)

        filename = f'{cell_name}--{exp_name}'
        data_path = os.path.join(daily_dir, filename)
        data_path += '.csv'
        data_path = ctrl_common.unique_file(data_path)

        # procedure
        procedure.lamp = self.system.lamp
        procedure.smu = self.system.smu

        result = Results(procedure, data_path)
        self.add_results(result)

    def add_results(self, result: Results):
        """
        """
        self._user_results.append(result)
        self.plot_frame.add_result(result)

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
