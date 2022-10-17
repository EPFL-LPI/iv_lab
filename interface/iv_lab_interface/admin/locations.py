from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication,
    QStyle,
    QMessageBox,
    QDialog,
    QPushButton,
    QFileDialog,
    QVBoxLayout,
    QLabel,
    QHBoxLayout
)


from iv_lab_controller import gui as ctrl
from iv_lab_controller import common as ctrl_common

from .. import common


class ApplicationLocationsDialog(QDialog):
    """
    Dialog showing important application directory and file locations.
    """
    def __init__(self):
        super().__init__()

        self.setWindowTitle('Application Locations')
        self.init_ui()
        self.register_connections()

    def init_ui(self):
        # app data
        lbl_app_title = QLabel('Application data folder:')
        lbl_app_location = QLabel(ctrl_common.app_data_directory())
        lbl_app_location.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )

        # --- open app data folder
        qstyle = QApplication.style()
        self.btn_open_app_folder = QPushButton(
            qstyle.standardIcon(QStyle.StandardPixmap.SP_DirIcon),
            ''
        )

        lo_app_dir = QHBoxLayout()
        lo_app_dir.addWidget(lbl_app_title)
        lo_app_dir.addWidget(lbl_app_location)
        lo_app_dir.addWidget(self.btn_open_app_folder)

        # measurement data
        lbl_data_dir_title = QLabel('Meaurement data folder:')
        self.lbl_data_dir = QLabel(ctrl_common.data_directory())
        self.lbl_data_dir.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )

        self.btn_change_data_directory = QPushButton('Change')
        lo_data_dir = QHBoxLayout()
        lo_data_dir.addWidget(lbl_data_dir_title)
        lo_data_dir.addWidget(self.lbl_data_dir)
        lo_data_dir.addWidget(self.btn_change_data_directory)

        # main
        lo_main = QVBoxLayout()
        lo_main.addLayout(lo_app_dir)
        lo_main.addLayout(lo_data_dir)
        self.setLayout(lo_main)

    def register_connections(self):
        self.btn_open_app_folder.clicked.connect(self.open_app_data_dir)
        self.btn_change_data_directory.clicked.connect(self.set_data_directory)

    def open_app_data_dir(self):
        """
        Opens the application data directory.
        """
        ctrl.open_path(ctrl_common.app_data_directory())

    def set_data_directory(self):
        """
        Sets the data directory to a new, user-specified path.
        """
        data_path = QFileDialog.getExistingDirectory()
        if not data_path:
            return

        try:
            ctrl_common.set_data_directory(data_path)

        except Exception as err:
            common.show_message_box(
                'Error saving data directory',
                f'An error occured while saving the data directory\n{err}',
                icon=QMessageBox.Icon.Critical
            )
            return

        self.lbl_data_dir.setText(data_path)
