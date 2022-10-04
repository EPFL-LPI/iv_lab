import os
from typing import List, Union

import matplotlib.pyplot as plt

from ..base_classes.result import Result
from .iv_curve_parameters import IVCurveParameters
from .cell_parameters import CellParameters


class IVCurveSummary():
    """
    Summary results of an IV Curve.
    """
    def __init__(self):
        self.j_sc: Union[float, None] = None
        self.v_oc: Union[float, None] = None
        self.ff: Union[float, None] = None
        self.pce: Union[float, None] = None
        self.j_mpp: Union[float, None] = None
        self.v_mpp: Union[float, None] = None
        self.p_mpp: Union[float, None] = None

    def to_csv(self) -> List[str]:
        """
        :returns: Data as a list of CSV lines.
        """
        csv: List[str] = []
        if self.j_sc is not None:
            csv.append(f'Jsc,{self.j_sc},mA/cm^2')
        
        if self.v_oc is not None:
            csv.append(f'Voc,{self.v_oc},V')
        
        if self.ff is not None:
            csv.append(f"Fill Factor,{self.ff},")
        
        if self.pce is not None:
            csv.append(f'PCE,{self.pce},%')
        
        if self.j_mpp is not None:
            csv.append(f'Jmpp,{self.j_mpp},mA/cm^2')
        
        if self.v_mpp is not None:
            csv.append(f'Vmpp,{self.v_mpp},V')
        
        if self.p_mpp is not None:
            csv.append(f'Pmpp,{self.p_mpp},mW/cm^2')

        return csv


