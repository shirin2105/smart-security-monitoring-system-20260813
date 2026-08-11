"""
PHASE 7B.1 v4 — GENERIC LUGGAGE + CROSS-CLASS NMS + QUALITY/BACKGROUND FILTER

NOT a training job.

Required Kaggle Inputs:
1) Phase7A best.pth
2) one test video (.mp4/.avi/.mov/.mkv)
3) optional vitt_distill.pt (otherwise Internet ON)

phase7b_core.py is EMBEDDED; do not attach it separately.

Outputs:
  /kaggle/working/phase7b1_generic_luggage/annotated_all_tracks.mp4
  /kaggle/working/phase7b1_generic_luggage/annotated_candidate_view.mp4
  /kaggle/working/phase7b1_generic_luggage/tracks_v4.jsonl
  /kaggle/working/phase7b1_generic_luggage/background_anchors.json
  /kaggle/working/phase7b1_generic_luggage/summary_v4.json

Optional env:
  VIDEO_PATH=/kaggle/input/.../clip.mp4
  PHASE7A_CKPT=/kaggle/input/.../best.pth
  INFERENCE_MODE=auto|full640|tile768_overlap20
  MAX_SECONDS=120
"""

from __future__ import annotations
import os, sys, time, shutil, subprocess, json
from pathlib import Path
from collections import Counter

import numpy as np
import torch

INPUT=Path("/kaggle/input")
WORK=Path("/kaggle/working")
REPO=WORK/"DEIMv2"
OUT=WORK/"phase7b1_generic_luggage"

DEIM_COMMIT="0fff8d4dcdc272e6cf2d84be31399db471357941"
VITT_GOOGLE_DRIVE_ID="1YMTq_woOLjAcZnHSYNTsNg7f0ahj5LPs"

MODE=os.environ.get("INFERENCE_MODE","auto")
MAX_SECONDS=float(os.environ.get("MAX_SECONDS","120"))
DETECTOR_LOW_THRESHOLD=0.05
TILE_SIZE=768
TILE_OVERLAP=0.20
TILE_NMS_IOU=0.60
MAX_DETS=300
AUTO_TILE_MIN_PIXELS=1_500_000
ORIGINAL_CLASS_NAMES={0:"person",1:"backpack",2:"handbag",3:"suitcase"}
RUNTIME_CLASS_NAMES={0:"person",1:"luggage"}

PERSON_NMS_IOU=float(os.environ.get("PERSON_NMS_IOU","0.60"))
LUGGAGE_NMS_IOU=float(os.environ.get("LUGGAGE_NMS_IOU","0.50"))

WARMUP_SECONDS=float(os.environ.get("WARMUP_SECONDS","8.0"))
LUGGAGE_EVENT_MIN_AGE=float(os.environ.get("LUGGAGE_EVENT_MIN_AGE","1.5"))
LUGGAGE_EVENT_HIGH_CONF=float(os.environ.get("LUGGAGE_EVENT_HIGH_CONF","0.35"))
LUGGAGE_EVENT_MIN_HIGH_HITS=int(os.environ.get("LUGGAGE_EVENT_MIN_HIGH_HITS","3"))

