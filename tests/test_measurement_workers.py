"""Headless tests for the Qt measurement workers.

Signals connected in the same thread are delivered synchronously, so the
workers can be exercised by calling ``run()`` directly — no event loop
or pytest-qt needed; a ``QCoreApplication`` is created once for QtCore.
"""

import inspect
import sys

import pytest
from PySide6.QtCore import QCoreApplication

from iv_lab.config import LampSettings, SMUSettings
from iv_lab.data import (
    CalibrationResults,
    ConstantCurrentResults,
    ConstantVoltageResults,
    IVResults,
    MPPResults,
)
from iv_lab.hardware.lamp.drivers.emulated import EmulatedLamp
from iv_lab.hardware.smu.base import SMUChannel
from iv_lab.hardware.smu.drivers.emulated import EmulatedSMU
from iv_lab.measurements.protocols import (
    CalibrationProtocol,
    ConstantCurrentProtocol,
    ConstantVoltageProtocol,
    IVCurveProtocol,
    MPPTrackingProtocol,
)
from iv_lab.measurements.workers import (
    CalibrationWorker,
    ConstantCurrentWorker,
    ConstantVoltageWorker,
    IVCurveWorker,
    MeasurementWorker,
    MPPTrackingWorker,
)

# QtCore needs an application object; create one for the whole module
_app = QCoreApplication.instance() or QCoreApplication([])


class SignalRecorder:
    """Collects all worker signal emissions."""

    def __init__(self, worker: MeasurementWorker) -> None:
        self.status: list[str] = []
        self.warnings: list[str] = []
        self.data: list[dict] = []
        self.progress: list[int] = []
        self.results: list[object] = []
        self.errors: list[str] = []

        worker.status_update.connect(self.status.append)
        worker.warning_update.connect(self.warnings.append)
        worker.data_ready.connect(self.data.append)
        worker.progress_update.connect(self.progress.append)
        worker.finished.connect(self.results.append)
        worker.error.connect(self.errors.append)


def make_smu(**overrides) -> EmulatedSMU:
    data = {
        "brand": "Keithley",
        "model": "2602",
        "visa_address": "GPIB0::24::INSTR",
        "visa_library": "visa64.dll",
        "emulate": True,
        "useReferenceDiode": False,
    }
    data.update(overrides)
    smu = EmulatedSMU(SMUSettings(**data))
    smu.integration_delay = 0.0
    smu.meas_period_min = 0.0
    smu.full_sun_reference_current = 0.004
    smu.connect()
    return smu


def make_lamp() -> EmulatedLamp:
    lamp = EmulatedLamp(LampSettings(brand="manual", model="manual", emulate=True))
    lamp.connect()
    return lamp


def fake_metrics(voltage, current, active_area, cell_name="cell"):
    from iv_lab.analysis.jv_metrics import JVMetrics

    return JVMetrics(Voc=0.55, Jsc=-21.2, Vmpp=0.45, Jmpp=-18.8, Pmpp=8.46, FF=0.726)


def make_protocol(protocol_cls, smu=None, lamp=None, **kwargs):
    smu = smu or make_smu()
    lamp = lamp or make_lamp()
    if protocol_cls is IVCurveProtocol:
        kwargs.setdefault("metrics_function", fake_metrics)
    protocol = protocol_cls(smu, lamp, **kwargs)
    protocol.light_intensity_measure_time = 0.0
    protocol.light_intensity_poll_interval = 0.0
    protocol.voc_check_wait = 0.0
    protocol.voc_poll_interval = 0.0
    if protocol_cls is MPPTrackingProtocol:
        protocol.auto_scan_dv = 0.02
        protocol.auto_scan_sweep_rate = 100.0
    return protocol


def common_params(**overrides) -> dict:
    params = {
        "light_int": 100.0,
        "Imax": 0.01,
        "Vmax": 2.0,
        "Dwell": 0.0,
        "Nwire": "2 wire",
        "active_area": 0.16,
        "cell_name": "test cell",
    }
    params.update(overrides)
    return params


def iv_params(**overrides) -> dict:
    return common_params(
        start_V=0.0,
        stop_V=0.6,
        dV=0.05,
        sweep_rate=1000.0,
        Fwd_current_limit=0.001,
        **overrides,
    )


def timed_params(**overrides) -> dict:
    params = common_params(interval=0.002, duration=0.04)
    params.update(overrides)
    return params


WORKER_CASES = [
    (IVCurveWorker, IVCurveProtocol, iv_params, IVResults),
    (
        ConstantVoltageWorker,
        ConstantVoltageProtocol,
        lambda: timed_params(set_voltage=0.2),
        ConstantVoltageResults,
    ),
    (
        ConstantCurrentWorker,
        ConstantCurrentProtocol,
        lambda: timed_params(set_current=0.0),
        ConstantCurrentResults,
    ),
    (
        MPPTrackingWorker,
        MPPTrackingProtocol,
        lambda: timed_params(start_voltage=0.45, duration=0.05),
        MPPResults,
    ),
    (
        CalibrationWorker,
        CalibrationProtocol,
        lambda: timed_params(reference_current=0.004),
        CalibrationResults,
    ),
]


