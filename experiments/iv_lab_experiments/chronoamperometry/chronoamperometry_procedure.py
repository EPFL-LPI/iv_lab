import time

from pymeasure.experiment import FloatParameter

from iv_lab_controller.base_classes.procedure import Procedure
 

class ChronoamperometryProcedure(Procedure)
    """
    Chronoamperometry experiment.
    """
    set_voltage = FloatParameter(
        'Set voltage',
        units='V'
    )

    settling_time = FloatParameter(
        'Settling time',
        units='s',
        min=0,
        default=5
    )
    
    duration = FloatParameter(
        'Duration',
        units='s',
        min=0
    )

    interval = FloatParameter(
        'Interval',
        units='s',
        min=0
    )

    def validate_parameters(self) -> bool: 
        """
        :returns: `True` if all parameters and parameter combinations are valid.
        :raises ValueError: If a parameter or combination of parameters are
        invalid.
        """
        if abs(self.set_voltage) > self.compliance_voltage:
            raise ValueError('Set voltage larger than compliance voltage')

        return True


    def startup(self):
        """
        Validate parameters, initialize hardware, and perform inital checks.
        """
        self.validate_parameters()

        # set current and voltage
        self.smu.compliance_voltage = self.compliance_voltage
        self.smu.compliance_current = self.compliance_current
        self.smu.set_voltage(self.set_voltage)

        # initialize lamp
        self.status.emit('status', 'Turning lamp on...')
        self.lamp.intensity = self.light_intensity
        self.light_on()

        # wait for settling time
        time.sleep(self.settling_time)

    def shutdown(self):
        pass

    def execute(self):
        """
        Run a chronoamperometry experiment.
        """
        start_time = time.time()
        end_time = start_time + self.duration
        meas_index = 0
        while time.time() < end_time:
            if self.should_stop():
                break
            
            # wait until next measurement time
            meas_time = meas_index * self.interval + start_time
            wait_time = time.time() - meas_time
            if wait_time > 0:
                time.sleep(wait_time)

            # measure current
            elapsed_time = time.time() - start_time
            current = self.smu.measure_current()
            data = {
                'time': elapsed_time,
                'current': current
            }
            self.emit('results', data)

            meas_index += 1
            complete_perc = elapsed_time / self.duration
            self.emit('status', f'{complete_perc}% complete')
