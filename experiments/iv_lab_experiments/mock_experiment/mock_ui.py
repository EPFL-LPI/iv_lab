from PyQt6.QtWidgets import (
    QLabel,
    QSpinBox,
    QVBoxLayout,
    QCheckBox,
    QGridLayout
)

from .mock_parameters import MockExperimentParameters

from iv_lab_controller.base_classes import ExperimentParametersWidget


class MockParametersWidget(ExperimentParametersWidget):
    """
    Measurement parameters for a Mock procedure.
    """
    def __init__(self):
        super().__init__()

        self.setMaximumWidth(300)

    def init_params_ui(self, lo_main: QVBoxLayout):
        """
        Initialize parameters UI.
        """
        self.cb_log = QCheckBox("Log")

        lbl_iterations = QLabel("Iterations")
        self.sb_iterations = QSpinBox()
        self.sb_iterations.setMinimum(0)
        self.sb_iterations.setMaximum(100)

        # layout
        lo_params = QGridLayout()
        lo_params.addWidget(self.cb_log, 0, 0)

        lo_params.addWidget(lbl_iterations, 1, 0)
        lo_params.addWidget(self.sb_iterations, 1, 1)
       
        lo_main.addLayout(lo_params)
        self.reset_fields()

    @property
    def value(self) -> MockExperimentParameters:
        """
        :reutrns: Values of the measurement parameters.
        """

        params = MockExperimentParameters()
        params.log = self.cb_log.isChecked()
        params.iterations = self.sb_iterations.value()
        return params

    def reset_fields(self):
        """
        Reset field values to default.
        """
        self.cb_log.setChecked(False)
        self.sb_iterations.setValue(0)