EMBEDDED_CORE = 'from __future__ import annotations\n\nfrom dataclasses import dataclass, field\nfrom collections import defaultdict\nfrom typing import Dict, List, Sequence, Tuple\nimport json\nfrom pathlib import Path\nimport numpy as np\n\nRUNTIME_CLASS_NAMES = {0: "person", 1: "luggage"}\nID_NAMESPACE = 1_000_000\n\n\ndef bbox_iou(a, b) -> float:\n    ax1, ay1, ax2, ay2 = map(float, a)\n    bx1, by1, bx2, by2 = map(float, b)\n    ix1, iy1 = max(ax1, bx1), max(ay1, by1)\n    ix2, iy2 = min(ax2, bx2), min(ay2, by2)\n    iw, ih = max(0.0, ix2 - ix1), max(0.0, iy2 - iy1)\n    inter = iw * ih\n    aa = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)\n    ba = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)\n    union = aa + ba - inter\n    return inter / union if union > 0 else 0.0\n\n\n@dataclass\nclass TrackerConfig:\n    detector_low_threshold: float = 0.05\n    track_activation_threshold: float = 0.25\n    high_conf_det_threshold: float = 0.60\n    minimum_consecutive_frames: int = 2\n    minimum_iou_threshold: float = 0.10\n    lost_track_buffer: int = 30\n\n\n@dataclass\nclass QualityConfig:\n    # Provisional "eligible for event logic" gate, NOT final abandoned thresholds.\n    person_min_age_s: float = 0.7\n    person_min_hits: int = 3\n    person_high_conf_threshold: float = 0.40\n    person_min_high_hits: int = 2\n\n    luggage_min_age_s: float = 1.5\n    luggage_min_hits: int = 5\n    luggage_high_conf_threshold: float = 0.35\n    luggage_min_high_hits: int = 3\n\n\n@dataclass\nclass BackgroundConfig:\n    warmup_s: float = 8.0\n    max_first_seen_s: float = 1.0\n    min_duration_s: float = 3.0\n    min_hits: int = 20\n    max_stationary_norm: float = 0.25\n    suppress_iou: float = 0.50\n\n\n@dataclass\nclass TrackObservation:\n    frame_index: int\n    timestamp_s: float\n    class_id: int\n    class_name: str\n    global_track_id: int\n    local_track_id: int\n    bbox_xyxy: Tuple[float, float, float, float]\n    confidence: float\n\n    @property\n    def center(self) -> Tuple[float, float]:\n        x1, y1, x2, y2 = self.bbox_xyxy\n        return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)\n\n\n@dataclass\nclass TrackState:\n    class_id: int\n    global_track_id: int\n    first_seen_s: float\n    last_seen_s: float\n    first_frame: int\n    last_frame: int\n    hits: int = 0\n    high_conf_hits: int = 0\n    max_confidence: float = 0.0\n    confidence_sum: float = 0.0\n    boxes: List[Tuple[float, float, float, float]] = field(default_factory=list)\n    centers: List[Tuple[float, float]] = field(default_factory=list)\n\n    @property\n    def age_s(self) -> float:\n        return max(0.0, self.last_seen_s - self.first_seen_s)\n\n    @property\n    def mean_confidence(self) -> float:\n        return self.confidence_sum / max(self.hits, 1)\n\n    @property\n    def median_bbox(self) -> Tuple[float, float, float, float]:\n        if not self.boxes:\n            return (0.0, 0.0, 0.0, 0.0)\n        arr = np.asarray(self.boxes, dtype=np.float32)\n        return tuple(float(v) for v in np.median(arr, axis=0))\n\n    @property\n    def stationary_norm(self) -> float:\n        """Robust bbox-jitter-normalized spread; lower means more stationary."""\n        if len(self.centers) < 3 or not self.boxes:\n            return float("inf")\n        centers = np.asarray(self.centers, dtype=np.float32)\n        med = np.median(centers, axis=0)\n        dist = np.linalg.norm(centers - med, axis=1)\n        robust_disp = float(np.percentile(dist, 90))\n        boxes = np.asarray(self.boxes, dtype=np.float32)\n        w = np.maximum(1.0, boxes[:, 2] - boxes[:, 0])\n        h = np.maximum(1.0, boxes[:, 3] - boxes[:, 1])\n        diag = float(np.median(np.sqrt(w * w + h * h)))\n        return robust_disp / max(diag, 1.0)\n\n\n@dataclass\nclass BackgroundAnchor:\n    class_id: int\n    bbox_xyxy: Tuple[float, float, float, float]\n    source_track_id: int\n    stationary_norm: float\n\n\nclass RuntimeByteTrack:\n    """\n    Two trackers only:\n      0 = person\n      1 = generic luggage\n    """\n    def __init__(self, frame_rate: float, config: TrackerConfig | None = None):\n        self.config = config or TrackerConfig()\n        import supervision as sv\n        from trackers import ByteTrackTracker\n\n        self._sv = sv\n        self._trackers = {\n            cid: ByteTrackTracker(\n                lost_track_buffer=self.config.lost_track_buffer,\n                frame_rate=max(float(frame_rate), 1e-6),\n                track_activation_threshold=self.config.track_activation_threshold,\n                minimum_consecutive_frames=self.config.minimum_consecutive_frames,\n                minimum_iou_threshold=self.config.minimum_iou_threshold,\n                high_conf_det_threshold=self.config.high_conf_det_threshold,\n            )\n            for cid in RUNTIME_CLASS_NAMES\n        }\n\n    def reset(self):\n        for tracker in self._trackers.values():\n            tracker.reset()\n\n    def update(self, xyxy, confidence, class_id, frame_index: int, timestamp_s: float):\n        xyxy = np.asarray(xyxy, dtype=np.float32).reshape(-1, 4)\n        confidence = np.asarray(confidence, dtype=np.float32).reshape(-1)\n        class_id = np.asarray(class_id, dtype=np.int32).reshape(-1)\n        if not (len(xyxy) == len(confidence) == len(class_id)):\n            raise ValueError("xyxy/confidence/class_id length mismatch")\n\n        keep = (\n            (confidence >= self.config.detector_low_threshold)\n            & np.isin(class_id, list(RUNTIME_CLASS_NAMES))\n        )\n        xyxy, confidence, class_id = xyxy[keep], confidence[keep], class_id[keep]\n\n        output = []\n        for cid, tracker in self._trackers.items():\n            mask = class_id == cid\n            if mask.any():\n                det = self._sv.Detections(\n                    xyxy=xyxy[mask],\n                    confidence=confidence[mask],\n                    class_id=class_id[mask],\n                )\n            else:\n                det = self._sv.Detections.empty()\n\n            tracked = tracker.update(det, timestamp=float(timestamp_s))\n            if tracked.tracker_id is None:\n                continue\n\n            for box, score, returned_cid, local_tid in zip(\n                tracked.xyxy,\n                tracked.confidence,\n                tracked.class_id,\n                tracked.tracker_id,\n            ):\n                local_tid = int(local_tid)\n                if local_tid < 0:\n                    continue\n                returned_cid = int(returned_cid)\n                if returned_cid != cid:\n                    raise RuntimeError(\n                        f"Runtime class contamination: tracker={cid}, output={returned_cid}"\n                    )\n                output.append(\n                    TrackObservation(\n                        frame_index=int(frame_index),\n                        timestamp_s=float(timestamp_s),\n                        class_id=cid,\n                        class_name=RUNTIME_CLASS_NAMES[cid],\n                        global_track_id=(cid + 1) * ID_NAMESPACE + local_tid,\n                        local_track_id=local_tid,\n                        bbox_xyxy=tuple(float(v) for v in box),\n                        confidence=float(score),\n                    )\n                )\n        return sorted(output, key=lambda o: (o.class_id, o.global_track_id))\n\n\nclass CandidateManager:\n    def __init__(\n        self,\n        quality: QualityConfig | None = None,\n        background: BackgroundConfig | None = None,\n    ):\n        self.quality = quality or QualityConfig()\n        self.background = background or BackgroundConfig()\n        self.states: Dict[int, TrackState] = {}\n        self.anchors: List[BackgroundAnchor] = []\n        self.background_track_ids = set()\n        self.warmup_finalized = False\n\n    def _high_threshold(self, class_id: int) -> float:\n        if class_id == 0:\n            return self.quality.person_high_conf_threshold\n        return self.quality.luggage_high_conf_threshold\n\n    def update_state(self, obs: TrackObservation) -> TrackState:\n        state = self.states.get(obs.global_track_id)\n        if state is None:\n            state = TrackState(\n                class_id=obs.class_id,\n                global_track_id=obs.global_track_id,\n                first_seen_s=obs.timestamp_s,\n                last_seen_s=obs.timestamp_s,\n                first_frame=obs.frame_index,\n                last_frame=obs.frame_index,\n            )\n            self.states[obs.global_track_id] = state\n\n        state.last_seen_s = obs.timestamp_s\n        state.last_frame = obs.frame_index\n        state.hits += 1\n        state.confidence_sum += float(obs.confidence)\n        state.max_confidence = max(state.max_confidence, float(obs.confidence))\n        if obs.confidence >= self._high_threshold(obs.class_id):\n            state.high_conf_hits += 1\n        state.boxes.append(obs.bbox_xyxy)\n        state.centers.append(obs.center)\n        return state\n\n    def finalize_warmup(self):\n        if self.warmup_finalized:\n            return\n\n        anchors = []\n        for state in self.states.values():\n            if state.first_seen_s > self.background.max_first_seen_s:\n                continue\n            if state.age_s < self.background.min_duration_s:\n                continue\n            if state.hits < self.background.min_hits:\n                continue\n            s_norm = state.stationary_norm\n            if not np.isfinite(s_norm) or s_norm > self.background.max_stationary_norm:\n                continue\n\n            anchor = BackgroundAnchor(\n                class_id=state.class_id,\n                bbox_xyxy=state.median_bbox,\n                source_track_id=state.global_track_id,\n                stationary_norm=float(s_norm),\n            )\n            anchors.append(anchor)\n            self.background_track_ids.add(state.global_track_id)\n\n        self.anchors = anchors\n        self.warmup_finalized = True\n\n    def background_match(self, obs: TrackObservation):\n        if obs.global_track_id in self.background_track_ids:\n            return True, 1.0, obs.global_track_id\n\n        best_iou = 0.0\n        best_source = None\n        for anchor in self.anchors:\n            if anchor.class_id != obs.class_id:\n                continue\n            iou = bbox_iou(obs.bbox_xyxy, anchor.bbox_xyxy)\n            if iou > best_iou:\n                best_iou = iou\n                best_source = anchor.source_track_id\n\n        return (\n            best_iou >= self.background.suppress_iou,\n            float(best_iou),\n            best_source,\n        )\n\n    def eligible(self, state: TrackState, is_background: bool) -> bool:\n        if is_background:\n            return False\n\n        if state.class_id == 0:\n            return (\n                state.age_s >= self.quality.person_min_age_s\n                and state.hits >= self.quality.person_min_hits\n                and state.high_conf_hits >= self.quality.person_min_high_hits\n            )\n\n        return (\n            state.age_s >= self.quality.luggage_min_age_s\n            and state.hits >= self.quality.luggage_min_hits\n            and state.high_conf_hits >= self.quality.luggage_min_high_hits\n        )\n\n    def process(\n        self,\n        observations: Sequence[TrackObservation],\n        timestamp_s: float,\n    ):\n        for obs in observations:\n            self.update_state(obs)\n\n        if (\n            not self.warmup_finalized\n            and timestamp_s >= self.background.warmup_s\n        ):\n            self.finalize_warmup()\n\n        enriched = []\n        for obs in observations:\n            state = self.states[obs.global_track_id]\n            is_bg, bg_iou, bg_source = self.background_match(obs)\n            is_eligible = self.eligible(state, is_bg)\n            status = "BACKGROUND" if is_bg else ("ELIGIBLE" if is_eligible else "TRACK_ONLY")\n            enriched.append({\n                "observation": obs,\n                "status": status,\n                "is_background": bool(is_bg),\n                "background_iou": float(bg_iou),\n                "background_source_track_id": bg_source,\n                "eligible": bool(is_eligible),\n                "age_s": float(state.age_s),\n                "hits": int(state.hits),\n                "high_conf_hits": int(state.high_conf_hits),\n                "max_confidence": float(state.max_confidence),\n                "mean_confidence": float(state.mean_confidence),\n            })\n        return enriched\n\n    def summary(self):\n        by_class = defaultdict(list)\n        for state in self.states.values():\n            by_class[RUNTIME_CLASS_NAMES[state.class_id]].append(state)\n\n        out = {\n            "total_tracks": len(self.states),\n            "background_anchor_count": len(self.anchors),\n            "background_track_ids": len(self.background_track_ids),\n            "by_class": {},\n        }\n        for name in RUNTIME_CLASS_NAMES.values():\n            items = by_class.get(name, [])\n            ages = [s.age_s for s in items]\n            out["by_class"][name] = {\n                "tracks": len(items),\n                "mean_duration_s": float(np.mean(ages)) if ages else 0.0,\n                "median_duration_s": float(np.median(ages)) if ages else 0.0,\n                "max_duration_s": float(np.max(ages)) if ages else 0.0,\n                "short_track_ratio_lt_1s": (\n                    float(np.mean([a < 1.0 for a in ages])) if ages else 0.0\n                ),\n                "mean_track_confidence": (\n                    float(np.mean([s.mean_confidence for s in items])) if items else 0.0\n                ),\n            }\n        return out\n\n\ndef write_enriched_jsonl(path, enriched_rows):\n    path = Path(path)\n    path.parent.mkdir(parents=True, exist_ok=True)\n    with path.open("a", encoding="utf-8") as f:\n        for row in enriched_rows:\n            obs = row["observation"]\n            payload = {\n                "frame_index": obs.frame_index,\n                "timestamp_s": obs.timestamp_s,\n                "class_id": obs.class_id,\n                "class_name": obs.class_name,\n                "global_track_id": obs.global_track_id,\n                "local_track_id": obs.local_track_id,\n                "bbox_xyxy": list(obs.bbox_xyxy),\n                "center_xy": list(obs.center),\n                "confidence": obs.confidence,\n                "status": row["status"],\n                "eligible": row["eligible"],\n                "is_background": row["is_background"],\n                "background_iou": row["background_iou"],\n                "background_source_track_id": row["background_source_track_id"],\n                "age_s": row["age_s"],\n                "hits": row["hits"],\n                "high_conf_hits": row["high_conf_hits"],\n                "max_confidence": row["max_confidence"],\n                "mean_confidence": row["mean_confidence"],\n            }\n            f.write(json.dumps(payload, ensure_ascii=False) + "\\n")\n\n\ndef draw_runtime_tracks(\n    frame_bgr,\n    enriched_rows,\n    trails,\n    candidate_only=False,\n    max_trail_points=30,\n):\n    import cv2\n\n    out = frame_bgr.copy()\n    for row in enriched_rows:\n        if candidate_only and not row["eligible"]:\n            continue\n\n        obs = row["observation"]\n        x1, y1, x2, y2 = map(int, obs.bbox_xyxy)\n\n        if row["status"] == "BACKGROUND":\n            color = (110, 110, 110)\n        elif row["status"] == "ELIGIBLE":\n            color = (0, 220, 0) if obs.class_id == 0 else (0, 210, 255)\n        else:\n            color = (180, 180, 180)\n\n        label = (\n            f"{obs.class_name} ID={obs.global_track_id} "\n            f"{obs.confidence:.2f} {row[\'status\']}"\n        )\n        cv2.rectangle(out, (x1, y1), (x2, y2), color, 2 if row["eligible"] else 1)\n        cv2.putText(\n            out,\n            label,\n            (x1, max(18, y1 - 6)),\n            cv2.FONT_HERSHEY_SIMPLEX,\n            0.42,\n            color,\n            1,\n            cv2.LINE_AA,\n        )\n\n        if row["status"] != "BACKGROUND":\n            cx, cy = map(int, obs.center)\n            trail = trails.setdefault(obs.global_track_id, [])\n            trail.append((cx, cy))\n            if len(trail) > max_trail_points:\n                del trail[:-max_trail_points]\n            if len(trail) >= 2 and not candidate_only:\n                pts = np.asarray(trail, dtype=np.int32).reshape(-1, 1, 2)\n                cv2.polylines(out, [pts], False, color, 1)\n\n    return out\n'


