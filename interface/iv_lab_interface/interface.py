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
    QMenuBar
)
from pymeasure.experiment import Procedure, Results

from iv_lab_controller import Store
from iv_lab_controller.store import Observer
from iv_lab_controller import common as ctrl_common
from iv_lab_controller.user import User, Permission

from .types import (
    ApplicationState,
    HardwareState,
)

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
        Store.set('system_path', ctrl_common.system_path())  # str
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

        self.status_bar = QStatusBar()
        window.setStatusBar(self.status_bar)

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
        pass

    def init_observers(self):
        # status messages
        def status_changed(msg: Union[str, None], o_msg: Union[str, None]):
            """
            Updates the status bar message.
            """
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
            if state == ApplicationState.Disabled:
                self.toggle_admin_ui(enable=False)

            elif state == ApplicationState.Active:
                user = Store.get('user')
                is_admin = (
                    (user is not None) and
                    (Permission.Admin in user.permissions)
                )
                self.toggle_admin_ui(enable=is_admin)

            elif state == ApplicationState.Running:
                pass

            elif state == ApplicationState.Error:
                pass

            else:
                # @unreachable
                raise ValueError('Unknown application state')

        app_state_observer = Observer(changed=app_state_changed)
        Store.subscribe('application_state', app_state_observer)

    def __delete_controller(self):
        """
        Delete GUI controller.
        """
        pass

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
