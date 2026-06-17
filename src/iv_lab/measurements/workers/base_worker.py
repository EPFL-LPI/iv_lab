"""Base Qt worker wrapping a measurement protocol.

Workers make the pure-Python protocols usable from the GUI (step 10 of
docs/MIGRATION.md): a worker is a plain ``QObject`` intended to be moved
to a ``QThread`` (no ``QThread`` subclassing), whose ``run()`` slot
executes the protocol and translates its callbacks into Qt signals:

- ``status_update(str)`` — protocol status messages,
- ``warning_update(str)`` — non-fatal warnings,
- ``data_ready(dict)`` — live data arrays for plotting,
- ``progress_update(int)`` — percent complete, derived from the live
  data where possible (-1 when indeterminate),
- ``finished(object)`` — the result dataclass, emitted after successful
  completion *and* after controlled cancellation (protocols return
  partial results when cancelled, as the legacy code did),
- ``error(str)`` — emitted instead of ``finished`` when the protocol
  raises; hardware cleanup has already happened in the protocol's
  ``try/finally``.

Cancellation: ``request_stop()`` sets a flag that the protocol polls
through its cancellation callback at the same points the legacy code
checked ``abortRunFlag``.

Workers never create hardware (it lives in the protocol instance passed
to the constructor), never write files, and import QtCore only.
"""

from __future__ import annotations

import threading

from PySide6.QtCore import QObject, Signal, Slot

from iv_lab.measurements.protocols.base import MeasurementProtocol


class MeasurementWorker(QObject):
    """Runs one measurement protocol and reports through Qt signals."""

    status_update = Signal(str)
    warning_update = Signal(str)
    #: Emitted when the protocol needs user confirmation; (message, adjusted_dv_V).
    warning_confirmation_needed = Signal(str, float)
    data_ready = Signal(dict)
    progress_update = Signal(int)
    finished = Signal(object)
    error = Signal(str)

    #: Protocol type expected by the concrete worker (checked on init).
    protocol_class: type = MeasurementProtocol

    def __init__(
        self,
        protocol: MeasurementProtocol,
        params: dict,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        if not isinstance(protocol, self.protocol_class):
            raise TypeError(
                f"{type(self).__name__} expects a "
                f"{self.protocol_class.__name__}, got {type(protocol).__name__}"
            )
        self.protocol = protocol
        self.params = dict(params)
        self._stop_requested = False
        self._confirm_event = threading.Event()
        self._confirm_ok = False

        protocol.set_callbacks(
            status=self.status_update.emit,
            warning=self.warning_update.emit,
            data=self._on_data,
            cancel=self.is_stop_requested,
            # confirm is wired separately via enable_blocking_confirmations()
            # so that non-threaded (test) use auto-proceeds without blocking
        )

    # --- cancellation ---

    @Slot()
    def request_stop(self) -> None:
        """Request cancellation; the protocol stops at its next check."""
        self._stop_requested = True

    def is_stop_requested(self) -> bool:
        """Whether cancellation has been requested."""
        return self._stop_requested

    # --- warning confirmation (for threaded use) ---

    def enable_blocking_confirmations(self) -> None:
        """Wire the blocking confirm callback; call only in threaded mode.

        In non-threaded (test) mode the confirm callback is left unset so
        the protocol auto-proceeds without blocking the main thread.
        """
        self.protocol.set_callbacks(confirm=self._confirm_warning)

    def _confirm_warning(self, message: str, adjusted_dv: float = 0.0) -> bool:
        """Block the worker thread until the GUI responds (OK or Abort)."""
        self._confirm_event.clear()
        self._confirm_ok = False
        self.warning_confirmation_needed.emit(message, adjusted_dv)
        self._confirm_event.wait()
        return self._confirm_ok

    def confirm_warning_ok(self) -> None:
        """Unblock the worker: user chose to proceed."""
        self._confirm_ok = True
        self._confirm_event.set()

    def confirm_warning_abort(self) -> None:
        """Unblock the worker: user chose to abort."""
        self._confirm_ok = False
        self._stop_requested = True
        self._confirm_event.set()

    # --- progress derivation ---

    def _progress_from_data(self, data: dict) -> int | None:
        """Derive percent complete from a live data dict; None = unknown.

        Overridden by concrete workers. Time-based measurements derive
        progress from the elapsed time and the requested duration.
        """
        return None

    def _on_data(self, data: dict) -> None:
        self.data_ready.emit(data)
        progress = self._progress_from_data(data)
        if progress is not None:
            self.progress_update.emit(max(0, min(100, int(progress))))

    def _time_progress(self, data: dict) -> int | None:
        """Progress for duration-based protocols from the time axis."""
        times = data.get("t")
        duration = self.params.get("duration")
        if not times or not duration:
            return None
        return int(100.0 * times[-1] / duration)

    # --- execution ---

    @Slot()
    def run(self) -> None:
        """Execute the protocol (call from the worker's thread).

        Emits ``finished`` with the result on success or controlled
        cancellation; emits ``error`` with the message when the protocol
        raises (the protocol's ``try/finally`` has already turned the
        hardware off).
        """
        try:
            result = self.protocol.run(self.params)
        except Exception as exc:  # noqa: BLE001 - everything goes to the GUI
            self.error.emit(str(exc))
            return
        self.finished.emit(result)
