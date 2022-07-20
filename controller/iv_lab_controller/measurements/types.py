from enum import Enum


class MeasurementType(Enum):
	"""
	Types of measurements.
	"""
	IVCurve = 'iv_curve'
	Chronoamperometry = 'chronoamperometry'
	Chronopotentiometry = 'chronopotentiometry'
	MPP = 'mpp'
	Calibration = 'calibration'


class IVSweepDirection(Enum):
	Forward = 'forward'
	Reverse = 'reverse'