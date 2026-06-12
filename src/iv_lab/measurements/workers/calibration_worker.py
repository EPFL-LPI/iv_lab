"""Qt worker for the reference diode calibration protocol."""

from __future__ import annotations

from typing import Optional

from iv_lab.measurements.protocols.calibration import CalibrationProtocol

from .base_worker import MeasurementWorker


class CalibrationWorker(MeasurementWorker):
    """Runs :class:`CalibrationProtocol` (live data:
    ``{'t_meas': [...], 'i_meas_ma': [...], 't_ref': [...],
    'i_ref_ma': [...]}``)."""

    protocol_class = CalibrationProtocol

    def _progress_from_data(self, data: dict) -> Optional[int]:
        # use whichever time axis is advancing; the serial and IV_Old
        # modes run two passes, so this intentionally reaches 100% twice
        times = data.get("t_ref") or data.get("t_meas") or data.get("t")
        duration = self.params.get("duration")
        if not times or not duration:
            return None
        return int(100.0 * times[-1] / duration)
