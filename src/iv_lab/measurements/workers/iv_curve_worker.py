"""Qt worker for the J-V scan protocol."""

from __future__ import annotations

from iv_lab.measurements.protocols.iv_curve import IVCurveProtocol

from .base_worker import MeasurementWorker


class IVCurveWorker(MeasurementWorker):
    """Runs :class:`IVCurveProtocol` (live data: ``{'v': [...], 'j': [...]}``)."""

    protocol_class = IVCurveProtocol

    def _progress_from_data(self, data: dict) -> int | None:
        # progress along the voltage span; unknown for 'Voc' limits
        voltages = data.get("v")
        start = self.params.get("start_V")
        stop = self.params.get("stop_V")
        if not voltages or not isinstance(start, (int, float)) or not isinstance(
            stop, (int, float)
        ):
            return None
        span = stop - start
        if span == 0:
            return None
        return int(100.0 * (voltages[-1] - start) / span)
