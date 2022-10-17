import time

import numpy as np
from pymeasure.experiment import (
    FloatParameter,
    BooleanParameter,
)

from iv_lab_controller.base_classes.procedure import Procedure


class IVCurveProcedure(Procedure):
    """
    IV curve sweep.
    """
    DATA_COLUMNS = ['time elapsed', 'voltage', 'current', 'reference current']

    automatic_limits = BooleanParameter(
        'Automatic limits',
        default=False
    )

    compliance_current = FloatParameter(
        'Compliance current',
        units='A',
        default=0.05
    )

    start_voltage = FloatParameter(
        'Start voltage',
        units='V',
        default=0
    )

    stop_voltage = FloatParameter(
        'Stop voltage',
        units='V',
        default=1
    )

    voltage_step = FloatParameter(
        'Voltage step',
        units='V',
        minimum=0,
        default=0.01
    )

    sweep_rate = FloatParameter(
        'Sweep rate',
        units='V/s',
        minimum=0,
        default=0.1
    )

    settling_time = FloatParameter(
        'Settling time',
        units='s',
        minimum=0,
        default=0.1
    )

    check_polarity = BooleanParameter(
        'Check polarity',
        default=False
    )

    def validate_parameters(self) -> bool:
        """
        :returns: `True` if all parameters and parameter combinations are valid.
        :raises ValueError: If a parameter or combination of parameters are
        invalid.
        """
        if abs(self.start_voltage) > self.compliance_voltage:
            raise ValueError('Start voltage larger than compliance voltage')

        if abs(self.stop_voltage) > self.compliance_voltage:
            raise ValueError('End voltage larger than compliance voltage')

        return True

    def startup(self):
        """
        Validate parameters, initialize hardware, and perform inital checks.
        """
        self.validate_parameters()

        # initialize smu
        self.smu.reset()
        self.smu.compliance_voltage = self.compliance_voltage
        self.smu.compliance_current = self.compliance_current
        self.smu.measure_current()

        # initialize lamp
        # self.status.emit('status', 'Turning lamp on...')
        self.lamp.intensity = self.light_intensity
        self.lamp.light_on()

        # measure light intensity on the reference diode if configured
        if False: # self.smu.use_reference_diode:
            ref_intensity = self.measure_light_intensity()
            intensity_err = abs(ref_intensity - self.light_intensity)/ self.light_intensity
            if intensity_err > self.light_intensity_error:
                raise ValueError (
                    'Light level measured by reference diode is more than' +
                    f'{self.light_intensity_error}% off from targe.\nAborting Scan'
                )

        # check Voc polarity only when light is on
        if self.check_polarity and self.light_intensity > 0:
            self.show_status('status', 'Checking Voc Polarity...')

            # @todo: check this smu function
            polarity_ok = self.smu.checkVOCPolarity(IV_param)
            if not polarity_ok:
                raise ValueError(
                    'Incorrect polarity detected.' +
                    'This could be due to wires plugged incorrectly or light source not turning on.'
                )
         
    def shutdown(self):
        """
        Place hardware in standby.
        """
        self.emit('status', 'Turning lamp off...')
        self.lamp.turn_off()

    def execute(self):
        """
        Runs an IV curve sweep.
        """
        self.emit('status', 'Running JV Scan...')

        # create voltages
        step = (
            self.voltage_step
            if self.start_voltage < self.stop_voltage else
            -self.voltage_step
        )
        stop_voltage = self.stop_voltage + step
        voltages = np.arange(self.start_voltage, stop_voltage, step)

        self.smu.enable_output()

        start_time = time.time()
        for v in voltages:
            if self.should_stop():
                self.emit('status', 'Aborting experiment...')
                break

            # measure current at voltage, save result
            self.smu.set_voltage(v)
            current = self.smu.current
            elapsed_time = time.time() - start_time
            data = {
                'time elapsed': elapsed_time,
                'voltage': v,
                'current': current,
                'reference current': 0
            }

            # if False: # self.use_reference_diode:
            #     if self.smu.referenceDiodeParallel: # light level was measured real-time during scan
            #         avgRefCurrent = sum(i_ref)/len(i_ref)
            #         avgLightLevel = abs(100. * avgRefCurrent / self.smu.fullSunReferenceCurrent)
            #         if self.app != None:
            #             self.win.updateMeasuredLightIntensity(avgLightLevel)
            #             self.app.processEvents()
            #         lightLevelCorrectionFactor = IV_param['light_int'] / avgLightLevel
            #     else: #light level was only measured once at the beginning
            #         avgLightLevel = lightIntensity
            #         lightLevelCorrectionFactor = IV_param['light_int'] / avgLightLevel
            # else:
            #     lightLevelCorrectionFactor = 1.0
            #     avgLightLevel = IV_param['light_int']

            self.emit('results', data)

            # if len(v_smu) > 1:
            #     self.IV_Results = {}
            #     self.IV_Results['active_area'] = IV_param['active_area']
            #     self.IV_Results['cell_name'] = IV_param['cell_name']
            #     self.IV_Results['light_int'] = IV_param['light_int']
            #     if self.smu.useReferenceDiode:
            #         self.IV_Results['light_int_meas'] = IV_param['light_int']/lightLevelCorrectionFactor
            #     self.IV_Results['Imax'] = IV_param['Imax']
            #     self.IV_Results['Dwell'] = IV_param['Dwell']
            #     
            #     if IV_param['light_int'] > 0 and not self.abortRunFlag(): #don't analyze dark or aborted runs
            #         pairs = []
            #         dataJ = []
            #         for v, i in zip(v_smu, i_smu):
            #             pairs.append((v, i * lightLevelCorrectionFactor / IV_param['active_area']))
            #             dataJ.append(i * 1000. * lightLevelCorrectionFactor / IV_param['active_area'])
            #         #update JV plot with data from single-point light level correction.
            #         
            #         if self.win != None:
            #             self.win.updatePlotIV(v_smu,dataJ)
            #             
            #         jvData = np.array(pairs)
            #         df = pd.DataFrame(jvData)
            #         metrics = [ 'voltage', 'current' ]
            #         header = pd.MultiIndex.from_product( [ [ IV_param['cell_name'] ], metrics ], names = [ 'sample', 'metrics' ]  )
            #         df.columns = header
            #         
            #         df.index = df.xs( 'voltage', level = 'metrics', axis = 1 ).values.flatten()
            #         df.drop( 'voltage', level = 'metrics', axis = 1, inplace = True )
            #         df.columns = df.columns.droplevel( 'metrics' )

            #         jv_metrics = bric_jv.get_metrics(df, generator=False)
            #         #print(jv_metrics)
            #         
            #         self.IV_Results['Voc'] = float(jv_metrics['voc'])
            #         self.IV_Results['Jsc'] = float(jv_metrics['jsc'])*1000.
            #         self.IV_Results['Vmpp'] = float(jv_metrics['vmpp'])
            #         self.IV_Results['Jmpp'] = float(jv_metrics['jmpp'])*1000.
            #         self.IV_Results['Pmpp'] = abs(float(jv_metrics['pmpp'])*1000.)
            #         self.IV_Results['PCE'] = 100. * abs(float(jv_metrics['pmpp'])*1000.) / avgLightLevel #IV_param['light_int'] #percent
            #         self.IV_Results['FF'] = float(jv_metrics['ff'])
            #             
            #     #use actual voltage start and stop values for datafile.
            #     #important in case of 0-Voc scanning, or scan abort
            #     if len(v_smu) > 0:
            #         self.IV_Results['start_V'] = v_smu[0]
            #         self.IV_Results['stop_V'] = v_smu[len(v_smu)-1]
            #     else:
            #         self.IV_Results['start_V'] = IV_param['start_V']
            #         self.IV_Results['stop_V'] = IV_param['stop_V']
            #     self.IV_Results['dV'] = IV_param['dV']
            #     self.IV_Results['sweep_rate'] = IV_param['sweep_rate']
