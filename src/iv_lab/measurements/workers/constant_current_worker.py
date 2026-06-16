"""Qt worker for the constant-current protocol."""

from __future__ import annotations

from typing import Optional

from iv_lab.measurements.protocols.constant_current import ConstantCurrentProtocol

from .base_worker import MeasurementWorker


class ConstantCurrentWorker(MeasurementWorker):
    """Runs :class:`ConstantCurrentProtocol` (live data:
    ``{'t': [...], 'v': [...]}``)."""

    protocol_class = ConstantCurrentProtocol

    def _progress_from_data(self, data: dict) -> Optional[int]:
        return self._time_progress(data)