# Align the embedded runtime core with the pinned trackers 2.5 API.
EMBEDDED_CORE = EMBEDDED_CORE.replace(
    "tracker.update(det, timestamp=float(timestamp_s))", "tracker.update(det)"
)
EMBEDDED_CORE = EMBEDDED_CORE.replace(
    "is_eligible = self.eligible(state, is_bg)\n            status =",
    "is_eligible = self.eligible(state, is_bg)\n            if not self.warmup_finalized:\n                is_eligible = False\n            status =",
)

def run(cmd,cwd=None,env=None):
    print("$ "+" ".join(map(str,cmd)),flush=True)
    subprocess.run(list(map(str,cmd)),cwd=cwd,env=env,check=True)

def install_deps():
    run([sys.executable,"-m","pip","install","-q",
         "trackers==2.5.0.post0",
         "supervision",
         "opencv-python-headless",
         "gdown",
         "PyYAML",
         "transformers",
         "faster-coco-eval>=1.6.7",
         "calflops",
         "scipy",
         "tensorboard",
         "pycocotools"])

def find_video():
    explicit=os.environ.get("VIDEO_PATH")
    if explicit:
        p=Path(explicit)
        if not p.is_file(): raise FileNotFoundError(p)
        return p
    videos=[]
    for ext in ("*.mp4","*.avi","*.mov","*.mkv"):
        videos.extend(INPUT.rglob(ext))
    if len(videos)!=1:
        raise RuntimeError("Need exactly one test video, or set VIDEO_PATH. Found:\n"+"\n".join(map(str,videos[:30])))
    return videos[0]

