from __future__ import annotations

import time
from contextlib import nullcontext
from pathlib import Path
from typing import Any, Callable

import numpy as np

from app.common.schemas import DetectionResult, FrameData
from app.cv.deimv2_runtime_support import load_deimv2, merge_runtime_detections, validate_asset


class DEIMv2Detector:
    """Strict, stateless Phase 7A DEIMv2 inference adapter."""

    def __init__(
        self,
        source_path: str,
        config_path: str,
        checkpoint_path: str,
        backbone_path: str,
        device: str = "auto",
        confidence_threshold: float = 0.05,
        nms_iou_threshold: float = 0.5,
        checkpoint_sha256: str | None = None,
        backbone_sha256: str | None = None,
        model_version: str = "deimv2-phase7a",
        loader: Callable[..., tuple[Any, Any, Any, Any]] | None = None,
    ):
        self.source_path = validate_asset(source_path, "DEIMv2 source", directory=True)
        self.config_path = validate_asset(config_path, "DEIMv2 config")
        # The production loader deserializes a pickle-bearing checkpoint. It must
        # prove artifact identity first; injected test loaders never deserialize it.
        require_trusted_assets = loader is None
        self.checkpoint_path = validate_asset(
            checkpoint_path, "DEIMv2 checkpoint", checkpoint_sha256,
            require_checksum=require_trusted_assets,
        )
        self.backbone_path = validate_asset(
            backbone_path, "DINOv3 backbone", backbone_sha256,
            require_checksum=require_trusted_assets,
        )
        if not 0 <= confidence_threshold <= 1 or not 0 <= nms_iou_threshold <= 1:
            raise ValueError("confidence and NMS thresholds must be within [0, 1]")
        self.confidence_threshold = float(confidence_threshold)
        self.nms_iou_threshold = float(nms_iou_threshold)
        self.model_version = model_version
        load = loader or load_deimv2
        self.model, self.transform, self.device, self.torch = load(
            self.source_path, self.config_path, self.checkpoint_path, self.backbone_path, device
        )
        self.last_inference_latency_ms = 0.0

    def detect(self, frame_data: FrameData) -> tuple[list[DetectionResult], float]:
        if frame_data.image is None:
            return [], 0.0
        image = np.asarray(frame_data.image)
        if image.ndim != 3 or image.shape[2] != 3:
            raise ValueError("FrameData.image must be an HxWx3 BGR array")
        from PIL import Image

        rgb = Image.fromarray(image[:, :, ::-1])
        tensor = self.transform(rgb).unsqueeze(0).to(self.device)
        width, height = rgb.size
        sizes = self.torch.tensor([[width, height]], dtype=self.torch.float32, device=self.device)
        is_cuda = getattr(self.device, "type", str(self.device).split(":")[0]) == "cuda"
        context = self.torch.autocast("cuda", dtype=self.torch.float16) if is_cuda else nullcontext()
        start = time.perf_counter()
        with self.torch.inference_mode(), context:
            labels, boxes, scores = self.model(tensor, sizes)
        if is_cuda:
            self.torch.cuda.synchronize()
        latency = (time.perf_counter() - start) * 1000.0
        self.last_inference_latency_ms = latency
        labels = labels[0].detach().cpu().numpy().astype(np.int32)
        boxes = boxes[0].detach().float().cpu().numpy().astype(np.float32)
        scores = scores[0].detach().float().cpu().numpy().astype(np.float32)
        boxes, scores, labels = merge_runtime_detections(
            boxes, scores, labels, self.confidence_threshold, self.nms_iou_threshold
        )
        names = {0: "person", 1: "luggage"}
        detections = [
            DetectionResult(
                class_id=int(class_id),
                class_name=names[int(class_id)],
                bbox=[float(value) for value in box],
                confidence=float(score),
            )
            for box, score, class_id in zip(boxes, scores, labels)
        ]
        return detections, latency