class IVCurveResult(Result):
    """
    Results from an IV scan.
    """
    def __init__(self):
        self.experiment_parameters: Union[IVCurveParameters, None] = None
        self.summary = IVCurveSummary()
        self.cell_parameters = CellParameters()
        
    def header(self) -> List[str]:
        """
        :returns: Header for IV scan.
        """
        header = self._default_header()

        # parameters
        header += [     
            f'Min Voltage,{self.parameters.min_voltage},V',
            f'Max Voltage,{self.parameters.max_voltage},V',
            f'Voltage Step,{self.parameters.voltage_step},V',
            f'Sweep Rate,{self.parameters.sweep_rate},V/sec',
            f'Direction,{self.parameters.direction.value},'
            "J-V Results"
        ]

        # summary
        header += self.summary.to_csv()
       
        # data header
        if self.SMU.useReferenceDiode:
            header.append('Voltage(V),Normalized Current(A),Raw Current(A),light intensity (mW/cm^2)')
        
        else:
            header.append('Voltage(V),Current(A)')

        return header


    def save_pdf(self, file: Union[str, None]):
        """
        Save results as a PDF.

        :param file: File path to save to, or None to use default.
            [Default: None]
        """
        A4SizeY = 8.25 #inches, for A4
        A4SizeX = 11.75 #inches, for A4
        
        # @todo: add logo to data
        # load EPFL logo png file
        basepath, _ = os.path.split(os.getcwd())
        logoPath = os.path.join(basepath,"IVLab Accessories","EPFL_Logo.png")
        logo = plt.imread(logoPath)

        dataJ = []
        if self.SMU.useReferenceDiode:
            for i in data["i"]:
                #i_corr = i * IV_Results["light_int'] / IV_Results['light_int_meas"]
                i_corr = i
                dataJ.append(i_corr*1000./self.cell.active_area)
        else:
            for i in data["i"]:
                dataJ.append(i*1000./self.cell.active_area)
        
        #make plot of JV curve
        fig = plt.figure(figsize=(A4SizeX,A4SizeY))
        ax1 = fig.add_axes([0.5,0.4,0.4,0.4]) #x, y, width, height
        ax1.invert_yaxis()
        ax1.set_ylabel("Current density [mA/$cm^2$]")
        ax1.set_xlabel("Voltage [V]")
        ax1.grid(visible=True)
        ax1.axhline(color = 'k') #solid black line across x-axis at y=0
        ax1.plot(data["v"], dataJ, color='red')

        #report header - EPFL logo and cell name
        ax2 = fig.add_axes([0.04,0.80,0.15,0.15])
        ax2.axis('off')
        ax2.imshow(logo)

        #figtext is set relative to the figure.  'text' would be relative to an axis.
        headerText = "Cell Name: " + self.parameters.cell_name;
        plt.figtext(0.20, 0.85, headerText, weight='bold', fontsize=12, ha='left') #, rotation=15, wrap=True)

        #couldn't find a clean and simple way to print tabular text onto a figure that preserves all the spacings correctly.
        #fill the data into a list of tuples with each tuple containing title, data, and unit strings.
        #then print everything out with a specified spacing.

        #coordinates of run param text columns
        rpX1 = 0.05
        rpX2 = 0.19
        rpY = 0.8
        rpSpace = 0.0225
        params_text = []
        params_text.append(("Measurement Date",dateTimeString, ""))
        params_text.append(("Cell Active Area",str(self.parameters.active_area)," $cm^2$"))
        params_text.append(("Light Source",self.parameters.lamp["brand'] + " ",self.parameters.lamp['model"]))
        if self.SMU.useReferenceDiode:
            params_text.append(("Reference Calibration","{:6.4f}".format(self.SMU.fullSunReferenceCurrent*1000.), " mA"))
            params_text.append(("Calibration Date", self.SMU.calibrationDateTime, ""))
        
        if len(dataFileName) < 35 :
            params_text.append(("Data File Name",dataFileName,""))
        else: # wrap text every 35 characters
            params_text.append(("Data File Name",dataFileName[0:30],""))
            dataFileNameWrap = dataFileName[30:]
            while len(dataFileNameWrap) > 35 :
                params_text.append(("",dataFileNameWrap[0:30],""))
                dataFileNameWrap = dataFileNameWrap[30:]
            #print out the remaining text
            params_text.append(("",dataFileNameWrap,""))
                
        params_text.append(("Current Compliance",str(IV_Results["Imax"]*1000.)," mA"))
        #params_text.append(("Settling Time","{:5.3f}".format(IV_Results["dV']/IV_Results['sweep_rate"])," s"))
        params_text.append(("Sweep rate",f'{IV_Results["sweep_rate"]*1000:.1f}'," mV/s"))
        params_text.append(("Voltage step",str(IV_Results["dV"])," V"))
        params_text.append(("Meas. Delay",str(IV_Results["Dwell"])," s"))
        for label, data, units in params_text:
            plt.figtext(rpX1, rpY, label, fontsize=10, ha='left')
            plt.figtext(rpX2, rpY, ": " + data + units, fontsize=10, ha='left')
            rpY -= rpSpace

        rtX1 = 0.05
        rtX2 = 0.19
        rtY = 0.45
        rtSpace = 0.0225
        results_text = []
        results_text.append(("Nominal Light Intensity",str(IV_Results["light_int"])," mW/$cm^2$"))
        nominalLightIntensityString = str(IV_Results["light_int"]) + " mW/$cm^2$"
        if 'light_int_meas' in IV_Results:
            results_text.append(("Measured Intensity","{:6.2f}".format(IV_Results["light_int_meas"])," mW/$cm^2$"))
        if self.j_sc is not None:
            results_text.append(("Jsc","{:5.3f}".format(IV_Results["Jsc"]), " mA/$cm^2$"))
        if 'Voc' in IV_Results:
            results_text.append(("Voc","{:6.4f}".format(IV_Results["Voc"]),"V"))
        if 'FF' in IV_Results:
            results_text.append(("FF","{:6.4f}".format(IV_Results["FF"]),""))
        if 'PCE' in IV_Results:
            results_text.append(("PCE","{:5.2f}".format(IV_Results["PCE"]),"%"))
        if 'Jmpp' in IV_Results:
            results_text.append(("Jmpp","{:5.3f}".format(IV_Results["Jmpp"])," mA/$cm^2$"))
        if 'Vmpp' in IV_Results:
            results_text.append(("Vmpp","{:6.4f}".format(IV_Results["Vmpp"]),"V"))
        if 'Pmpp' in IV_Results:
            results_text.append(("Pmpp","{:7.3f}".format(IV_Results["Pmpp"])," mW/$cm^2$"))
            
        for label, data, units in results_text:
            plt.figtext(rtX1, rtY, label, fontsize=10, ha='left')
            plt.figtext(rtX2, rtY, ": " + data + units, fontsize=10, ha='left')
            rtY -= rtSpace
            
        # footer - measured by and date
        plt.figtext(0.05,0.05,"Measured by: " + username + " on " + self.parameters.IVsys["sysName"], fontsize = 10, ha = 'left')
        plt.figtext(0.75,0.05,"Date: " + self.time_string, fontsize = 10, ha = 'left')
            
        plt.savefig(file)