def find_checkpoint():
    explicit=os.environ.get("PHASE7A_CKPT")
    if explicit:
        p=Path(explicit)
        if not p.is_file(): raise FileNotFoundError(p)
        return p
    candidates=[p for p in INPUT.rglob("best.pth")
                if any(k in str(p).lower() for k in ("phase7a","person_luggage","person-luggage"))]
    named=list(INPUT.rglob("phase7a_best.pth"))
    candidates=list(dict.fromkeys(named+candidates))
    if len(candidates)!=1:
        raise RuntimeError("Phase7A checkpoint not uniquely found. Set PHASE7A_CKPT.\n"+"\n".join(map(str,candidates[:30])))
    return candidates[0]

def prepare_repo():
    if REPO.exists(): shutil.rmtree(REPO)
    run(["git","clone","https://github.com/Intellindust-AI-Lab/DEIMv2.git",str(REPO)])
    run(["git","checkout","--detach",DEIM_COMMIT],cwd=REPO)
    actual=subprocess.check_output(["git","rev-parse","HEAD"],cwd=REPO,text=True).strip()
    assert actual==DEIM_COMMIT

def patch_profiler_utils():
    """Keep DEIMv2 profiler dependency from blocking inference."""
    path=REPO/"engine"/"misc"/"profiler_utils.py"
    source=path.read_text(encoding="utf-8")
    sentinel="# PHASE7B_V3_OPTIONAL_CALFLOPS"
    if sentinel in source:
        return

    import_needle="from calflops import calculate_flops"
    if source.count(import_needle)!=1:
        raise RuntimeError("Unexpected profiler_utils calflops import layout")
    source=source.replace(
        import_needle,
        """# PHASE7B_V3_OPTIONAL_CALFLOPS
try:
    from calflops import calculate_flops
except Exception:
    calculate_flops = None"""
    )

    needle="""    model_for_info = copy.deepcopy(cfg.model).deploy()\n\n    flops, macs, _ = calculate_flops(model=model_for_info,\n"""
    replacement="""    model_for_info = copy.deepcopy(cfg.model).deploy()\n    if calculate_flops is None:\n        params = sum(p.numel() for p in model_for_info.parameters())\n        del model_for_info\n        return params, {\"Model FLOPs: skipped (calflops unavailable); Params:%s\" % params}\n\n    flops, macs, _ = calculate_flops(model=model_for_info,\n"""
    if source.count(needle)!=1:
        raise RuntimeError("Unexpected profiler_utils calculate_flops layout")
    source=source.replace(needle,replacement,1)

    path.write_text(source,encoding="utf-8")
    print("[OK] profiler_utils patched: calflops optional")

