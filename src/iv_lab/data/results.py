"""Result containers for the measurement types.

Lightweight dataclasses replacing the legacy ad-hoc dictionaries in
``IVLab/IVlab.py`` (``IV_Results``/``data_IV``, ``CV_Results``/``data_CV``,
``CC_Results``/``data_CC``, ``MPP_Results``/``data_MPP`` and the reference
diode calibration data).

Naming convention:

- Scalar parameters and photovoltaic metrics keep the exact legacy key
  spelling (``start_V``, ``dV``, ``Voc``, ``Jsc``, ``FF``, ``Nwire``, ...)
  so that ``data/file_writer.py`` can later reproduce the legacy file
  format by direct field lookup.
- Data arrays get descriptive names; the legacy ``data_*`` keys were
  ``t`` (time), ``v`` (voltage), ``i`` (current) and ``i_ref``
  (reference diode current).

Arrays are stored as passed in (list or numpy array); no copies are made.
This module is dependency-light by design: standard library only, no GUI,
hardware, file-writing, or analysis imports.

The ``metadata`` dict carries any extra legacy metadata (e.g. system name,
calibration date, user) that the file writer needs to preserve but that has
no dedicated field.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional, Sequence, Union

#: Legacy units: voltages in V, currents in A, time in s, active area in cm².
Array = Sequence[float]


@dataclass
class MeasurementResult:
    """Fields common to all measurement types.

    Mirrors the keys shared by all legacy ``*_Results`` dictionaries.
    """

    #: Legacy ``scanType`` tag ('JV', 'CV', 'CC', 'MPP'); set per subclass.
    scan_type: str = ""
    #: Measurement start time, legacy formatted string (``data_*['start_time']``).
    start_time: Optional[str] = None
    cell_name: Optional[str] = None
    #: Active cell area in cm².
    active_area: Optional[float] = None
    #: Requested light intensity in percent of one sun (``light_int``).
    light_int: Optional[float] = None
    #: Measured light intensity in percent of one sun (``light_int_meas``).
    light_int_meas: Optional[float] = None
    #: Sense wiring, 2 or 4 (legacy ``Nwire``).
    Nwire: Optional[int] = None
    #: Extra legacy metadata preserved for the file writer.
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class IVResults(MeasurementResult):
    """J-V scan result (legacy ``IV_Results`` and ``data_IV``)."""

    scan_type: str = "JV"

    # scan parameters (legacy key spelling)
    start_V: Optional[Union[float, str]] = None  # may be 'Voc' in legacy
    stop_V: Optional[Union[float, str]] = None  # may be 'Voc' in legacy
    dV: Optional[float] = None
    sweep_rate: Optional[float] = None
    Imax: Optional[float] = None
    Dwell: Optional[float] = None

    # data arrays (legacy data_IV['v'], ['i'], ['i_ref'])
    voltage: Array = field(default_factory=list)
    current: Array = field(default_factory=list)
    current_reference: Optional[Array] = None

    # photovoltaic metrics (legacy key spelling)
    Voc: Optional[float] = None
    Jsc: Optional[float] = None
    Vmpp: Optional[float] = None
    Jmpp: Optional[float] = None
    Pmpp: Optional[float] = None
    PCE: Optional[float] = None
    FF: Optional[float] = None


@dataclass
class ConstantVoltageResults(MeasurementResult):
    """Constant-voltage, measure-current result (legacy ``CV_Results`` and
    ``data_CV``)."""

    scan_type: str = "CV"

    set_voltage: Optional[float] = None
    interval: Optional[float] = None
    duration: Optional[float] = None

    # data arrays (legacy data_CV['t'], ['v'], ['i'], ['i_ref'])
    time: Array = field(default_factory=list)
    voltage: Array = field(default_factory=list)
    current: Array = field(default_factory=list)
    current_reference: Optional[Array] = None


@dataclass
class ConstantCurrentResults(MeasurementResult):
    """Constant-current, measure-voltage result (legacy ``CC_Results`` and
    ``data_CC``; the legacy data dict has no reference diode array)."""

    scan_type: str = "CC"

    set_current: Optional[float] = None
    interval: Optional[float] = None
    duration: Optional[float] = None

    # data arrays (legacy data_CC['t'], ['v'], ['i'])
    time: Array = field(default_factory=list)
    voltage: Array = field(default_factory=list)
    current: Array = field(default_factory=list)
    current_reference: Optional[Array] = None


@dataclass
class MPPResults(MeasurementResult):
    """Maximum-power-point tracking result (legacy ``MPP_Results`` and
    ``data_MPP``)."""

    scan_type: str = "MPP"

    #: Legacy ``start_voltage``; may be 'auto' to start from a J-V scan.
    start_voltage: Optional[Union[float, str]] = None
    interval: Optional[float] = None
    duration: Optional[float] = None

    # data arrays (legacy data_MPP['t'], ['v'], ['i'], ['i_ref'])
    time: Array = field(default_factory=list)
    voltage: Array = field(default_factory=list)
    current: Array = field(default_factory=list)
    current_reference: Optional[Array] = None


@dataclass
class CalibrationResults(MeasurementResult):
    """Reference diode calibration result (legacy
    ``run_reference_diode_calibration`` / ``measure_reference_calibration``).

    The legacy routine records cell and reference diode current traces and
    derives the full-sun reference current; the user then saves it to the
    ``IVsys.fullSunReferenceCurrent`` setting together with a new
    ``calibrationDateTime``.
    """

    scan_type: str = "Calibration"

    interval: Optional[float] = None
    duration: Optional[float] = None

    # data arrays (time, cell/diode current, reference diode current)
    time: Array = field(default_factory=list)
    current: Array = field(default_factory=list)
    current_reference: Optional[Array] = None

    #: Derived full-sun reference current in A (``fullSunReferenceCurrent``).
    reference_current: Optional[float] = None
    #: Legacy formatted calibration date string (``calibrationDateTime``).
    calibration_datetime: Optional[str] = None
