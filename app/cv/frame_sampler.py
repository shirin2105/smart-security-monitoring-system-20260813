from app.common.schemas import FrameData
from app.common.time_utils import parse_iso_timestamp


class FrameSampler:
    """Samples frames according to source FPS and target inference FPS."""

    def __init__(self, inference_fps: float = 5.0):
        self.inference_fps = inference_fps
        self._last_live_sample_at: float | None = None

    def should_process(self, frame_data: FrameData) -> bool:
        if str(frame_data.source_type).upper() in {"RTSP", "CAMERA", "LIVE"}:
            return self._should_process_live(frame_data)
        if self.inference_fps <= 0:
            return True
        if frame_data.source_fps <= 0:
            return True
        sample_interval = max(1, int(frame_data.source_fps / self.inference_fps))
        return (frame_data.frame_id % sample_interval) == 0

    def _should_process_live(self, frame_data: FrameData) -> bool:
        """Use capture time for streams because RTSP FPS metadata is often absent or wrong."""
        if self.inference_fps <= 0:
            return True
        captured_at_s = parse_iso_timestamp(frame_data.captured_at).timestamp()
        if self._last_live_sample_at is None:
            self._last_live_sample_at = captured_at_s
            return True
        if captured_at_s < self._last_live_sample_at:
            return False
        if captured_at_s - self._last_live_sample_at < 1.0 / self.inference_fps:
            return False
        self._last_live_sample_at = captured_at_s
        return True
