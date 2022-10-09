import datetime as dt
from typing import Dict, List, Union

import numpy as np
from pymeasure.experiment import Results as PyMeasureResults

from ..user import User
from .. import common
from .experiment_parameters import ExperimentParametersInterface


class Results(PyMeasureResults):
    """
    Results from an experiment.
    """
    @property
    def time_string(self) -> str:
        """
        :returns: Time string if provided by the scan parameteres, or the current time.
        """
        return (
            self.scan_parameters['start_time']
            if ('start_time' in self.scan_parameters) else
            dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        )

#    def header(self) -> List[str]:
#        """
#        :returns: List of header lines.
#        """
#        return self._default_header()

#    def save_csv(self, file: Union[str, None]):
#        """
#        Save result data to the given path.
#
#        :param file: File path to save data to, or None to use default.
#            [Default: None]
#        """
#        if file is None:
#            file = self._default_filename() 
#        
#        header = self.header()        
#        header.append(f'nHeader,{len(header) + 1}')
#
#        out = header
#
#        if data['scanType'] == 'JV':
#            for v,i,ref in zip(data['v'], data['i'], data['i_ref']):
#                if self.SMU.useReferenceDiode:
#                    i_corr = i * IV_Results['light_int'] / IV_Results['light_int_meas']
#                    light_intensity = 100.0 * ref / self.SMU.fullSunReferenceCurrent
#                    fileLine = (str(round(v,12)) + "," + str(round(i_corr,12)) + "," + str(round(i,12)) + "," + str(round(light_intensity,12)) + "\n")
#                else:
#                    fileLine = str(round(v,12)) + "," + str(round(i,12)) + "\n"
#                f.write(fileLine)
#                fileString += fileLine
#
#        elif data['scanType'] == 'CV':
#            for t,v,i_corr,i in zip(data['t'], data['v'], data['i_corr'], data['i']):
#                if self.SMU.useReferenceDiode:
#                    fileLine = str(round(t,6)) + "," + str(round(v,12)) + "," + str(round(i_corr,12)) + "," + str(round(i,12)) + "\n"
#                else:
#                    fileLine = str(round(t,6)) + "," + str(round(v,12)) + "," + str(round(i,12)) + "\n"
#                f.write(fileLine)
#                fileString += fileLine
#
#        elif data['scanType'] == 'CC':
#            for t,v,i in zip(data['t'], data['v'], data['i']):
#                fileLine = str(round(t,6)) + "," + str(round(v,12)) + "," + str(round(i,12)) + "\n"
#                f.write(fileLine)
#                fileString += fileLine
#
#        elif data['scanType'] == 'MPP':
#            for t,v,i_corr,i in zip(data['t'], data['v'], data['i_corr'], data['i']):
#                if self.SMU.useReferenceDiode:
#                    w = abs(i_corr*v*1000./IV_Results['active_area'])
#                    fileLine = str(round(t,6)) + "," + str(round(v,12)) + "," + str(round(i_corr,12)) + "," + str(round(w,12)) + "," + str(round(i,12)) + "\n"
#                else:
#                    w = abs(i*v*1000./IV_Results['active_area'])
#                    fileLine = str(round(t,6)) + "," + str(round(v,12)) + "," + str(round(i,12)) + "," + str(round(w,12)) + "\n"
#                f.write(fileLine)
#                fileString += fileLine
#        
#        f.close()
#        
#        if data['scanType'] == 'JV':
#            self.generate_JV_Results_PDF(data, uname, IV_Results, filename, pdfFilePath)
#        
#        self.show_status("Saved data to: " + dataFilePath)
#        
#        # copy into hidden data path
#        try:
#            basePath, filename = os.path.split(sdFilePath)
#            if (not os.path.exists(basePath)):
#                os.makedirs(basePath)
#            s = open(sdFilePath, "w")
#            s.write(self.scramble_string(fileString)) 
#            s.close()
#
#        except:
#            pass
#
#        out = '\n'.join(out)
#        
#        data_path = os.path.join(common.data_directory(), self.username, filename)
#        basePath, _ = os.path.split(dataFilePath)
#        if not os.path.exists(basePath):
#            os.makedirs(basePath)
#            
#        with open(data_path, "w") as f:
#            f.write(out)
#
#    def _default_filename(self) -> str:
#        """
#        :returns: Default file name for the data.
#            Default path is <cell name>_<scan_type>_<date_time>
#        """
#        cell_name = self.cell_parameters['cell_name']
#
#        scan_type = (
#            self.scan_parameters['scan_type']
#            if ('scan_type' in self.scan_parameters) else
#            'scan'
#        )
#            
#        filename = f'{cell_name}_{scan_type}_{self.time_string}'

    def _default_header(self) -> List[str]:
        """
        :returns: List of header lines describing the system.
        """
        header = [
            f'Measurement System,{self.parameters.IVsys["sysName"]}',
            f'Scan Start Time,{data["start_time"]}',
            f'Sourcemeter Brand,{self.parameters.SMU["brand"]}',
            f'Sourcemeter Model,{self.parameters.SMU["model"]}',
            f'Lamp Brand,{self.parameters.lamp["brand"]}',
            f'Lamp Model,{self.parameters.lamp["model"]}',
            f'Requested Light Intensity,{IV_Results["light_int"]},mW/cm^2'
        ]

        if self.SMU.useReferenceDiode:
            header += [
                f'Measured Light Intensity,{IV_Results["light_int_meas"]},mW/cm^2',
                f'Reference Diode 1sun Current,{self.SMU.fullSunReferenceCurrent*1000},mA',
                f'Reference Diode calibration date,{self.SMU.calibrationDateTime}'
            ]
        
        header.append(f'Cell Active Area,{self.cell_parameters["active_area"]},cm^2')

        return header
