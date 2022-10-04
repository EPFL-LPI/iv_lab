import os
from datetime import datetime
from typing import Dict, List

from .lamp import Lamp
from .smu import SMU
from .system_parameters import SystemParameters
from .experiment import Experiment
from ..user import Permission

class System:
    """
    Represents an IV system.
    An IV System consists of
    + A `Lamp` controller
    + A `SMU`controller
    + System parameters describing the system
    + Procedures the system can run.
    """
    def __init__(
        self,
        lamp: Lamp,
        smu: SMU,
        system_parameters: SystemParameters,
        emulate: bool = False
    ):
        """
        :param emulate: Run in emulation mode. [Default: False]
        """
        self._lamp = lamp
        self._smu = smu
        self._system_parameters = system_parameters
        self._emulate = emulate

        self._experiments: Dict[Permission, List[Experiment]] = {}
        for perm in Permission:
            self._experiments[perm] = []

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
    def experiments(self) -> Dict[Permission, List[Experiment]]:
        """
        :returns: Dictionary of permission-experiments pairs.
        """
        return self._experiments

    def add_experiment(self, permission: Permission, experiment: Experiment):
        """
        Adds an experiment for the gievn permission.
        """
        self._experiments[permission].append(experiment)

    def experiments_for_permission(self, perm: Permission) -> List[Experiment]:
        """
        :param perm: Desired Permission.
        :returns: List of Experiments available to the given permission.
        """
        return self._experiments[perm]

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

    def toggleAutoSave(self,autoSave):
        self.saveDataAutomatic = autoSave
    
    # @todo
    def save_calibration_to_system_settings(self, calibration_params):
        dateTimeString = datetime.datetime.now().strftime("%c") #"%Y%m%d_%H%M%S")
        self.parameters.IVsys['fullSunReferenceCurrent'] = calibration_params['reference_current']
        self.smu.fullSunReferenceCurrent = calibration_params['reference_current']
        self.parameters.IVsys['calibrationDateTime'] = dateTimeString
        self.smu.calibrationDateTime = dateTimeString
        settingsFilePath = os.path.join(os.getcwd() , "system_settings.json")
        sys_params = {}
        sys_params['computer'] = self.parameters.computer
        sys_params['IVsys'] = self.parameters.IVsys
        sys_params['lamp'] = self.parameters.lamp
        sys_params['SMU'] = self.parameters.SMU
        with open(settingsFilePath, 'w') as outfile:
            json.dump(sys_params, outfile)                        