@pytest.mark.parametrize(
    "worker_cls,protocol_cls,make_params,result_type",
    WORKER_CASES,
    ids=[case[0].__name__ for case in WORKER_CASES],
)
def test_worker_runs_and_emits_signals(
    worker_cls, protocol_cls, make_params, result_type
) -> None:
    protocol = make_protocol(protocol_cls)
    if protocol_cls is CalibrationProtocol:
        protocol.smu.reference_diode_parallel = True
        protocol.smu.use_reference_diode = True

    worker = worker_cls(protocol, make_params())
    recorder = SignalRecorder(worker)

    worker.run()

    assert recorder.errors == []
    assert len(recorder.results) == 1
    assert isinstance(recorder.results[0], result_type)
    assert recorder.status  # status messages flowed
    assert recorder.data  # live data flowed
    assert "Turning lamp off..." in recorder.status


def test_progress_is_derived_and_bounded() -> None:
    protocol = make_protocol(ConstantVoltageProtocol)
    worker = ConstantVoltageWorker(protocol, timed_params(set_voltage=0.1))
    recorder = SignalRecorder(worker)

    worker.run()

    assert recorder.progress  # derived from t / duration
    assert all(0 <= p <= 100 for p in recorder.progress)
    assert recorder.progress[-1] >= recorder.progress[0]


def test_iv_progress_follows_voltage_span() -> None:
    protocol = make_protocol(IVCurveProtocol)
    worker = IVCurveWorker(protocol, iv_params())
    recorder = SignalRecorder(worker)

    worker.run()

    assert recorder.progress
    assert recorder.progress[-1] == 100


def test_request_stop_cancels_long_run() -> None:
    smu = make_smu()
    protocol = make_protocol(ConstantVoltageProtocol, smu)
    worker = ConstantVoltageWorker(
        protocol, timed_params(set_voltage=0.1, duration=60.0)
    )
    recorder = SignalRecorder(worker)

    # signals are delivered synchronously: stop after the second sample
    worker.data_ready.connect(
        lambda data: worker.request_stop() if len(data["t"]) >= 2 else None
    )

    worker.run()

    assert worker.is_stop_requested()
    # controlled cancellation still finishes with the partial result
    assert recorder.errors == []
    assert len(recorder.results) == 1
    assert len(recorder.results[0].time) == 2
    assert "Run Aborted" in recorder.status
    # the protocol's cleanup ran
    assert not smu.output_enabled(SMUChannel.CELL)


def test_protocol_exception_is_emitted_as_error() -> None:
    smu = make_smu()
    lamp = make_lamp()
    protocol = make_protocol(ConstantVoltageProtocol, smu, lamp)
    worker = ConstantVoltageWorker(
        protocol, timed_params(set_voltage=5.0)  # outside Vmax compliance
    )
    recorder = SignalRecorder(worker)

    worker.run()

    assert len(recorder.errors) == 1
    assert "outside of compliance range" in recorder.errors[0]
    # no finished signal after an unhandled protocol error
    assert recorder.results == []
    # the protocol's try/finally still cleaned up
    assert not smu.output_enabled(SMUChannel.CELL)
    assert not lamp.light_is_on


def test_worker_rejects_wrong_protocol_type() -> None:
    protocol = make_protocol(ConstantVoltageProtocol)

    with pytest.raises(TypeError, match="expects a IVCurveProtocol"):
        IVCurveWorker(protocol, iv_params())


def test_workers_do_not_import_pyqt5_or_widgets() -> None:
    assert "PyQt5" not in sys.modules

    import iv_lab.measurements.workers as workers_pkg

    for module_name in list(sys.modules):
        if module_name.startswith("iv_lab.measurements.workers"):
            module = sys.modules[module_name]
            source = inspect.getsource(module)
            assert "PyQt5" not in source
            assert "QtWidgets" not in source
            assert "QtGui" not in source

    assert workers_pkg is not None


def test_workers_do_not_create_hardware() -> None:
    # workers receive hardware through the protocol instance only
    import iv_lab.measurements.workers as workers_pkg

    for module_name in list(sys.modules):
        if module_name.startswith("iv_lab.measurements.workers"):
            source = inspect.getsource(sys.modules[module_name])
            for factory in ("create_smu", "create_lamp", "create_arduino"):
                assert factory not in source

    smu = make_smu()
    protocol = make_protocol(ConstantVoltageProtocol, smu)
    worker = ConstantVoltageWorker(protocol, timed_params(set_voltage=0.0))
    assert worker.protocol.smu is smu
    assert workers_pkg is not None