def patch_torchvision():
    path=REPO/"engine"/"data"/"transforms"/"_transforms.py"
    source=path.read_text(encoding="utf-8")
    sentinel="# PHASE7B_KAGGLE_TORCHVISION_COMPAT"
    if sentinel in source: return
    patch=r"""
# PHASE7B_KAGGLE_TORCHVISION_COMPAT
if hasattr(T.Transform, "transform"):
    if hasattr(ConvertPILImage, "_transform") and "transform" not in ConvertPILImage.__dict__:
        ConvertPILImage.transform = ConvertPILImage._transform
    if hasattr(ConvertBoxes, "_transform") and "transform" not in ConvertBoxes.__dict__:
        ConvertBoxes.transform = ConvertBoxes._transform
    if hasattr(PadToSize, "_transform") and "transform" not in PadToSize.__dict__:
        PadToSize.transform = PadToSize._transform
    if hasattr(T.Transform, "make_params") and hasattr(PadToSize, "_get_params") and "make_params" not in PadToSize.__dict__:
        PadToSize.make_params = PadToSize._get_params
"""
    path.write_text(source.rstrip()+"\n"+patch+"\n",encoding="utf-8")

def prepare_backbone():
    dest=REPO/"ckpts"/"vitt_distill.pt"
    dest.parent.mkdir(parents=True,exist_ok=True)
    candidates=list(INPUT.rglob("vitt_distill.pt"))
    if candidates:
        shutil.copy2(candidates[0],dest)
        return dest
    import gdown
    result=gdown.download(id=VITT_GOOGLE_DRIVE_ID,output=str(dest),quiet=False)
    if result is None:
        raise RuntimeError("Backbone download failed. Enable Internet or attach vitt_distill.pt.")
    return dest

def write_eval_config(backbone):
    path=WORK/"phase7b_deimv2_s_eval.yml"
    base=REPO/"configs"/"deimv2"/"deimv2_dinov3_s_coco.yml"
    text=f"""
__include__: ['{base}']
num_classes: 4
remap_mscoco_category: False
eval_spatial_size: [640, 640]

DINOv3STAs:
  weights_path: "{backbone}"

PostProcessor:
  num_top_queries: 300
""".strip()
    path.write_text(text+"\n",encoding="utf-8")
    return path

def load_deim(checkpoint,config):
    sys.path.insert(0,str(REPO))
    from engine.core import YAMLConfig
    cfg=YAMLConfig(str(config),resume=str(checkpoint))
    obj=torch.load(checkpoint,map_location="cpu",weights_only=False)
    state=obj["ema"]["module"] if "ema" in obj else obj["model"]
    info=cfg.model.load_state_dict(state,strict=True)
    print("[MODEL] load_state_dict:",info)
    class Deploy(torch.nn.Module):
        def __init__(self,model,post):
            super().__init__(); self.model=model.deploy(); self.post=post.deploy()
        def forward(self,images,orig_sizes):
            return self.post(self.model(images),orig_sizes)
    return Deploy(cfg.model,cfg.postprocessor).to("cuda:0").eval()

