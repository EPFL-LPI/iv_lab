from iv_lab_controller.base_classes import Experiment

from .iv_curve_procedure import IVCurveProcedure
from .iv_curve_ui import IVCurveParametersWidget
from ..mock_experiment.mock_experiment_plot import MockExperimentPlot

class IVCurve(Experiment):
    """
    IV curve measurement.
    """
    name = "J-V scan"
    procedure = IVCurveProcedure
    ui = IVCurveParametersWidget
    plot = MockExperimentPlot
