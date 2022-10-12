import os
from typing import Union

from PyQt6.QtCore import QRegularExpression
from PyQt6.QtGui import QRegularExpressionValidator
from PyQt6.QtWidgets import (
    QApplication,
    QPushButton,
    QLineEdit,
    QHBoxLayout,
    QWidget,
    QStyle,
)

from iv_lab_controller import gui as ctrl
from iv_lab_controller import common as ctrl_common
from iv_lab_controller.user import User
from iv_lab_controller.store import Store, Observer
from iv_lab_controller.types import RunnerState

from .. import common
from ..types import ApplicationState, HardwareState

        
class PlotHeaderWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.register_connections()
        self.init_observers()

    def init_ui(self):
        # @note: Functionality for autosave left in if desired for later use.
        # cell name
        cn_regex = QRegularExpression(r"[a-zA-Z\d\s\-_]{1,255}")
        cn_validator = QRegularExpressionValidator(cn_regex)
        self.in_cell_name = QLineEdit()
        self.in_cell_name.setValidator(cn_validator)
        self.in_cell_name.setPlaceholderText('Enter Cell Name Here...')
        self.in_cell_name.setMinimumWidth(500)
        self.in_cell_name.setEnabled(False)

        # open data folder
        qstyle = QApplication.style()
        self.btn_open_data_folder = QPushButton(
            qstyle.standardIcon(QStyle.StandardPixmap.SP_DirIcon),
            ''
        )
        self.btn_open_data_folder.setEnabled(False)

        # save mode
#        autosave = Store.get('autosave')
#        self.cb_auto_save = QCheckBox("Autosave")
#        self.cb_auto_save.setChecked(autosave)
#        self.cb_auto_save.setEnabled(False)

        # save
#        self.btn_save = QPushButton("Save Data",self)
#        self.btn_save.setEnabled(False)
        
        # layout
        lo_main = QHBoxLayout()
        lo_main.addWidget(self.in_cell_name)
#        lo_main.addWidget(self.cb_auto_save)
#        lo_main.addWidget(self.btn_save)
        lo_main.addWidget(self.btn_open_data_folder)
        self.setLayout(lo_main)

        self.reset_fields()

    def register_connections(self):
        self.in_cell_name.textChanged.connect(self.set_cell_name)
#        self.cb_auto_save.stateChanged.connect(self.toggle_auto_save)
#        self.btn_save.clicked.connect(self.save_data)

    def init_observers(self):
        # application
        def app_state_changed(state: ApplicationState, o_state: ApplicationState):
            if state is ApplicationState.Error:
                pass

            elif state is ApplicationState.Disabled:
                self.toggle_ui(False)

            elif state is ApplicationState.Active:
                hardware_state = Store.get('hardware_state')
                enable = hardware_state is HardwareState.Initialized
                self.toggle_ui(enable)

        app_state_observer = Observer(changed=app_state_changed)
        Store.subscribe('application_state', app_state_observer)

        # hardware
        def hardware_state_changed(state: HardwareState, o_state: HardwareState):
            if state is HardwareState.Error:
                self.toggle_ui(False)

            elif state is HardwareState.Uninitialized:
                self.toggle_ui(False)

            elif state is HardwareState.Initialized:
                self.toggle_ui(True)

        hardware_state_observer = Observer(changed=hardware_state_changed)
        Store.subscribe('hardware_state', hardware_state_observer)

        # runner
        def runner_state_changed(state: RunnerState, o_state: RunnerState):
            if (o_state is RunnerState.Running) and (state is RunnerState.Standby):
                self.in_cell_name.clear()

        runner_state_observer = Observer(changed=runner_state_changed)
        Store.subscribe('runner_state', runner_state_observer)

        # user
        def _open_data_folder(user):
            dir_path = get_best_user_directory(user)
            if dir_path is None:
                # could not find data directories
                common.show_message_box(
                    'Could not find data directories',
                    'Could not find data directories.\nPlease contact an administrator.'
                )
                return

            ctrl.open_path(dir_path)

        def user_changed(user: User, o_user: User):
            try:
                self.btn_open_data_folder.clicked.disconnect()

            except TypeError:
                # button did not have any connected slots
                pass

            if user is None:
                self.btn_open_data_folder.setEnabled(False)

            else:
                self.btn_open_data_folder.clicked.connect(
                    lambda: _open_data_folder(user)
                )
                self.btn_open_data_folder.setEnabled(True)

        user_observer = Observer(changed=user_changed)
        Store.subscribe('user', user_observer)

    def set_cell_name(self):
        """
        Sets the cell name in the store.
        """
        cell_name = self.in_cell_name.text().strip()
        if not cell_name:
            cell_name = None

        Store.set('cell_name', cell_name)

    def toggle_ui(self, enable: bool):
        """
        Toggles UI elements.
        """
        self.in_cell_name.setEnabled(enable)
#        self.cb_auto_save.setEnabled(enable)
#        self.btn_save.setEnabled(enable)

#    def toggle_auto_save(self):
#        autosave = self.cb_auto_save.isChecked()
#        Store.set('autosave', autosave)

    def reset_fields(self):
        """
        Reset field values to default.
        """
        self.in_cell_name.clear()
#        self.cb_auto_save.setChecked(False)


# ------------------------
# --- helper functions ---
# ------------------------

def get_best_user_directory(user: User) -> Union[str, None]:
    """
    Get most specific directory for a user.

    :param user: User.
    :returns: Path to most specific data directory for `user`,
        or None if could not be determined.
    """
    avail_dirs = [
        ctrl_common.user_daily_data_directory(user),
        ctrl_common.user_data_directory(user),
        ctrl_common.data_directory()
    ]

    dir_path = None
    for a_dir in avail_dirs:
        if os.path.exists(a_dir):
            dir_path = a_dir
            break

    return dir_path
