"""Qt worker for the constant-voltage protocol."""

from __future__ import annotations

from typing import Optional

from iv_lab.measurements.protocols.constant_voltage import ConstantVoltageProtocol

from .base_worker import MeasurementWorker


class ConstantVoltageWorker(MeasurementWorker):
    """Runs :class:`ConstantVoltageProtocol` (live data:
    ``{'t': [...], 'j': [...]}``)."""

    protocol_class = ConstantVoltageProtocol

    def _progress_from_data(self, data: dict) -> Optional[int]:
        return self._time_progress(data)
