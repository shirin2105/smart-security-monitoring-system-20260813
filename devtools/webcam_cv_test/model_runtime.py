from __future__ import annotations

import importlib.util
import sys
from contextlib import nullcontext
from pathlib import Path

import numpy as np


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import runtime module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class SharedCvRuntime:
    """One DEIMv2 inference and one shared tracking update per webcam frame."""

    def __init__(self, repo_root: Path, fps: float):
        self.repo_root = repo_root
        self.deim_repo = repo_root / "third_party/deimv2"
        self.checkpoint = (repo_root / "artifacts/phase7a-results/outputs/"
                           "phase7a_deimv2_s_person_luggage/best.pth")
        self.backbone = self.deim_repo / "ckpts/vitt_distill.pt"
        for path in (self.checkpoint, self.backbone):
            if not path.is_file():
                raise FileNotFoundError(path)
        runner_path = repo_root / "kaggle_pipeline/phase7b1_kernel/phase7b1_kaggle_v4_generic_luggage.py"
        core_path = repo_root / "kaggle_pipeline/phase7b1_kernel/phase7b1_runtime_core.py"
        self.runner = _load_module("webcam_phase7b1_runner", runner_path)
        core = _load_module("webcam_phase7b1_core", core_path)
        self.runner.REPO = self.deim_repo
        self.runner.WORK = Path(__file__).resolve().parent / "outputs/runtime"
        self.runner.WORK.mkdir(parents=True, exist_ok=True)
        config = self._write_config()
        self.model, self.device = self._load_model(config)
        self.transform = self.runner.build_transform()
        self.tracker = core.RuntimeByteTrack(frame_rate=fps, config=core.TrackerConfig())
        self.manager = core.CandidateManager(
            quality=core.QualityConfig(luggage_min_age_s=1.5,
                                       luggage_high_conf_threshold=0.35,
                                       luggage_min_high_hits=3),
            background=core.BackgroundConfig(warmup_s=8.0),
        )

    def _load_model(self, config: Path):
        import torch

        sys.path.insert(0, str(self.deim_repo))
        from engine.core import YAMLConfig
        cfg = YAMLConfig(str(config), resume=str(self.checkpoint))
        checkpoint = torch.load(self.checkpoint, map_location="cpu", weights_only=False)
        state = checkpoint["ema"]["module"] if "ema" in checkpoint else checkpoint["model"]
        info = cfg.model.load_state_dict(state, strict=True)
        print("[MODEL] load_state_dict:", info)

        class Deploy(torch.nn.Module):
            def __init__(self, model, postprocessor):
                super().__init__()
                self.model = model.deploy()
                self.postprocessor = postprocessor.deploy()

            def forward(self, images, original_sizes):
                return self.postprocessor(self.model(images), original_sizes)

        device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
        return Deploy(cfg.model, cfg.postprocessor).to(device).eval(), device

    def _write_config(self) -> Path:
        path = self.runner.WORK / "webcam_deimv2_s.yml"
        base = self.deim_repo / "configs/deimv2/deimv2_dinov3_s_coco.yml"
        path.write_text(
            f"__include__: ['{base.as_posix()}']\n"
            "num_classes: 4\nremap_mscoco_category: False\n"
            "eval_spatial_size: [640, 640]\n"
            f"DINOv3STAs:\n  weights_path: '{self.backbone.as_posix()}'\n"
            "PostProcessor:\n  num_top_queries: 300\n",
            encoding="utf-8",
        )
        return path

    def process(self, frame, frame_index: int, timestamp_s: float) -> tuple[list[dict], float, float]:
        import cv2
        import torch
        from PIL import Image

        start = __import__("time").perf_counter()
        image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        tensor = self.transform(image).unsqueeze(0).to(self.device)
        width, height = image.size
        original = torch.tensor([[width, height]], dtype=torch.float32, device=self.device)
        context = (torch.autocast(device_type="cuda", dtype=torch.float16)
                   if self.device.type == "cuda" else nullcontext())
        with torch.inference_mode(), context:
            labels, boxes, scores = self.model(tensor, original)
        if self.device.type == "cuda":
            torch.cuda.synchronize()
        detector_ms = (__import__("time").perf_counter() - start) * 1000.0
        labels = labels[0].detach().cpu().numpy().astype(np.int32)
        boxes = boxes[0].detach().float().cpu().numpy().astype(np.float32)
        scores = scores[0].detach().float().cpu().numpy().astype(np.float32)
        keep = scores >= 0.05
        boxes, scores, labels = boxes[keep], scores[keep], labels[keep]
        boxes, scores, runtime_labels, _, _ = self.runner.runtime_merge_detections(
            boxes, scores, labels)
        observations = self.tracker.update(boxes, scores, runtime_labels,
                                           frame_index, timestamp_s)
        enriched = self.manager.process(observations, timestamp_s)
        rows = []
        for item in enriched:
            obs = item["observation"]
            rows.append({
                "frame_index": obs.frame_index,
                "timestamp_s": obs.timestamp_s,
                "class_id": obs.class_id,
                "class_name": obs.class_name,
                "global_track_id": obs.global_track_id,
                "local_track_id": obs.local_track_id,
                "bbox_xyxy": list(obs.bbox_xyxy),
                "center_xy": list(obs.center),
                "confidence": obs.confidence,
                "eligible": bool(item["eligible"]),
                "status": item["status"],
            })
        if self.device.type == "cuda":
            torch.cuda.synchronize()
        pipeline_ms = (__import__("time").perf_counter() - start) * 1000.0
        return rows, detector_ms, pipeline_ms
