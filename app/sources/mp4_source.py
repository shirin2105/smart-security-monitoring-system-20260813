import os
import cv2
import numpy as np
from typing import Generator, Optional
from app.sources.base import BaseVideoSource
from app.common.schemas import FrameData
from app.common.time_utils import utc_now_iso, video_timestamp_iso

DEFAULT_FILE_SOURCE_EPOCH = "2026-01-01T00:00:00Z"


class MP4VideoSource(BaseVideoSource):
    def __init__(
        self,
        camera_id: str,
        source_uri: str,
        source_type: str = "SIMULATED",
        inference_fps: float = 5.0,
        source_start: Optional[str] = None,
    ):
        self.camera_id = camera_id
        self.source_uri = source_uri
        self.source_type = source_type
        self.inference_fps = inference_fps
        is_live = source_type.upper() in {"LIVE", "CAMERA", "RTSP"}
        self.source_start = source_start or (utc_now_iso() if is_live else DEFAULT_FILE_SOURCE_EPOCH)
        self.cap: Optional[cv2.VideoCapture] = None
        self._init_capture()

    def _init_capture(self) -> None:
        if os.path.exists(self.source_uri):
            self.cap = cv2.VideoCapture(self.source_uri)
        else:
            self.cap = None

    def read_frames(self) -> Generator[FrameData, None, None]:
        frame_id = 0
        if self.cap and self.cap.isOpened():
            source_fps = self.cap.get(cv2.CAP_PROP_FPS) or 25.0
            while self.cap.isOpened():
                ret, frame = self.cap.read()
                if not ret:
                    break
                frame_id += 1
                yield FrameData(
                    camera_id=self.camera_id,
                    frame_id=frame_id,
                    captured_at=video_timestamp_iso(self.source_start, frame_id - 1, source_fps),
                    source_type=self.source_type,
                    source_fps=source_fps,
                    inference_fps=self.inference_fps,
                    image=frame,
                )
        else:
            # Synthetic frame generator for testing when clip file isn't present
            source_fps = 25.0
            for i in range(1, 101):
                # 640x480 black image with synthetic text
                frame = np.zeros((480, 640, 3), dtype=np.uint8)
                yield FrameData(
                    camera_id=self.camera_id,
                    frame_id=i,
                    captured_at=video_timestamp_iso(self.source_start, i - 1, source_fps),
                    source_type="SYNTHETIC",
                    source_fps=source_fps,
                    inference_fps=self.inference_fps,
                    image=frame,
                )

    def release(self) -> None:
        if self.cap and self.cap.isOpened():
            self.cap.release()
