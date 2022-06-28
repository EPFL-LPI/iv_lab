from PyQt5.QtCore import (
    QSettings,
)

from PyQt5.QtWidgets import (
    QMenuBar,
    QWidget
)

from iv_lab_controller import controller as GuiCtrl


class IVLabInterface(QWidget):
    """
    Main desktop interface for EPFL LPI IV Lab.
    """

    # --- window close ---
    def closeEvent(self, event):
        self.__delete_controller()
        event.accept()

    def __del__(self):
        self.__delete_controller()

    def __init__(
        self,
        main_window=None,
        resources='resources/base',
        debug=False
    ):
        """
        :param main_window: QMainWindow of application.
        :param resources: Path to static app resources.
        :param debug: Debug mode. [Defualt: False]
        """
        super().__init__()
        self.__debug = debug

        # --- instance variables ---
        # self.window = None
        self.settings = QSettings()
        self._app_resources = resources

        # --- init UI ---
        self.init_window(main_window)
        self.init_ui()
        self.register_connections()

    @property
    def debug(self):
        """
        :returns: Debug mode.
        """
        return self.__debug

    def init_window(self, window):
        """
        :param window: QWindow to initialize.
        """
        self.window = window
        self.window.setGeometry(100, 100, 1000, 600)
        self.window.setWindowTitle('IV Lab')

        mb_main = QMenuBar()
        self.window.setMenuBar(mb_main)

        # edit menu
        mn_edit = mb_main.addMenu('Edit')

    def init_ui(self):
        """
        Initialize UI.
        """
        pass

    def register_connections(self):
        """
        Register top level connections.
        """
        pass

    def __delete_controller(self):
        """
        Delete GUI controller.
        """
        pass
