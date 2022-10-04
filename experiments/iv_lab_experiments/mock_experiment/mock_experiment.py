from iv_lab_controller.base_classes.experiment import Experiment

from .mock_procedure import MockProcedure
from .mock_ui import MockParametersWidget

class MockExperiment(Experiment):
    """
    Mock experiment.
    """
    name = "Mock Experiment"
    procedure = MockProcedure
    ui = MockParametersWidget
