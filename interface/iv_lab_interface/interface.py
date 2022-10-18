import os
import json
import logging
from typing import Union, Any, Type

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
    QMenuBar,
)

from iv_lab_controller import common as ctrl_common
from iv_lab_controller import gui as gui_ctrl
from iv_lab_controller.store import Store, Observer
from iv_lab_controller.user import User, Permission
from iv_lab_controller.types import RunnerState
from iv_lab_controller.parameters.system_parameters import (
    SystemParameters,
    SystemParametersJSONEncoder,
)

from .types import (
    ApplicationState,
    HardwareState,
)

from . import common
from .experiment import ExperimentFrame
from .plot import PlotFrame
from .admin import (
    SystemsDialog,
    ApplicationLocationsDialog,
    UsersDialog
)


# logger
logger = logging.getLogger('iv_lab')
logger.setLevel(logging.INFO)


class IVLabInterface(QWidget):
    """
    Main desktop interface for EPFL LPI IV Lab.
    """
    progress = pyqtSignal(int)

    # --- window close ---
    def closeEvent(self, event):
        if Store.has('runner_state'):
            runner_state = Store.get('runner_state')
            if runner_state is RunnerState.Running:
                common.show_message_box(
                    'Can not quit program',
                    'Can not quit program while an experiment is running.'
                )
                event.ignore()
                return

            elif runner_state is RunnerState.Aborting:
                common.show_message_box(
                    'Can not quit program',
                    'Please wait for experiments to finish aborting, then try again.'
                )
                event.ignore()
                return

        logger.info('Program closed')
        self.__delete_controllers()
        event.accept()

    def __del__(self):
        logger.info('Program closed')
        self.__delete_controllers()

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

        # --- logger ---
        log_file = os.path.join(ctrl_common.get_admin_daily_data_directory(), 'log.txt')
        log_fmt = logging.Formatter('[%(asctime)s] %(message)s')
        log_fh = logging.FileHandler(log_file)
        log_fh.setFormatter(log_fmt)
        logger.addHandler(log_fh)

        if debug:
            logger.setLevel(logging.DEBUG)
            logger.info('Starting in debug mode')

        if emulate:
            logger.info('Starting in emulation mode')

        # --- instance variables ---
        self.settings = QSettings()
        self._app_resources = resources

        # --- store ---
        Store.set('debug_mode', debug)  # bool
        Store.set('emulation_mode', emulate)  # bool

        Store.set('status_msg', None)  # Union[str, None]
        Store.set('user', None)  # Union[User, None]
        Store.set('application_state', ApplicationState.Disabled)  # ApplicationState
        Store.set('hardware_state', HardwareState.Uninitialized)  # HardwareState
        Store.set('system', None)  # Union[System, None]
        Store.set('experiment_results', [])  # List[Results]
        Store.set('autosave', True)  # bool
        Store.set('cell_name', None)  # Union[str, None]

        # --- init UI ---
        self.init_window(main_window)
        self.init_ui()
        self.register_connections()
        self.init_observers()

    def init_window(self, window):
        """
        :param window: QWindow to initialize.
        """
        self.window = window
        self.window.setGeometry(100, 100, 1200, 600)
        self.window.setWindowTitle('IV Lab')
        self.window.closeEvent = self.closeEvent

        self.status_bar = QStatusBar()
        window.setStatusBar(self.status_bar)

    def init_ui(self):
        """
        Initialize UI.
        """
        self.wgt_experiment = ExperimentFrame()
        self.wgt_plot = PlotFrame()
        self.authentication = self.wgt_plot.authentication

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.wgt_experiment)
        splitter.addWidget(self.wgt_plot)
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
        pass

    def init_observers(self):
        # status messages
        def status_changed(msg: Union[str, None], o_msg: Union[str, None]):
            """
            Updates the status bar message.
            """
            logger.debug(msg)
            self.status_bar.showMessage(msg)

        status_observer = Observer(changed=status_changed)
        Store.subscribe('status_msg', status_observer)

        # user
        def user_changed(user: Union[User, None], o_user: Union[User, None]):
            """
            Sets the UI based on the user's authentication state.
            """
            # clear user results if needed
            if user is None:
                Store.set('experiment_results', [])
                Store.set('application_state', ApplicationState.Disabled)

            else:
                Store.set('application_state', ApplicationState.Active)

        user_observer = Observer(changed=user_changed)
        Store.subscribe('user', user_observer)

        # application state
        def app_state_changed(state: ApplicationState, o_state: ApplicationState):
            """
            Sets the application state, updating fields as needed.

            :param state: Application state.
            """
            if state is ApplicationState.Disabled:
                self.destroy_ui()

            elif state is ApplicationState.Active:
                user = Store.get('user')
                if user is None:
                    return

                # basic
                if Permission.Basic in user.permissions:
                    self.create_basic_ui()

                # admin
                if Permission.Admin in user.permissions:
                    self.create_admin_ui()

            elif state is ApplicationState.Error:
                pass

            else:
                # @unreachable
                raise ValueError('Unknown application state')

        app_state_observer = Observer(changed=app_state_changed)
        Store.subscribe('application_state', app_state_observer)

        # hardware state
        def hardware_state_changed(state: HardwareState, o_state: HardwareState):
            """
            """
            if (state is HardwareState.Uninitialized):
                if hasattr(self, 'mn_basic'):
                    # disable system actions
                    self.mn_system_parameters.setEnabled(False)
                    self.mn_experiment_parameters.setEnabled(False)

            if (state is HardwareState.Initialized):
                if hasattr(self, 'mn_basic'):
                    # disable system actions
                    self.mn_system_parameters.setEnabled(True)
                    self.mn_experiment_parameters.setEnabled(True)

        hardware_state_observer = Observer(changed=hardware_state_changed)
        Store.subscribe('hardware_state', hardware_state_observer)

        # debug
        def debug_mode_changed(debug: bool, o_debug: bool):
            # set logger level
            log_level = logging.DEBUG if debug else logging.INFO
            logger.setLevel(log_level)

            # log change
            log_msg = (
                'Entered debug mode'
                if debug else
                'Exited debug mode'
            )
            logger.info(log_msg)

            log_level = 'logging.DEBUG' if debug else 'logging.INFO'
            logger.info(f'Changed logging to {log_level}')

            if hasattr(self, 'act_debug_mode'):
                # change menu text
                act_text = (
                    'Disable debug mode'
                    if debug else
                    'Enable debug mode'
                )

                self.act_debug_mode.setText(act_text)

        debug_observer = Observer(changed=debug_mode_changed)
        Store.subscribe('debug_mode', debug_observer)

        # emuate
        def emulate_mode_changed(emulate: bool, o_emulate: bool):
            # log change
            log_msg = (
                'Entered emulation mode'
                if emulate else
                'Exited emulation mode'
            )
            logger.info(log_msg)

            if hasattr(self, 'act_emulate_mode'):
                # change menu text
                act_text = (
                    'Disable emulate mode'
                    if emulate else
                    'Enable emulate mode'
                )

                self.act_emulate_mode.setText(act_text)

        emulate_observer = Observer(changed=emulate_mode_changed)
        Store.subscribe('emulation_mode', emulate_observer)

    def __delete_controllers(self):
        """
        Clean up controllers.
        """
        pass

    def create_basic_ui(self):
        """
        Create the basic UI.
        """

        self.mn_basic = self.mb_main.addMenu('User')

        # system parameters
        self.mn_system_parameters = self.mn_basic.addMenu('System parameters')

        # system parameters - save 
        act_system_parameters_save = self.mn_system_parameters.addAction('Save')
        act_system_parameters_save.triggered.connect(self.basic_system_parameters_save)

        # system parameters - load 
        act_system_parameters_load = self.mn_system_parameters.addAction('Load')
        act_system_parameters_load.triggered.connect(self.basic_system_parameters_load)

        # experiment parameters
        self.mn_experiment_parameters = self.mn_basic.addMenu('Experiment parameters')

        # experiment parameters - save
        act_experiment_parameters_save = self.mn_experiment_parameters.addAction('Save')
        act_experiment_parameters_save.triggered.connect(self.basic_experiment_parameters_save)

        # @todo: How should parameters be loaded?
        #   Should experimetn be selected when loaded?
        # experiment parameters - load
        # act_experiment_parameters_load = self.mn_experiment_parameters.addAction('Load')
        # act_experiment_parameters_load.triggered.connect(self.basic_experiment_parameters_load)

        # enable menu items as needed
        hardware_state = Store.get('hardware_state')
        if hardware_state is HardwareState.Uninitialized:
            self.mn_system_parameters.setEnabled(False)
            self.mn_experiment_parameters.setEnabled(False)

    def create_admin_ui(self):
        """
        Create the admin UI.
        """
        self.mn_admin = self.mb_main.addMenu('Admin')

        act_set_system = self.mn_admin.addAction('Set system')
        act_set_system.triggered.connect(self.admin_set_system)

        act_locations = self.mn_admin.addAction('Application locations')
        act_locations.triggered.connect(self.admin_locations)

        act_users = self.mn_admin.addAction('Users')
        act_users.triggered.connect(self.admin_users)

        # debug
        debug_text = (
            'Disable debug mode'
            if Store.get('debug_mode') else
            'Enable debug mode'
        )

        self.act_debug_mode = self.mn_admin.addAction(debug_text)
        self.act_debug_mode.triggered.connect(self.toggle_debug_mode)

        # emulate
        emulate_text = (
            'Disable emulate mode'
            if Store.get('emulation_mode') else
            'Enable emulate mode'
        )

        self.act_emulate_mode = self.mn_admin.addAction(emulate_text)
        self.act_emulate_mode.triggered.connect(self.toggle_emulate_mode)

    def destroy_ui(self):
        """
        Destorys the owned UI.
        """
        self.mb_main.clear()

    # ---------------------
    # --- basic actions ---
    # ---------------------

    def basic_system_parameters_save(self):
        """
        Saves the current system parameters for the user.
        """
        user = Store.get('user')
        path = gui_ctrl.get_parameters_save_path(user)
        if path is None:
            return

        value = self.wgt_experiment.wgt_parameters.wgt_system_parameters.value
        save_value_to_file(value, path, encoder=SystemParametersJSONEncoder)

    # @todo
    def basic_system_parameters_load(self):
        """
        Loads user selected system parameters.
        """
        user = Store.get('user')
        path = gui_ctrl.get_parameters_file_path(user)
        if path is None:
            return

        value = load_value_from_file(path)
        if value is None:
            return

        value = SystemParameters.from_dict(value)
        try:
            self.wgt_experiment.wgt_parameters.wgt_system_parameters.value = value

        except Exception as err:
            common.debug(err)
            common.show_message_box(
                'Could not load parameters',
                f'An error occurred when attempting to set parameters from file\n{err}'
            )

    def basic_experiment_parameters_save(self):
        """
        Saves the current experiment parameters for the user.
        """
        user = Store.get('user')
        path = gui_ctrl.get_parameters_save_path(user)
        if path is None:
            return

        value = self.wgt_experiment.wgt_parameters.wgt_experiment_parameters.value
        save_value_to_file(value.to_dict_default(), path)

    # @todo
    def basic_experiment_parameters_load(self):
        """
        Loads user selected experiment parameters.
        """
        pass

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

    def toggle_debug_mode(self):
        """
        Toggle debug mode.
        """
        debug = Store.get('debug_mode') 
        Store.set('debug_mode', not debug)

    def toggle_emulate_mode(self):
        """
        Toggle emulate mode.
        """
        emulate = Store.get('emulation_mode')
        Store.set('emulation_mode', not emulate)


# ------------------------
# --- helper functions ---
# ------------------------


def save_value_to_file(
    value: Any,
    path: str,
    mode: str = 'w',
    encoder: Union[Type[json.JSONEncoder], None] = None
):
    """
    Saves a value to a file using JSON encoding.

    :param value: Value to save.
    :param path: Path to save to.
    :param mode: File mode to write with. [Default: 'w']
    :param encoder: JSON encoder to user, or `None` for default. [Default: `None`]
    """
    with open(path, mode) as f:
        try:
            json.dump(value, f, cls=encoder, indent=4)

        except Exception as err:
            common.debug(err)
            common.show_message_box(
                'Could not save',
                f'An error occurred while saving\n{err}'
            )
            return


def load_value_from_file(
    path: str,
    decoder: Union[Type[json.JSONDecoder], None] = None
) -> Any:
    """
    Loads a JSON value from a file

    :param path: Path to save to.
    :param decoder: JSON decoder to user, or `None` for default. [Default: `None`]
    :returns: Object or `None` if error.
    """
    with open(path) as f:
        try:
            val = json.load(f, cls=decoder)

        except Exception as err:
            common.debug(err)
            common.show_message_box(
                'Could not load',
                f'An error occurred while loading\n{err}'
            )
            return None

    return val
