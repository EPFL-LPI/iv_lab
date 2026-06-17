"""Qt worker for the MPP tracking protocol."""

from __future__ import annotations

from iv_lab.measurements.protocols.mpp_tracking import MPPTrackingProtocol

from .base_worker import MeasurementWorker


class MPPTrackingWorker(MeasurementWorker):
    """Runs :class:`MPPTrackingProtocol` (live data:
    ``{'t': [...], 'w': [...], 'v': [...], 'j': [...]}``; the automatic
    start scan emits J-V data dicts first)."""

    protocol_class = MPPTrackingProtocol

    def _progress_from_data(self, data: dict) -> int | None:
        # the auto-start J-V scan emits {'v','j'} dicts with no time axis;
        # report indeterminate progress for those
        return self._time_progress(data)
