import numpy as np
from pymeasure.instruments.keithley import Keithley2400 as Keithley2400Base
from pymeasure.adapters import Adapter

from iv_lab_controller.base_classes.smu import SMU, RangeValue


class Keithley2400(SMU, Keithley2400Base):
    """
    Keithley 2400 controller.
    """
    def __init__(self, adapter: Adapter, **kwargs):
        # copy and remove emulate, if needed
        emulate = False
        if "emulate" in kwargs:
            emulate = kwargs['emulate']
            del kwargs['emulate']

        # initialize smu interface
        SMU.__init__(self, emulate=emulate)

        if not self.emulate:
            Keithley2400Base.__init__(self, adapter, **kwargs)

    @property
    def name(self) -> str:
        """
        :returns: Name of the instrument.
        """
        return "Keithley 2400"

    @property
    def current_range(self) -> RangeValue:
        """
        :returns: Min and max current values.
        """
        return self.source_current_range

    @property
    def voltage_range(self) -> RangeValue:
        """
        :returns: Min and max voltage values.
        """
        return self.source_voltage_range

    def _connect(self):
        pass

    def _disconnect(self):
        if not self.emulate:
            Keithley2400Base.shutdown(self)

    @property
    def compliance_current(self) -> float:
        """
        :returns: Compliance current.
        """
        return Keithley2400Base.compliance_current.fget(self)

    @compliance_current.setter
    def compliance_current(self, i: float):
        """
        Sets the compliance current.

        :param: Desired compliance current.
        """
        Keithley2400Base.compliance_current.fset(self, i)

    @property
    def compliance_voltage(self) -> float:
        """
        :returns: Compliance voltage.
        """
        return Keithley2400Base.compliance_voltage.fget(self)

    @compliance_voltage.setter
    def compliance_voltage(self, v: float):
        """
        Sets the compliance voltage.

        :param v: Desired compliance voltage.
        """
        Keithley2400Base.compliance_voltage.fset(self, v)

    def set_voltage(
        self,
        voltage: float
    ):
        """
        Sets the applied voltage.

        :param voltage: Desired voltage.
        """
        self.source_voltage = voltage

    def set_current(
        self,
        current: float
    ):
        """
        Sets the applied current.

        :param current: Desired current.
        """
        self.source_current = current

    def enable_output(self):
        """
        Enable output.
        """
        self.enable_source()

    def disable_output(self):
        """
        Disable output.
        """
        self.disable_source()

    def measure_voltage(self, **kwargs) -> float:
        """
        Measure the voltage.

        :returns: Measured voltage.
        """
        return Keithley2400Base.measure_voltage(self, **kwargs)

    def measure_current(self, **kwargs) -> float:
        """
        Measure the current.

        :returns: Measured current.
        """
        return Keithley2400Base.measure_current(self, **kwargs)

    def measure_iv_curve(
        self,
        start: float,
        stop: float,
        step: float,
        rate: float,
    ) -> np.array:
        """
        Measure an IV curve.

        :param start: Start voltage.
        :param stop: Stop voltage.
        :param step: Absolute voltage step size.
        :param rate: Scan rate.
        :returns: numpy.array of measured values.
        """
        raise NotImplementedError()

    def measure_iv_point_by_point(
        self,
        start: float,
        stop: float,
        step: float,
        rate: float
    ) -> np.array:
        """
        Measure an IV curve.

        :param start: Start voltage.
        :param stop: Stop voltage.
        :param step: Absolute voltage step size.
        :param rate: Scan rate.
        :returns: numpy.array of measured values.
        """
        raise NotImplementedError()

    def measure_chronopotentiometry(
        self,
        current: float,
        time: float
    ) -> np.array:
        """
        Perform a chronopotentiometry experiment.

        :param current: Set point current.
        :param time: Run time.
        :returns: numpy.array of measured values.
        """
        raise NotImplementedError()

    def measure_chronoampometry(
        self,
        voltage: float,
        time: float
    ) -> np.array:
        """
        Perform a chronoampometry experiment.

        :param voltage: Set point voltage.
        :param time: Run time.
        :returns: numpy.array of measured values.
        """
        raise NotImplementedError()
