from PyQt6.QtWidgets import (
    QMessageBox,
    QDialog,
    QPushButton,
    QFileDialog,
    QVBoxLayout,
    QLabel,
    QHBoxLayout
)

from iv_lab_controller import common as ctrl

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
        lbl_app_data = QLabel(
            f'Application data folder: {ctrl.app_data_directory()}'
        )

        # measurement data
        lbl_data_dir_title = QLabel('Meaurement data folder:')
        self.lbl_data_dir = QLabel(ctrl.data_directory())

        self.btn_change_data_directory = QPushButton('Change')
        lo_data_dir = QHBoxLayout()
        lo_data_dir.addWidget(lbl_data_dir_title)
        lo_data_dir.addWidget(self.lbl_data_dir)
        lo_data_dir.addWidget(self.btn_change_data_directory)

        # main
        lo_main = QVBoxLayout()
        lo_main.addWidget(lbl_app_data)
        lo_main.addLayout(lo_data_dir)
        self.setLayout(lo_main)

    def register_connections(self):
        self.btn_change_data_directory.clicked.connect(self.set_data_directory)

    def set_data_directory(self):
        data_path = QFileDialog.getExistingDirectory()
        if data_path is None:
            return

        try:
            ctrl.set_data_directory(data_path)

        except Exception as err:
            common.show_message_box(
                'Error saving data directory',
                f'An error occured while saving the data directory\n{err}',
                icon=QMessageBox.Icon.Critical
            )
            return

        self.lbl_data_dir.setText(data_path)