def build_transform():
    import torchvision.transforms as T
    return T.Compose([
        T.Resize((640,640)),
        T.ToTensor(),
        T.Normalize(mean=[0.485,0.456,0.406],std=[0.229,0.224,0.225]),
    ])

@torch.inference_mode()
def infer_pil(model,transform,image):
    tensor=transform(image).unsqueeze(0).to("cuda:0")
    w,h=image.size
    orig=torch.tensor([[w,h]],dtype=torch.float32,device="cuda:0")
    with torch.autocast(device_type="cuda",dtype=torch.float16):
        labels,boxes,scores=model(tensor,orig)
    labels=labels[0].detach().cpu().numpy().astype(np.int32)
    boxes=boxes[0].detach().float().cpu().numpy().astype(np.float32)
    scores=scores[0].detach().float().cpu().numpy().astype(np.float32)
    keep=scores>=DETECTOR_LOW_THRESHOLD
    return boxes[keep],scores[keep],labels[keep]

def positions(length,window,overlap):
    if length<=window: return [0]
    stride=max(1,int(round(window*(1.0-overlap))))
    out=list(range(0,max(1,length-window+1),stride))
    final=length-window
    if out[-1]!=final: out.append(final)
    return sorted(set(out))

def make_tiles(width,height):
    tw=min(TILE_SIZE,width); th=min(TILE_SIZE,height)
    out=[]; seen=set()
    for y0 in positions(height,th,TILE_OVERLAP):
        for x0 in positions(width,tw,TILE_OVERLAP):
            x1=min(width,x0+tw); y1=min(height,y0+th)
            x0=max(0,x1-tw); y0=max(0,y1-th)
            t=(int(x0),int(y0),int(x1),int(y1))
            if t not in seen: seen.add(t); out.append(t)
    return out

def classwise_nms(boxes,scores,labels):
    import torchvision
    if len(scores)==0: return boxes,scores,labels
    keep=torchvision.ops.batched_nms(
        torch.from_numpy(boxes),torch.from_numpy(scores),torch.from_numpy(labels),TILE_NMS_IOU
    )[:MAX_DETS].numpy()
    return boxes[keep],scores[keep],labels[keep]


def runtime_merge_detections(boxes,scores,labels):
    """
    Keep the detector's 4-class head, but change runtime taxonomy to:
      0 person
      1 generic luggage = backpack|handbag|suitcase

    Critical fix:
      luggage NMS is class-agnostic across original luggage subclasses.
    """
    import torchvision

    boxes=np.asarray(boxes,dtype=np.float32).reshape(-1,4)
    scores=np.asarray(scores,dtype=np.float32).reshape(-1)
    labels=np.asarray(labels,dtype=np.int32).reshape(-1)

    stats={
        "raw_person":int(np.sum(labels==0)),
        "raw_backpack":int(np.sum(labels==1)),
        "raw_handbag":int(np.sum(labels==2)),
        "raw_suitcase":int(np.sum(labels==3)),
        "raw_luggage_total":int(np.sum(np.isin(labels,[1,2,3]))),
        "merged_person":0,
        "merged_luggage":0,
        "luggage_duplicates_removed":0,
    }

    out_b=[]; out_s=[]; out_l=[]; out_sub=[]

    # Person: standard NMS.
    pmask=labels==0
    if pmask.any():
        pb=boxes[pmask]; ps=scores[pmask]
        keep=torchvision.ops.nms(
            torch.from_numpy(pb),
            torch.from_numpy(ps),
            PERSON_NMS_IOU,
        ).numpy()
        pb=pb[keep]; ps=ps[keep]
        out_b.append(pb); out_s.append(ps)
        out_l.append(np.zeros(len(keep),dtype=np.int32))
        out_sub.append(np.zeros(len(keep),dtype=np.int32))
        stats["merged_person"]=int(len(keep))

    # Luggage: MERGE subclasses first, then one class-agnostic NMS.
    lmask=np.isin(labels,[1,2,3])
    if lmask.any():
        lb=boxes[lmask]; ls=scores[lmask]; lsub=labels[lmask]
        keep=torchvision.ops.nms(
            torch.from_numpy(lb),
            torch.from_numpy(ls),
            LUGGAGE_NMS_IOU,
        ).numpy()
        lb=lb[keep]; ls=ls[keep]; lsub=lsub[keep]
        out_b.append(lb); out_s.append(ls)
        out_l.append(np.ones(len(keep),dtype=np.int32))
        out_sub.append(lsub.astype(np.int32))
        stats["merged_luggage"]=int(len(keep))
        stats["luggage_duplicates_removed"]=int(stats["raw_luggage_total"]-len(keep))

    if not out_s:
        return (
            np.empty((0,4),np.float32),
            np.empty((0,),np.float32),
            np.empty((0,),np.int32),
            np.empty((0,),np.int32),
            stats,
        )

    b=np.concatenate(out_b)
    s=np.concatenate(out_s)
    l=np.concatenate(out_l)
    sub=np.concatenate(out_sub)

    order=np.argsort(-s)
    return b[order],s[order],l[order],sub[order],stats


def select_mode(width,height):
    if MODE in ("full640","tile768_overlap20"): return MODE
    if MODE!="auto": raise ValueError(f"Unknown INFERENCE_MODE={MODE}")
    return "tile768_overlap20" if width*height>=AUTO_TILE_MIN_PIXELS else "full640"

