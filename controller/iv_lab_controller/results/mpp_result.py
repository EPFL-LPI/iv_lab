from typing import List

from ..base_classes.result import Result


class MPPResult(Result):
    """
    Results from an MPP scan.
    """
    def header(self) -> List[str]:
        """
        :returns: List of header strings.
        """
        header = self._default_header()
        header += [
            f'Start Voltage,{IV_Results['start_voltage']},V',
            f'Measurement Interval,{IV_Results['interval']},sec',
            f'Measurement Duration,{IV_Results['duration'] },sec',
            'Maximum Power Point Results'
        ]

        if self.SMU.useReferenceDiode:
            header.append('Time(s),Voltage(V),Normalized Current(A),Normalized Power(mW/cm2),Raw Current (A)')
        
        else:
            header.append('Time(s),Voltage(V),Current(A),Power(mW/cm2)')

        return header