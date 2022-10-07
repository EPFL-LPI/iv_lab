from iv_lab_controller.base_classes import Experiment

from .mock_procedure import MockProcedure
from .mock_ui import MockParametersWidget
from .mock_experiment_plot import MockExperimentPlot

class MockExperiment(Experiment):
    """
    Mock experiment.
    """
    name = "Mock Experiment"
    procedure = MockProcedure
    ui = MockParametersWidget
    plot = MockExperimentPlot
