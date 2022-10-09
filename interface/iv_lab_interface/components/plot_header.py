from PyQt6.QtCore import QRegularExpression
from PyQt6.QtGui import QRegularExpressionValidator
from PyQt6.QtWidgets import (
    QPushButton,
    QLineEdit,
    QCheckBox,
    QHBoxLayout,
    QWidget,
)

from iv_lab_controller.store import Store, Observer
from iv_lab_controller.types import RunnerState

from ..types import ApplicationState, HardwareState

        
class PlotHeaderWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.register_connections()
        self.init_observers()

    def init_ui(self):
        # cell name
        cn_regex = QRegularExpression(r"[a-zA-Z\d\s\-_]{1,255}")
        cn_validator = QRegularExpressionValidator(cn_regex)
        self.in_cell_name = QLineEdit()
        self.in_cell_name.setValidator(cn_validator)
        self.in_cell_name.setPlaceholderText('Enter Cell Name Here...')
        self.in_cell_name.setMinimumWidth(500)
        self.in_cell_name.setEnabled(False)
        
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
