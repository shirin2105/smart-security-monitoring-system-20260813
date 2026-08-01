from app.common.schemas import FrameData


class FrameSampler:
    """Samples frames according to source FPS and target inference FPS."""

    def __init__(self, inference_fps: float = 5.0):
        self.inference_fps = inference_fps

    def should_process(self, frame_data: FrameData) -> bool:
        if frame_data.source_fps <= 0:
            return True
        sample_interval = max(1, int(frame_data.source_fps / self.inference_fps))
        return (frame_data.frame_id % sample_interval) == 0
