from typing import List

from ..base_classes.result import Result


class ChronoampometryResult(Result):
    """
    Results from a chronoampometry experiment.
    """
    def header(self) -> List[str]:
        """
        :returns: List of header strings.
        """
        header = self._default_header()
        header += [
            f'Set Voltage,{IV_Results['set_voltage']},V',
            f'Measurement Interval,{IV_Results['interval']},sec',
            f'Measurement Duration,{IV_Results['duration'] },sec',
            'Constant Voltage Results'
        ]

        if self.SMU.useReferenceDiode:
            header.append("Time(s),Voltage(V),Normalized Current(A), Raw Current(A)")
        
        else:
            header.append("Time(s),Voltage(V),Current(A)")

        return header
