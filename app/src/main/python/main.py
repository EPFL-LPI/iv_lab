import sys
import argparse

from fbs_runtime.application_context.PyQt5 import ApplicationContext

from PyQt5.QtCore import QCoreApplication
from PyQt5.QtWidgets import QMainWindow

from iv_lab_interface import IVLabInterface


class AppContext(ApplicationContext):
    def run(self, debug=False):
        """
        :param debug: Run in debug mode. [Default: False]
        :returns: Exit code.
        """
        window = QMainWindow()
        interface = IVLabInterface(window, self.get_resource(), debug=debug)

        window.setCentralWidget(interface)
        window.show()

        return self.app.exec_()


def _get_cmdline_parser():
    """
    :returns: argparse.ArgumentParser
    """
    parser = argparse.ArgumentParser(description='IV Lab')
    parser.add_argument('--debug', action='store_true')
    return parser


def _get_args():
    """
    :returns: arparse.NameSpace
    """
    parser = _get_cmdline_parser()
    p_args = parser.parse_args()

    return p_args


if __name__ == '__main__':
    QCoreApplication.setOrganizationName('EPFL LPI')
    QCoreApplication.setOrganizationDomain('epfl.ch/labs/lpi/')
    QCoreApplication.setApplicationName('IV Lab')

    args = _get_args()  # cli arguments
    app = AppContext()
    exit_code = app.run(debug=args.debug)
    sys.exit(exit_code)
