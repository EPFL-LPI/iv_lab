from iv_lab_controller.base_classes.experiment import Experiment

from .chronoamperometry_procedure import ChronoamperometryProcedure
from .chronoamperometry_ui import ChronoamperometryParametersWidget

class ChronoamperometryExperiment(Experiment):
    """
    Chronoamperometry experiment.
    """
    name = "Chronoamperometry Experiment"
    procedure = ChronoamperometryProcedure
    ui = ChronoamperometryParametersWidget

