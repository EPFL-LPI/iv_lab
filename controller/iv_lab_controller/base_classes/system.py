import os
from datetime import datetime
from typing import Union, Dict, List, Callable, Type
from enum import Enum

from .lamp import Lamp
from .smu import SMU
from .system_parameters import SystemParameters
from .experiment import Experiment
from ..user import Permission

class ReferenceDiodeState(Enum):
    """
    InSeries: Used mainly for single channel SMUs where reference cell is measured before and/or after test cell on the same channel
    InParallel: Only works with multi channel SMUs, reference cell is measured in parallel with test cell on a different channel  
    """
    NotPresent = 0
    InSeries = 1
    InParallel = 2

ProcedureFunction = Callable[[], None]


class ProcedureFunctions:
    """
    Functions used by the `System` in an `Experiment`'s `Procedure`
    for `System` specific initialization of the `Procedure`.
    This is injectected into the `Procedure` as an instance variable.

    # See also
    + `iv_lab_controller.base_classes.procedure.Procedure`
    """
    def __init__(
        self,
        startup: Union[ProcedureFunction, None] = None,
        shutdown: Union[ProcedureFunction, None] = None
    ):
        """
        :param startup: Function to be run in `Procedure`'s `startup` method, or `None`.
        :param shutdown: Function to be run in `Procedure`'s `shutdown` method, or `None`.
        """
        def _default_fcn():
            """
            Does nothing.
            """
            pass

        if startup is None:
            startup = _default_fcn

        if shutdown is None:
            shutdown = _default_fcn

        self.startup = startup
        self.shutdown = shutdown


class System:
    """
    Represents an IV system.
    An IV System consists of
    + A `Lamp` controller
    + A `SMU`controller
    + System parameters describing the system
    + State of the reference diode
    + Procedures the system can run
    """
    def __init__(
        self,
        lamp: Lamp,
        smu: SMU,
        system_parameters: SystemParameters,
        reference_diode_state: ReferenceDiodeState,
        emulate: bool = False
    ):
        """
        :param emulate: Run in emulation mode. [Default: False]
        """
        self._lamp = lamp
        self._smu = smu
        self._system_parameters = system_parameters
        self._reference_diode_state = reference_diode_state
        self._emulate = emulate

        self._experiments: Dict[Permission, List[Type[Experiment]]] = {}
        for perm in Permission:
            self._experiments[perm] = []

        # setup procedure functions
        self.procedure_functions: Dict[Type[Experiment], ProcedureFunctions] = {}

    @property
    def emulate(self) -> bool:
        """
        :returns: If the system is running in emulation mode.
        """
        return self._emulate

    @property
    def lamp(self) -> Lamp:
        """
        :returns: The System's lamp controller.
        """
        return self._lamp

    @property
    def smu(self) -> SMU:
        """
        :returns: The System's SMU controller.
        """
        return self._smu

    @property
    def system_parameters(self) -> SystemParameters:
        """
        :returns: The system's config parameters.
        """
        return self._system_parameters

    @property
    def reference_diode_state(self) -> ReferenceDiodeState:
        """
        State of the reference diode (NotPresent, InSeries, InParallel)

        :returns: State of reference diode.
        """
        return self._reference_diode_state

    @property
    def experiments(self) -> Dict[Permission, List[Type[Experiment]]]:
        """
        :returns: Dictionary of permission-experiments pairs.
        """
        return self._experiments

    def add_experiment(self, permission: Permission, experiment: Type[Experiment]):
        """
        Adds an experiment for the gievn permission.

        :param permission: The permission to add the experiment to.
        :param experiment: The experiment to add.
        """
        self._experiments[permission].append(experiment)

    def experiments_for_permission(self, perm: Permission) -> List[Type[Experiment]]:
        """
        :param perm: Desired Permission.
        :returns: List of Experiments available to the given permission.
        """
        return self._experiments[perm]

    def set_procedure_functions(
        self,
        exp: Type[Experiment],
        startup: Union[ProcedureFunction, None] = None,
        shutdown: Union[ProcedureFunction, None] = None
    ):
        """
        Creates a `ProcedureFunctions` with the given startup and shutdown methods,
        and sets it for the given experiment.

        :parm exp: The `Experiment` to set the procedure functions for.
        :param startup: The startup function.
        :param shutdown: The shutdown function.
        """
        proc_fns = ProcedureFunctions(startup=startup, shutdown=shutdown)
        self.procedure_functions[exp] = proc_fns

    def procedure_functions_for_experiment(self, exp: Type[Experiment]) -> ProcedureFunctions:
        """
        :returns: `ProcedureFunctions` for the given experiment type, or
            a default `ProcedureFunctions` if not set.
        """
        return (
            self.procedure_functions[exp]
            if exp in self.procedure_functions else
            ProcedureFunctions()
        )

    def connect(self):
        """
        Connect to and initialize hardware.
        """
        self.smu.connect()
        self.lamp.connect()

    def disconnect(self):
        """
        Disconnect from hardware.
        """
        self.smu.disconnect()
        self.lamp.disconnect()

    def shutdown(self):
        """
        Shutdown the system.
        """
        self.smu.shutdown()
        self.lamp.shutdown()

    def lamp_on(self):
        """
        Turn lamp on.
        """
        self.lamp.light_on()

    def lamp_off(self):
        """
        Turn lamp off..
        """
        self.lamp.light_off()

    def measure_light_intensity(self):
        raise NotImplementedError()

    def calibrate(self):
        """
        """
        NotImplementedError()

    def toggleAutoSave(self, autoSave):
        self.saveDataAutomatic = autoSave

    # @todo
    def save_calibration_to_system_settings(self, calibration_params):
        dateTimeString = datetime.datetime.now().strftime("%c")  # "%Y%m%d_%H%M%S")
        self.parameters.IVsys['fullSunReferenceCurrent'] = calibration_params['reference_current']
        self.smu.fullSunReferenceCurrent = calibration_params['reference_current']
        self.parameters.IVsys['calibrationDateTime'] = dateTimeString
        self.smu.calibrationDateTime = dateTimeString
        settingsFilePath = os.path.join(os.getcwd(), "system_settings.json")
        sys_params = {}
        sys_params['computer'] = self.parameters.computer
        sys_params['IVsys'] = self.parameters.IVsys
        sys_params['lamp'] = self.parameters.lamp
        sys_params['SMU'] = self.parameters.SMU
        with open(settingsFilePath, 'w') as outfile:
            json.dump(sys_params, outfile)