def detect_frame(model,transform,frame_bgr,mode):
    import cv2
    from PIL import Image
    image=Image.fromarray(cv2.cvtColor(frame_bgr,cv2.COLOR_BGR2RGB))
    width,height=image.size
    if mode=="full640":
        b,s,l=infer_pil(model,transform,image)
        return b,s,l,1
    all_b=[]; all_s=[]; all_l=[]
    tiles=make_tiles(width,height)
    for x0,y0,x1,y1 in tiles:
        crop=image.crop((x0,y0,x1,y1))
        b,s,l=infer_pil(model,transform,crop)
        if len(s)==0: continue
        b=b.copy(); b[:,[0,2]]+=x0; b[:,[1,3]]+=y0
        all_b.append(b); all_s.append(s); all_l.append(l)
    if not all_s:
        return np.empty((0,4),np.float32),np.empty((0,),np.float32),np.empty((0,),np.int32),len(tiles)
    b=np.concatenate(all_b); s=np.concatenate(all_s); l=np.concatenate(all_l)
    b,s,l=classwise_nms(b,s,l)
    return b,s,l,len(tiles)

def main():
    if not torch.cuda.is_available(): raise RuntimeError("GPU required.")
    install_deps()

    # Self-contained runner: materialize embedded core automatically.
    core_runtime = WORK / "phase7b1_runtime_core.py"
    core_runtime.write_text(EMBEDDED_CORE, encoding="utf-8")
    print("[CORE] materialized:", core_runtime)
    sys.path.insert(0, str(WORK))
    from phase7b1_runtime_core import (
        RuntimeByteTrack,
        TrackerConfig,
        QualityConfig,
        BackgroundConfig,
        CandidateManager,
        write_enriched_jsonl,
        draw_runtime_tracks,
    )

    video_path=find_video()
    checkpoint=find_checkpoint()
    print("[INPUT] video:",video_path)
    print("[INPUT] checkpoint:",checkpoint)

    prepare_repo()
    patch_profiler_utils()
    patch_torchvision()
    backbone=prepare_backbone()
    config=write_eval_config(backbone)
    os.environ["TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD"]="1"

    try:
        import calflops
        print("[OK] calflops import")
    except Exception as exc:
        print("[WARN] calflops unavailable; profiler fallback active:",repr(exc))
    import scipy
    print("[OK] scipy import")

    model=load_deim(checkpoint,config)
    transform=build_transform()

    import cv2
    cap=cv2.VideoCapture(str(video_path))
    if not cap.isOpened(): raise RuntimeError(f"Could not open {video_path}")
    fps=float(cap.get(cv2.CAP_PROP_FPS)); width=int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)); height=int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames=int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if not np.isfinite(fps) or fps<=0: fps=30.0
    selected_mode=select_mode(width,height)
    print(f"[VIDEO] {width}x{height} @ {fps:.3f} FPS frames={total_frames} mode={selected_mode}")

    OUT.mkdir(parents=True,exist_ok=True)
    all_video_out=OUT/"annotated_all_tracks.mp4"
    candidate_video_out=OUT/"annotated_candidate_view.mp4"
    jsonl_out=OUT/"tracks_v4.jsonl"
    summary_out=OUT/"summary_v4.json"
    anchors_out=OUT/"background_anchors.json"

    if jsonl_out.exists(): jsonl_out.unlink()

    writer_all=cv2.VideoWriter(str(all_video_out),cv2.VideoWriter_fourcc(*"mp4v"),fps,(width,height))
    writer_candidate=cv2.VideoWriter(str(candidate_video_out),cv2.VideoWriter_fourcc(*"mp4v"),fps,(width,height))
    if not writer_all.isOpened() or not writer_candidate.isOpened():
        raise RuntimeError("Could not create output videos")

    tracker=RuntimeByteTrack(
        frame_rate=fps,
        config=TrackerConfig(
            detector_low_threshold=0.05,
            track_activation_threshold=0.25,
            high_conf_det_threshold=0.60,
            minimum_consecutive_frames=2,
            minimum_iou_threshold=0.10,
            lost_track_buffer=30,
        ),
    )

    manager=CandidateManager(
        quality=QualityConfig(
            luggage_min_age_s=LUGGAGE_EVENT_MIN_AGE,
            luggage_high_conf_threshold=LUGGAGE_EVENT_HIGH_CONF,
            luggage_min_high_hits=LUGGAGE_EVENT_MIN_HIGH_HITS,
        ),
        background=BackgroundConfig(warmup_s=WARMUP_SECONDS),
    )

    trails_all={}
    raw_original_counts=Counter()
    runtime_detection_counts=Counter()
    runtime_confirmed_counts=Counter()
    status_counts=Counter()
    merge_totals=Counter()

    processed=0; total_tiles=0; frame_index=0; start=time.perf_counter()
    max_frames=int(round(MAX_SECONDS*fps)) if MAX_SECONDS>0 else total_frames

    while True:
        ok,frame=cap.read()
        if not ok: break
        if max_frames>0 and processed>=max_frames: break
        ts=frame_index/fps
        boxes,scores,labels,tile_count=detect_frame(model,transform,frame,selected_mode)

        for cid in labels.tolist():
            if cid in ORIGINAL_CLASS_NAMES:
                raw_original_counts[ORIGINAL_CLASS_NAMES[cid]]+=1

        r_boxes,r_scores,r_labels,r_subclasses,merge_stats=runtime_merge_detections(
            boxes,scores,labels
        )
        for k,v in merge_stats.items():
            merge_totals[k]+=int(v)

        for cid in r_labels.tolist():
            runtime_detection_counts[RUNTIME_CLASS_NAMES[cid]]+=1

        obs=tracker.update(
            r_boxes,r_scores,r_labels,
            frame_index=frame_index,
            timestamp_s=ts,
        )
        for item in obs:
            runtime_confirmed_counts[item.class_name]+=1

        enriched=manager.process(obs,timestamp_s=ts)
        for row in enriched:
            status_counts[row["status"]]+=1
        write_enriched_jsonl(jsonl_out,enriched)

        annotated_all=draw_runtime_tracks(
            frame,enriched,trails_all,
            candidate_only=False,
            max_trail_points=max(10,int(round(fps))),
        )
        annotated_candidate=draw_runtime_tracks(
            frame,enriched,{},
            candidate_only=True,
            max_trail_points=0,
        )

        info=(
            f"mode={selected_mode} frame={frame_index} "
            f"tracks={len(obs)} eligible={sum(int(r['eligible']) for r in enriched)} "
            f"bg={sum(int(r['is_background']) for r in enriched)}"
        )
        cv2.putText(annotated_all,info,(12,25),cv2.FONT_HERSHEY_SIMPLEX,0.55,(255,255,255),2,cv2.LINE_AA)
        cv2.putText(annotated_candidate,info,(12,25),cv2.FONT_HERSHEY_SIMPLEX,0.55,(255,255,255),2,cv2.LINE_AA)

        writer_all.write(annotated_all)
        writer_candidate.write(annotated_candidate)
        frame_index+=1; processed+=1; total_tiles+=tile_count
        if processed==1 or processed%max(1,int(fps*10))==0:
            elapsed=time.perf_counter()-start
            print(f"[RUN] frames={processed} time={processed/fps:.1f}s wall_fps={processed/max(elapsed,1e-9):.2f} avg_tiles={total_tiles/processed:.2f}")

    elapsed=time.perf_counter()-start
    cap.release()
    writer_all.release()
    writer_candidate.release()

    # Ensure anchors are materialized even when video is shorter than warmup.
    if not manager.warmup_finalized:
        manager.finalize_warmup()

    anchors_payload=[
        {
            "class_id":a.class_id,
            "class_name":RUNTIME_CLASS_NAMES[a.class_id],
            "bbox_xyxy":list(a.bbox_xyxy),
            "source_track_id":a.source_track_id,
            "stationary_norm":a.stationary_norm,
        }
        for a in manager.anchors
    ]
    anchors_out.write_text(
        json.dumps(anchors_payload,ensure_ascii=False,indent=2),
        encoding="utf-8",
    )

    summary=manager.summary()
    raw_luggage=merge_totals.get("raw_luggage_total",0)
    merged_luggage=merge_totals.get("merged_luggage",0)
    summary.update({
        "phase":"7B.1_generic_luggage",
        "video_path":str(video_path),
        "checkpoint":str(checkpoint),
        "video_width":width,"video_height":height,"source_fps":fps,
        "processed_frames":processed,"processed_video_seconds":processed/fps,
        "wall_seconds":elapsed,"pipeline_fps":processed/max(elapsed,1e-9),
        "inference_mode":selected_mode,
        "average_tiles_per_frame":total_tiles/max(processed,1),

        "raw_original_detections":dict(raw_original_counts),
        "runtime_detections_after_merge_nms":dict(runtime_detection_counts),
        "runtime_confirmed_observations":dict(runtime_confirmed_counts),
        "status_observations":dict(status_counts),

        "merge_totals":dict(merge_totals),
        "luggage_duplicate_reduction_ratio":(
            1.0-(merged_luggage/max(raw_luggage,1))
        ),

        "config":{
            "person_nms_iou":PERSON_NMS_IOU,
            "luggage_cross_class_nms_iou":LUGGAGE_NMS_IOU,
            "warmup_seconds":WARMUP_SECONDS,
            "luggage_event_min_age_s":LUGGAGE_EVENT_MIN_AGE,
            "luggage_event_high_conf":LUGGAGE_EVENT_HIGH_CONF,
            "luggage_event_min_high_hits":LUGGAGE_EVENT_MIN_HIGH_HITS,
            "track_activation_threshold":0.25,
            "high_conf_det_threshold":0.60,
        },
        "notes":[
            "This phase produces event-eligible track candidates, NOT abandoned-object alarms.",
            "Backpack/handbag/suitcase are merged to generic luggage before tracking.",
            "Background suppression assumes the startup warmup window contains no true abandoned-object event.",
            "No MOT ground truth: do not claim IDF1/HOTA/MOTA.",
        ],
    })
    summary_out.write_text(
        json.dumps(summary,ensure_ascii=False,indent=2),
        encoding="utf-8",
    )

    print("\n"+"="*100)
    print("PHASE 7B.1 GENERIC-LUGGAGE FILTER COMPLETE")
    print("="*100)
    print(json.dumps(summary,indent=2))
    print("All tracks video:",all_video_out)
    print("Candidate view:",candidate_video_out)
    print("Tracks:",jsonl_out)
    print("Background anchors:",anchors_out)
    print("Summary:",summary_out)
    print("="*100)

if __name__=="__main__":
    main()
