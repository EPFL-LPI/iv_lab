"""Application orchestration (step 13 of docs/MIGRATION.md).

:class:`IVLabSystem` is the stable interface the GUI talks to. It is
the migrated orchestration layer of the legacy ``system`` class in
``IVLab/IVlab.py``:

- holds the typed settings,
- creates hardware through the factories (never directly in the GUI),
- connects/disconnects hardware (legacy ``hardware_init``),
- starts measurements by building a protocol + worker and running the
  worker on a ``QThread`` (legacy ran everything on the GUI thread with
  ``processEvents``); ``abort_run`` requests cancellation,
- re-emits the worker signals and stores the last result per scan type
  (legacy ``data_IV``/``IV_Results`` etc.),
- routes results to :class:`~iv_lab.data.FileWriter` (manual save with
  the legacy scan-type labels and error messages, and automatic save
  when ``saveDataAutomatic`` is enabled),
- coordinates authentication and the logbook (legacy
  ``user_login``/``user_logout``),
- persists a confirmed calibration to the settings file (.json or .toml),
  preserving comments in TOML files (legacy
  ``save_calibration_to_system_settings`` — with the fix that the
  arduino section is no longer dropped from the file).

GUI-facing communication happens exclusively through Qt signals; this
module imports QtCore only.
"""

from __future__ import annotations

import contextlib
import datetime
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QObject, QThread, Signal, Slot

from iv_lab.config import SystemSettings, save_settings
from iv_lab.data import FileWriter, SystemContext
from iv_lab.data.results import MeasurementResult
from iv_lab.hardware.arduino import create_arduino
from iv_lab.hardware.arduino.base import BaseArduino
from iv_lab.hardware.errors import HardwareError
from iv_lab.hardware.lamp import create_lamp
from iv_lab.hardware.smu import create_smu
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
from iv_lab.services import (
    AuthenticatedUser,
    AuthenticationError,
    Authenticator,
    Logbook,
    UserTableError,
    load_users,
)
from iv_lab.services.auth import USERS_FILENAME

#: Default settings filename (mirrors config.DEFAULT_SETTINGS_FILENAME).
SETTINGS_FILENAME = "config/system_settings.toml"


@dataclass(frozen=True)
class _MeasurementSpec:
    """Maps a legacy GUI scan-type label to its protocol and worker."""

    label: str
    protocol_cls: type
    worker_cls: type
    #: Result store key ('JV', 'CV', 'CC', 'MPP'); None for calibration.
    scan_key: str | None
    #: Legacy error message when saving without data.
    no_data_message: str | None = None


#: Legacy scan-type labels (GUI measurement menu / system.saveData).
MEASUREMENTS = {
    spec.label: spec
    for spec in [
        _MeasurementSpec(
            "J-V Scan",
            IVCurveProtocol,
            IVCurveWorker,
            "JV",
            "ERROR: No current J-V Data available to save.",
        ),
        _MeasurementSpec(
            "Constant Voltage, Measure J",
            ConstantVoltageProtocol,
            ConstantVoltageWorker,
            "CV",
            "ERROR: No current Constant-Voltage Data available to save.",
        ),
        _MeasurementSpec(
            "Constant Current, Measure V",
            ConstantCurrentProtocol,
            ConstantCurrentWorker,
            "CC",
            "ERROR: No current Constant-Current Data available to save.",
        ),
        _MeasurementSpec(
            "Maximum Power Point",
            MPPTrackingProtocol,
            MPPTrackingWorker,
            "MPP",
            "ERROR: No current MPP Data available to save.",
        ),
        _MeasurementSpec(
            "Calibration",
            CalibrationProtocol,
            CalibrationWorker,
            None,
        ),
    ]
}


class _HardwareInitWorker(QObject):
    """Runs ``IVLabSystem.hardware_init()`` on a worker thread.

    Hardware connection involves blocking VISA calls that can take seconds
    (or hang on a mis-wired instrument); running them here keeps the GUI
    responsive. ``hardware_init`` reports through the system's own signals,
    so this worker only needs to signal when it is done (so the thread can
    quit). ``hardware_init`` handles its own errors and never raises.
    """

    done = Signal()

    def __init__(self, system: IVLabSystem) -> None:
        super().__init__()
        self._system = system

    @Slot()
    def run(self) -> None:
        try:
            self._system.hardware_init()
        finally:
            self.done.emit()


