import time
from typing import List, Tuple
import numpy as np
from app.common.schemas import DetectionResult, FrameData

try:
    from ultralytics import YOLO
    ULTRALYTICS_AVAILABLE = True
except ImportError:
    ULTRALYTICS_AVAILABLE = False


class YOLODetector:
    def __init__(
        self,
        model_path: str = "yolo11n.pt",
        confidence_threshold: float = 0.5,
        iou_threshold: float = 0.45,
        target_classes: List[int] = None,
        model_version: str = "yolo-v11n",
    ):
        self.model_path = model_path
        self.confidence_threshold = confidence_threshold
        self.iou_threshold = iou_threshold
        self.target_classes = target_classes or [0]  # default person
        self.model_version = model_version
        self.last_inference_latency_ms: float = 0.0

        if ULTRALYTICS_AVAILABLE:
            try:
                self.model = YOLO(self.model_path)
            except Exception:
                self.model = None
        else:
            self.model = None

    def detect(self, frame_data: FrameData) -> Tuple[List[DetectionResult], float]:
        """Detect objects in a frame. Returns (detections, latency_ms)."""
        start_time = time.perf_counter()
        results: List[DetectionResult] = []

        if self.model is not None and frame_data.image is not None:
            # Run YOLO inference
            prediction = self.model.predict(
                source=frame_data.image,
                conf=self.confidence_threshold,
                iou=self.iou_threshold,
                classes=self.target_classes,
                verbose=False,
            )
            if prediction and len(prediction) > 0:
                boxes = prediction[0].boxes
                for box in boxes:
                    cls_id = int(box.cls[0].item())
                    conf = float(box.conf[0].item())
                    xyxy = box.xyxy[0].tolist()  # [x1, y1, x2, y2]
                    
                    results.append(
                        DetectionResult(
                            class_id=cls_id,
                            class_name="person" if cls_id == 0 else f"cls_{cls_id}",
                            bbox=[float(x) for x in xyxy],
                            confidence=round(conf, 4),
                        )
                    )

        latency_ms = (time.perf_counter() - start_time) * 1000.0
        self.last_inference_latency_ms = latency_ms
        return results, latency_ms
