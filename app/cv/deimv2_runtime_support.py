from __future__ import annotations

import hashlib
import importlib
import re
import sys
from contextlib import contextmanager
from pathlib import Path
from threading import RLock

import numpy as np


_DEIM_IMPORT_LOCK = RLock()


@contextmanager
def _configured_source_import(source: str | Path):
    """Temporarily expose a DEIM checkout for its absolute ``engine`` imports."""
    source_path = Path(source).resolve()
    source_text = str(source_path)
    with _DEIM_IMPORT_LOCK:
        loaded_engine = sys.modules.get("engine")
        if loaded_engine is not None:
            engine_file = Path(getattr(loaded_engine, "__file__", "")).resolve()
            if source_path not in engine_file.parents:
                raise ImportError(
                    f"engine was already loaded outside configured DEIMv2 source: {engine_file}"
                )
        original_path = sys.path[:]
        try:
            sys.path.insert(0, source_text)
            importlib.invalidate_caches()
            yield
        finally:
            sys.path[:] = original_path


def _load_configured_engine(source: str | Path):
    with _configured_source_import(source):
        engine = importlib.import_module("engine.core")
    engine_file = Path(engine.__file__).resolve()
    if Path(source).resolve() not in engine_file.parents:
        raise ImportError(f"engine.core was not loaded from configured DEIMv2 source: {source}")
    return engine


def validate_configured_backbone(config: str | Path, backbone: str | Path) -> None:
    import yaml

    runtime_config = yaml.safe_load(Path(config).read_text(encoding="utf-8")) or {}
    configured_backbone = runtime_config.get("DINOv3STAs", {}).get("weights_path")
    if not configured_backbone or Path(configured_backbone).expanduser().resolve() != Path(backbone).resolve():
        raise ValueError("configured DEIMv2 backbone does not match validated backbone_path")


def validate_asset(
    value: str,
    label: str,
    checksum: str | None = None,
    directory: bool = False,
    require_checksum: bool = False,
) -> Path:
    path = Path(value).expanduser().resolve()
    valid = path.is_dir() if directory else path.is_file()
    if not valid:
        raise FileNotFoundError(f"{label} not found: {path}")
    if not directory and (checksum is not None or require_checksum):
        if not isinstance(checksum, str) or re.fullmatch(r"[0-9a-fA-F]{64}", checksum) is None:
            raise ValueError(f"{label} requires a valid 64-hex SHA-256 checksum")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest.lower() != checksum.lower():
            raise ValueError(f"{label} SHA-256 mismatch: {path}")
    return path


def _nms(boxes: np.ndarray, scores: np.ndarray, threshold: float) -> np.ndarray:
    order = scores.argsort()[::-1]
    keep: list[int] = []
    while order.size:
        current = int(order[0])
        keep.append(current)
        if order.size == 1:
            break
        rest = order[1:]
        xx1 = np.maximum(boxes[current, 0], boxes[rest, 0])
        yy1 = np.maximum(boxes[current, 1], boxes[rest, 1])
        xx2 = np.minimum(boxes[current, 2], boxes[rest, 2])
        yy2 = np.minimum(boxes[current, 3], boxes[rest, 3])
        inter = np.maximum(0, xx2 - xx1) * np.maximum(0, yy2 - yy1)
        area_a = (boxes[current, 2] - boxes[current, 0]) * (boxes[current, 3] - boxes[current, 1])
        area_b = (boxes[rest, 2] - boxes[rest, 0]) * (boxes[rest, 3] - boxes[rest, 1])
        iou = inter / np.maximum(area_a + area_b - inter, 1e-12)
        order = rest[iou <= threshold]
    return np.asarray(keep, dtype=np.int64)


def merge_runtime_detections(boxes, scores, labels, threshold: float, nms_iou: float):
    boxes = np.asarray(boxes, dtype=np.float32).reshape(-1, 4)
    scores = np.asarray(scores, dtype=np.float32).reshape(-1)
    labels = np.asarray(labels, dtype=np.int32).reshape(-1)
    valid = (scores >= threshold) & np.isin(labels, [0, 1, 2, 3])
    valid &= np.isfinite(scores) & np.isfinite(boxes).all(axis=1)
    valid &= (boxes[:, 2] > boxes[:, 0]) & (boxes[:, 3] > boxes[:, 1])
    boxes, scores, labels = boxes[valid], scores[valid], labels[valid]
    labels = np.where(labels == 0, 0, 1).astype(np.int32)
    selected = []
    for cid in (0, 1):
        indexes = np.flatnonzero(labels == cid)
        if indexes.size:
            selected.extend(indexes[_nms(boxes[indexes], scores[indexes], nms_iou)].tolist())
    selected = np.asarray(sorted(selected, key=lambda i: (-scores[i], labels[i])), dtype=np.int64)
    return boxes[selected], scores[selected], labels[selected]


def load_deimv2(source, config, checkpoint, backbone, device_name):
    import torch
    from torchvision.transforms import v2

    validate_configured_backbone(config, backbone)
    engine = _load_configured_engine(source)
    if device_name not in {"auto", "cpu", "cuda"}:
        raise ValueError("device must be auto, cpu, or cuda")
    if device_name == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA requested but unavailable")
    device = torch.device("cuda:0" if device_name == "cuda" or
                          (device_name == "auto" and torch.cuda.is_available()) else "cpu")
    cfg = engine.YAMLConfig(str(config), resume=str(checkpoint))
    state_file = torch.load(checkpoint, map_location="cpu", weights_only=False)
    state = state_file.get("ema", {}).get("module") or state_file.get("model")
    if state is None:
        raise ValueError("checkpoint must contain ema.module or model state")
    cfg.model.load_state_dict(state, strict=True)

    class Deploy(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.net = cfg.model.deploy()
            self.post = cfg.postprocessor.deploy()

        def forward(self, images, sizes):
            return self.post(self.net(images), sizes)

    transform = v2.Compose([v2.Resize((640, 640)), v2.ToImage(),
                            v2.ToDtype(torch.float32, scale=True)])
    return Deploy().to(device).eval(), transform, device, torch
