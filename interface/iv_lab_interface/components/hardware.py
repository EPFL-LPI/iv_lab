from typing import Union

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QPushButton,
    QMessageBox,
)

from iv_lab_controller import Store
from iv_lab_controller.store import Observer
from iv_lab_controller import system as SystemCtrl
from iv_lab_controller import common as ctrl_common
from iv_lab_controller.user import User

from .. import common
from ..base_classes import ToggleUiInterface
from ..types import HardwareState


class HardwareInitialization(QWidget, ToggleUiInterface):
    """
    Handles hardware initialization.
    """

    def __init__(self):
        super().__init__()

        self.init_ui()
        self.register_connections()
        self.init_observers()

    def init_ui(self):
        self.btn_initialize = QPushButton("Initialize Hardware", self)
        self.btn_initialize.setMaximumWidth(300)
        self.btn_initialize.setEnabled(False)

        lo_main = QVBoxLayout()
        lo_main.addWidget(self.btn_initialize)
        self.setLayout(lo_main)

    def register_connections(self):
        self.btn_initialize.clicked.connect(self.initialize_hardware)

    def init_observers(self):
        # hardware state
        def state_changed(state: HardwareState, o_state: HardwareState):
            if state is HardwareState.Uninitialized:
                self.enable_ui()

            elif state is HardwareState.Initialized:
                self.disable_ui()

            elif state is HardwareState.Error:
                # allow user to attempt reinitialization
                self.enable_ui()

            else:
                raise ValueError('Unknown hardware state')

        state_observer = Observer(changed=state_changed)
        Store.subscribe('hardware_state', state_observer)
    
        # user
        def user_changed(user: Union[User, None], o_user: Union[User, None]):
            if user is None:
                self.disable_ui()

            else:
                self.enable_ui()

        user_observer = Observer(changed=user_changed)
        Store.subscribe('user', user_observer)

        # system path
        def system_path_changed(path: str, o_path: str):
            if path == o_path:
                return

            # deactivate hardware
            Store.set('hardware_state', HardwareState.Uninitialized)

        sys_path_observer = Observer(changed=system_path_changed)
        Store.subscribe('system_path', sys_path_observer)

    def enable_ui(self):
        self.btn_initialize.setEnabled(True)

    def disable_ui(self):
        self.btn_initialize.setEnabled(False)

    def initialize_hardware(self):
        """
        Create system controller if not already.
        Initialize hardware.
        """
        emulate = Store.get('emulation_mode')
        system = Store.get('system')
        if system is None:
            # load system
            try:
                system_file = ctrl_common.system_path()
                _system_name, system_cls = SystemCtrl.load_system(system_file, emulate=emulate)
            
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

            system = system_cls(emulate=emulate)
            system.smu.add_listener('status_msg', lambda msg: Store.set('status_msg', msg))
            system.lamp.add_listener('status_msg', lambda msg: Store.set('status_msg', msg))
            Store.set('system', system)

        # initialize hardware
        Store.set('status_msg', 'Initializing hardware...')
        try:
            system.connect()

        except Exception as err:
            common.show_message_box(
                'Could not initialize hardware',
                f'Could not initialize hardware due to the following error.\n{err}',
                icon=QMessageBox.Icon.Critical
            )
            Store.set('status_msg', 'Error initializing hardware')

        else:
            Store.set('status_msg', 'Hardware initialized')
            Store.set('hardware_state', HardwareState.Initialized)
