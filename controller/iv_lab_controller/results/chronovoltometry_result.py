from typing import List

from ..base_classes.result import Result



class ChronovoltometryResult(Result):
	"""
	Results from a chronovoltometry experiment.
	"""
	def header(self) -> List[str]:
		"""
		:returns: List of header strings.
		"""
		header = self._default_header()
		headr += [
		    f'Set Current,{IV_Results['set_current']},A',
            f'Measurement Interval,{IV_Results['interval']},sec',
            f'Measurement Duration,{IV_Results['duration'] },sec',
            'Constant Current Results',
            'Time(s),Voltage(V),Current(A)'
        ]

        return header