class IVLabSystem(QObject):
    """Coordinates hardware, measurements, data, and services."""

    # GUI-facing signals
    status_message = Signal(str)
    warning_message = Signal(str)
    #: Emitted when a protocol needs the user to confirm before continuing.
    #: Payload: (message, adjusted_dv_in_V); adjusted_dv is 0 when not applicable.
    warning_confirmation_needed = Signal(str, float)
    error_message = Signal(str)
    data_updated = Signal(dict)
    #: Measured light intensity in % sun, emitted right after the reference
    #: diode reading and before the electrical measurement begins.
    light_intensity_measured = Signal(float)
    progress_updated = Signal(int)
    measurement_started = Signal(str)  # scan-type label
    measurement_finished = Signal(object)  # result dataclass
    #: Derived full-sun reference current in A after a calibration run.
    calibration_ready = Signal(float)
    hardware_ready = Signal(bool)
    user_logged_in = Signal(object)  # AuthenticatedUser
    user_logged_out = Signal()

    def __init__(
        self,
        settings: SystemSettings,
        *,
        settings_file: str | Path = SETTINGS_FILENAME,
        users_file: str | Path = USERS_FILENAME,
        logo_path: str | Path | None = None,
        threaded: bool = True,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self.settings = settings
        self.settings_file = Path(settings_file)
        self.logo_path = str(logo_path) if logo_path is not None else None
        #: Run workers on a QThread (True in the GUI; False runs
        #: synchronously, used by tests and scripting).
        self.threaded = threaded

        # system preferences (legacy system.__init__, defaults from settings)
        self.save_data_automatic = settings.IVsys.saveDataAutomatic

        # user table (legacy: failure is reported, login stays impossible)
        self.authenticator: Authenticator | None = None
        self.user_table_error: str | None = None
        try:
            self.authenticator = Authenticator(load_users(users_file))
        except UserTableError as exc:
            self.user_table_error = str(exc)

        self.logbook = Logbook(settings.computer.sdPath)
        self.user: AuthenticatedUser | None = None

        # hardware through the factories (legacy system.__init__)
        self.smu = create_smu(settings.SMU)
        self.smu.full_sun_reference_current = settings.IVsys.fullSunReferenceCurrent
        self.smu.calibration_datetime = settings.IVsys.calibrationDateTime
        self.smu.reference_diode_imax = settings.IVsys.referenceDiodeImax

        # parallel reference measurement needs a real second channel; on
        # IV_Old the diode sits on a stage and is never lit with the cell
        self.smu.reference_diode_parallel = settings.SMU.model in (
            "2600",
            "2602",
        ) and settings.IVsys.sysName != "IV_Old"

        self.lamp = create_lamp(settings.lamp, smu=self.smu)

        self.arduino: BaseArduino | None = None
        if settings.IVsys.sysName == "IV_Old":
            if settings.arduino is None:
                raise ValueError(
                    "ERROR: System name is set to 'IV_Old' but no arduino "
                    "settings dictionary is present"
                )
            self.arduino = create_arduino(settings.arduino)

        #: Last result per scan key ('JV', 'CV', 'CC', 'MPP'); legacy
        #: data_IV/IV_Results etc.
        self.results: dict[str, MeasurementResult] = {}

        self._worker: MeasurementWorker | None = None
        self._thread: QThread | None = None
        self._running = False

        # background hardware-initialization thread (keeps the GUI responsive)
        self._init_worker: _HardwareInitWorker | None = None
        self._init_thread: QThread | None = None

    # --- hardware (legacy hardware_init) ---

    def hardware_init(self) -> bool:
        """Connect all configured hardware; emits ``hardware_ready``."""
        self.status_message.emit("Initializing SMU...")
        try:
            self.smu.connect()
        except (ValueError, HardwareError) as err:
            self.error_message.emit(
                "Error initializing keithley sourcemeter: \n\n" + str(err)
            )
            self.hardware_ready.emit(False)
            return False
        except Exception:
            self.error_message.emit("Error initializing keithley sourcemeter")
            self.hardware_ready.emit(False)
            return False

        self.status_message.emit("Initializing lamp...")
        try:
            self.lamp.connect()
        except (ValueError, HardwareError) as err:
            self.error_message.emit("Error initializing lamp: \n\n" + str(err))
            self.hardware_ready.emit(False)
            return False
        except Exception:
            self.error_message.emit("Error initializing lamp")
            self.hardware_ready.emit(False)
            return False

        if self.arduino is not None:
            self.status_message.emit("Initializing Arduino...")
            try:
                self.arduino.connect()
            except (ValueError, HardwareError) as err:
                self.error_message.emit(
                    "Error initializing arduino: \n\n" + str(err)
                )
                self.hardware_ready.emit(False)
                return False
            except Exception:
                # legacy printed the generic lamp message here by accident
                self.error_message.emit("Error initializing arduino")
                self.hardware_ready.emit(False)
                return False

        self.status_message.emit("Hardware initialized")
        self.hardware_ready.emit(True)
        return True

    def start_hardware_init(self) -> None:
        """Connect hardware without blocking the caller.

        In threaded mode (the GUI) the connection runs on a worker thread so
        a slow or hanging instrument cannot freeze the UI; progress and the
        final ``hardware_ready`` are reported through the usual signals. In
        non-threaded mode (tests/scripting) it runs synchronously. A second
        call while an initialization is already running is ignored.
        """
        if not self.threaded:
            self.hardware_init()
            return
        if self._init_thread is not None and self._init_thread.isRunning():
            return

        worker = _HardwareInitWorker(self)
        thread = QThread(self)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.done.connect(thread.quit)
        thread.finished.connect(self._cleanup_init_thread)
        self._init_worker = worker
        self._init_thread = thread
        thread.start()

    def _cleanup_init_thread(self) -> None:
        # runs in the main thread after the init thread finished; drop the
        # worker reference and reclaim the thread object (mirrors
        # _cleanup_worker)
        self._init_worker = None
        if self._init_thread is not None:
            self._init_thread.deleteLater()
            self._init_thread = None

    def turn_off(self) -> None:
        """Bring the hardware into a safe state.

        Safe order per docs/HARDWARE.md: block the light first (close
        the shutter), then the lamp, then disable the SMU outputs. The
        legacy ``turn_off`` did SMU first and had no arduino step.
        """
        if self.arduino is not None:
            self.arduino.turn_off()  # closes the shutter
        self.lamp.turn_off()
        self.smu.turn_off()

    def disconnect_hardware(self) -> None:
        """Disconnect all hardware, ignoring errors (legacy logout path)."""
        for device in (self.smu, self.lamp, self.arduino):
            if device is None:
                continue
            with contextlib.suppress(Exception):
                device.disconnect()

    # --- authentication and logbook (legacy user_login / user_logout) ---

    def login(self, username: str, password: str) -> bool:
        """Authenticate a user; emits the legacy error messages on failure."""
        if self.authenticator is None:
            self.error_message.emit(self.user_table_error or "No user table")
            return False
        try:
            self.user = self.authenticator.login(username, password)
        except AuthenticationError as err:
            self.error_message.emit(str(err))
            return False

        self.status_message.emit("User set to: " + self.user.username)
        self.logbook.log_login(self.user.username)
        self.user_logged_in.emit(self.user)
        return True

    def logout(self, log_book_entry: str = "") -> None:
        """Log the user out (legacy ``user_logout``)."""
        # clear out scan data and results (legacy)
        self.results = {}

        if self.user is not None:
            self.logbook.log_logout(self.user.username, log_book_entry)
        self.user = None

        # disconnect the hardware, ignoring errors (legacy)
        self.disconnect_hardware()

        self.status_message.emit("Please Log In")
        self.user_logged_out.emit()

    # --- measurements ---

    def _build_protocol(self, spec: _MeasurementSpec):
        kwargs = {}
        if spec.protocol_cls is MPPTrackingProtocol:
            # legacy MPPVoltageStep* system preferences
            kwargs["voltage_step_initial"] = self.settings.IVsys.MPPVoltageStepInitial
            kwargs["voltage_step_max"] = self.settings.IVsys.MPPVoltageStepMax
            kwargs["voltage_step_min"] = self.settings.IVsys.MPPVoltageStepMin

        return spec.protocol_cls(
            self.smu,
            self.lamp,
            self.arduino,
            system_name=self.settings.IVsys.sysName,
            check_voc_before_scan=self.settings.IVsys.checkVOCBeforeScan,
            **kwargs,
        )

    def is_measurement_running(self) -> bool:
        """Whether a measurement is currently in progress."""
        if self._running:
            return True
        return self._thread is not None and self._thread.isRunning()

    def run_measurement(self, label: str, params: dict) -> bool:
        """Start the measurement with the legacy scan-type ``label``.

        Returns False (with an error message) when the label is unknown
        or a measurement is already running.
        """
        spec = MEASUREMENTS.get(label)
        if spec is None:
            self.error_message.emit(f"ERROR: Unknown measurement type '{label}'")
            return False
        if self.is_measurement_running():
            self.error_message.emit("ERROR: A measurement is already running")
            return False

        protocol = self._build_protocol(spec)
        worker = spec.worker_cls(protocol, params)

        # route the worker signals to the GUI-facing signals
        worker.status_update.connect(self.status_message)
        worker.warning_update.connect(self.warning_message)
        worker.data_ready.connect(self.data_updated)
        worker.light_intensity_ready.connect(self.light_intensity_measured)
        worker.progress_update.connect(self.progress_updated)
        worker.finished.connect(
            lambda result, spec=spec: self._on_worker_finished(spec, result)
        )
        worker.error.connect(self._on_worker_error)

        self._worker = worker
        self.measurement_started.emit(label)

        if not self.threaded:
            self._running = True
            try:
                worker.run()
            finally:
                self._running = False
                self._worker = None
            return True

        # threaded mode: enable blocking confirmations and route the signal
        worker.enable_blocking_confirmations()
        worker.warning_confirmation_needed.connect(self.warning_confirmation_needed)

        thread = QThread(self)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(thread.quit)
        worker.error.connect(thread.quit)
        thread.finished.connect(self._cleanup_worker)
        self._thread = thread
        thread.start()
        return True

    def abort_run(self) -> None:
        """Request cancellation of the running measurement (legacy
        ``abort_run``)."""
        if self._worker is not None:
            self._worker.request_stop()

    def confirm_warning_ok(self) -> None:
        """Unblock the running measurement worker: user chose to proceed."""
        if self._worker is not None:
            self._worker.confirm_warning_ok()

    def confirm_warning_abort(self) -> None:
        """Unblock the running measurement worker: user chose to abort."""
        if self._worker is not None:
            self._worker.confirm_warning_abort()

    def _cleanup_worker(self) -> None:
        # runs in the main thread after the worker thread finished;
        # deleteLater on the worker would post to the finished thread's
        # queue and never run — dropping the Python reference lets
        # PySide reclaim the worker safely instead
        self._worker = None
        if self._thread is not None:
            self._thread.deleteLater()  # thread object lives in this thread
            self._thread = None

    def _on_worker_finished(self, spec: _MeasurementSpec, result) -> None:
        if spec.scan_key is not None:
            self.results[spec.scan_key] = result

            # legacy: automatic save after a completed run with data
            primary = result.voltage if spec.scan_key == "JV" else result.time
            if self.save_data_automatic and len(primary) > 0 and self.user is not None:
                self._save_result(result)
        else:
            # calibration: hand the derived current to the GUI; saving to
            # the settings file stays a separate user-confirmed step
            if result.reference_current is not None:
                self.calibration_ready.emit(result.reference_current)

        self.measurement_finished.emit(result)

    def _on_worker_error(self, message: str) -> None:
        self.error_message.emit(message)

    # --- data saving (legacy saveData / toggleAutoSave) ---

    def toggle_auto_save(self, enabled: bool) -> None:
        """Legacy ``toggleAutoSave``."""
        self.save_data_automatic = enabled

    def _system_context(self) -> SystemContext:
        return SystemContext(
            base_path=self.settings.computer.basePath,
            sd_path=self.settings.computer.sdPath,
            system_name=self.settings.IVsys.sysName,
            smu_brand=self.settings.SMU.brand,
            smu_model=self.settings.SMU.model,
            lamp_display_name=self.settings.lamp.display_name or "",
            use_reference_diode=self.smu.use_reference_diode,
            full_sun_reference_current=self.smu.full_sun_reference_current,
            calibration_datetime=self.smu.calibration_datetime,
            logo_path=self.logo_path,
        )

    def _save_result(self, result: MeasurementResult) -> None:
        writer = FileWriter(
            self._system_context(), status_callback=self.status_message.emit
        )
        writer.save(result, self.user.username)

    def save_data(self, label: str, cell_name: str) -> bool:
        """Save the last result of the scan type (legacy ``saveData``).

        The cell name field value at save time overwrites the stored one
        (legacy: 'this gives a more intuitive functionality').
        """
        spec = MEASUREMENTS.get(label)
        if spec is None or spec.scan_key is None:
            self.error_message.emit(f"ERROR: Unknown measurement type '{label}'")
            return False

        result = self.results.get(spec.scan_key)
        if result is None:
            self.error_message.emit(spec.no_data_message)
            return False

        result.cell_name = cell_name
        self._save_result(result)
        return True

    # --- calibration persistence (legacy save_calibration_to_system_settings) ---

    def save_calibration_to_system_settings(self, calibration_params: dict) -> None:
        """Persist a confirmed calibration to the settings file.

        Updates ``fullSunReferenceCurrent`` and ``calibrationDateTime``
        in memory and on the SMU, then writes the file back via
        :func:`~iv_lab.config.save_settings` (JSON: full rewrite;
        TOML: targeted round-trip that preserves comments).
        """
        date_time_string = datetime.datetime.now().strftime("%c")
        reference_current = calibration_params["reference_current"]

        self.settings.IVsys.fullSunReferenceCurrent = reference_current
        self.smu.full_sun_reference_current = reference_current
        self.settings.IVsys.calibrationDateTime = date_time_string
        self.smu.calibration_datetime = date_time_string

        save_settings(self.settings_file, self.settings)

    # --- shutdown ---

    def shutdown(self) -> None:
        """Abort any run, make the hardware safe, and disconnect."""
        self.abort_run()
        with contextlib.suppress(Exception):
            self.turn_off()
        self.disconnect_hardware()
