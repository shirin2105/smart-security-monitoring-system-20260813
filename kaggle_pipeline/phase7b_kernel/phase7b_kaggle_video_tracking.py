"""
PHASE 7B v3 — ROBUST SELF-CONTAINED DEIMv2 Phase7A + class-wise ByteTrack on video

NOT a training job.

Required Kaggle Inputs:
1) Phase7A best.pth
2) one test video (.mp4/.avi/.mov/.mkv)
3) optional vitt_distill.pt (otherwise Internet ON)

phase7b_core.py is EMBEDDED; do not attach it separately.

Outputs:
  /kaggle/working/phase7b_tracking/annotated_tracking.mp4
  /kaggle/working/phase7b_tracking/tracks.jsonl
  /kaggle/working/phase7b_tracking/summary.json

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
OUT=WORK/"phase7b_tracking"

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
CLASS_NAMES={0:"person",1:"backpack",2:"handbag",3:"suitcase"}

EMBEDDED_CORE = 'from __future__ import annotations\nfrom dataclasses import dataclass, field\nfrom collections import defaultdict\nfrom typing import Dict, List, Sequence, Tuple\nimport json\nfrom pathlib import Path\nimport numpy as np\n\nCLASS_NAMES = {0: "person", 1: "backpack", 2: "handbag", 3: "suitcase"}\nID_NAMESPACE = 1_000_000\n\n@dataclass\nclass TrackerConfig:\n    detector_low_threshold: float = 0.05\n    track_activation_threshold: float = 0.25\n    high_conf_det_threshold: float = 0.25\n    minimum_consecutive_frames: int = 2\n    minimum_iou_threshold: float = 0.10\n    lost_track_buffer: int = 30\n\n@dataclass\nclass TrackObservation:\n    frame_index: int\n    timestamp_s: float\n    class_id: int\n    class_name: str\n    global_track_id: int\n    local_track_id: int\n    bbox_xyxy: Tuple[float, float, float, float]\n    confidence: float\n\n    @property\n    def center(self):\n        x1, y1, x2, y2 = self.bbox_xyxy\n        return ((x1+x2)/2.0, (y1+y2)/2.0)\n\n@dataclass\nclass TrackRecord:\n    class_id: int\n    global_track_id: int\n    first_frame: int\n    last_frame: int\n    first_timestamp_s: float\n    last_timestamp_s: float\n    observations: int = 0\n    confidence_sum: float = 0.0\n    centers: List[Tuple[float, float]] = field(default_factory=list)\n\n    def update(self, obs: TrackObservation):\n        self.last_frame = obs.frame_index\n        self.last_timestamp_s = obs.timestamp_s\n        self.observations += 1\n        self.confidence_sum += float(obs.confidence)\n        self.centers.append(obs.center)\n\n    @property\n    def duration_s(self):\n        return max(0.0, self.last_timestamp_s - self.first_timestamp_s)\n\n    @property\n    def mean_confidence(self):\n        return self.confidence_sum / max(1, self.observations)\n\nclass ClasswiseByteTrack:\n    """Separate ByteTrack instance per semantic class."""\n    def __init__(self, frame_rate: float, config: TrackerConfig | None = None):\n        self.config = config or TrackerConfig()\n        import supervision as sv\n        from trackers import ByteTrackTracker\n        self._sv = sv\n        self._trackers = {\n            cid: ByteTrackTracker(\n                lost_track_buffer=self.config.lost_track_buffer,\n                frame_rate=max(float(frame_rate), 1e-6),\n                track_activation_threshold=self.config.track_activation_threshold,\n                minimum_consecutive_frames=self.config.minimum_consecutive_frames,\n                minimum_iou_threshold=self.config.minimum_iou_threshold,\n                high_conf_det_threshold=self.config.high_conf_det_threshold,\n            )\n            for cid in CLASS_NAMES\n        }\n\n    def reset(self):\n        for tracker in self._trackers.values():\n            tracker.reset()\n\n    def update(self, xyxy, confidence, class_id, frame_index: int, timestamp_s: float):\n        xyxy = np.asarray(xyxy, dtype=np.float32).reshape(-1, 4)\n        confidence = np.asarray(confidence, dtype=np.float32).reshape(-1)\n        class_id = np.asarray(class_id, dtype=np.int32).reshape(-1)\n        if not (len(xyxy) == len(confidence) == len(class_id)):\n            raise ValueError("xyxy/confidence/class_id length mismatch")\n\n        keep = (confidence >= self.config.detector_low_threshold) & np.isin(class_id, list(CLASS_NAMES))\n        xyxy, confidence, class_id = xyxy[keep], confidence[keep], class_id[keep]\n        output = []\n\n        for cid, tracker in self._trackers.items():\n            mask = class_id == cid\n            if mask.any():\n                det = self._sv.Detections(\n                    xyxy=xyxy[mask],\n                    confidence=confidence[mask],\n                    class_id=class_id[mask],\n                )\n            else:\n                det = self._sv.Detections.empty()\n\n            tracked = tracker.update(det, timestamp=float(timestamp_s))\n            if tracked.tracker_id is None:\n                continue\n\n            for box, score, ret_cid, local_tid in zip(\n                tracked.xyxy, tracked.confidence, tracked.class_id, tracked.tracker_id\n            ):\n                local_tid = int(local_tid)\n                if local_tid < 0:\n                    continue\n                ret_cid = int(ret_cid)\n                if ret_cid != cid:\n                    raise RuntimeError(f"Class contamination tracker={cid} output={ret_cid}")\n                output.append(TrackObservation(\n                    frame_index=int(frame_index),\n                    timestamp_s=float(timestamp_s),\n                    class_id=cid,\n                    class_name=CLASS_NAMES[cid],\n                    global_track_id=(cid + 1) * ID_NAMESPACE + local_tid,\n                    local_track_id=local_tid,\n                    bbox_xyxy=tuple(float(v) for v in box),\n                    confidence=float(score),\n                ))\n        return sorted(output, key=lambda x: (x.class_id, x.global_track_id))\n\nclass TrackHistory:\n    def __init__(self):\n        self.records: Dict[int, TrackRecord] = {}\n        self.confirmed_observations = 0\n\n    def update(self, observations: Sequence[TrackObservation]):\n        self.confirmed_observations += len(observations)\n        for obs in observations:\n            rec = self.records.get(obs.global_track_id)\n            if rec is None:\n                rec = TrackRecord(\n                    class_id=obs.class_id,\n                    global_track_id=obs.global_track_id,\n                    first_frame=obs.frame_index,\n                    last_frame=obs.frame_index,\n                    first_timestamp_s=obs.timestamp_s,\n                    last_timestamp_s=obs.timestamp_s,\n                )\n                self.records[obs.global_track_id] = rec\n            rec.update(obs)\n\n    def summary(self):\n        by_class = defaultdict(list)\n        for rec in self.records.values():\n            by_class[CLASS_NAMES[rec.class_id]].append(rec)\n        out = {"total_tracks": len(self.records), "confirmed_observations": self.confirmed_observations, "by_class": {}}\n        for name in CLASS_NAMES.values():\n            items = by_class.get(name, [])\n            durations = [r.duration_s for r in items]\n            obs_counts = [r.observations for r in items]\n            out["by_class"][name] = {\n                "tracks": len(items),\n                "mean_duration_s": float(np.mean(durations)) if durations else 0.0,\n                "median_duration_s": float(np.median(durations)) if durations else 0.0,\n                "max_duration_s": float(np.max(durations)) if durations else 0.0,\n                "mean_observations": float(np.mean(obs_counts)) if obs_counts else 0.0,\n                "short_track_ratio_lt_1s": float(np.mean([d < 1.0 for d in durations])) if durations else 0.0,\n                "mean_track_confidence": float(np.mean([r.mean_confidence for r in items])) if items else 0.0,\n            }\n        return out\n\ndef append_jsonl(path, observations):\n    path = Path(path)\n    path.parent.mkdir(parents=True, exist_ok=True)\n    with path.open("a", encoding="utf-8") as f:\n        for obs in observations:\n            row = {\n                "frame_index": obs.frame_index,\n                "timestamp_s": obs.timestamp_s,\n                "class_id": obs.class_id,\n                "class_name": obs.class_name,\n                "global_track_id": obs.global_track_id,\n                "local_track_id": obs.local_track_id,\n                "bbox_xyxy": list(obs.bbox_xyxy),\n                "confidence": obs.confidence,\n                "center_xy": list(obs.center),\n            }\n            f.write(json.dumps(row, ensure_ascii=False) + "\\n")\n\ndef draw_tracks(frame_bgr, observations, trails, max_trail_points=30):\n    import cv2\n    out = frame_bgr.copy()\n    colors = {0:(0,220,0), 1:(255,180,0), 2:(255,0,220), 3:(0,180,255)}\n    for obs in observations:\n        x1,y1,x2,y2 = map(int, obs.bbox_xyxy)\n        color = colors.get(obs.class_id, (255,255,255))\n        label = f"{obs.class_name} ID={obs.global_track_id} {obs.confidence:.2f}"\n        cv2.rectangle(out, (x1,y1), (x2,y2), color, 2)\n        cv2.putText(out, label, (x1,max(18,y1-7)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1, cv2.LINE_AA)\n        cx,cy = map(int, obs.center)\n        trail = trails.setdefault(obs.global_track_id, [])\n        trail.append((cx,cy))\n        if len(trail) > max_trail_points:\n            del trail[:-max_trail_points]\n        if len(trail) >= 2:\n            pts = np.asarray(trail, dtype=np.int32).reshape(-1,1,2)\n            cv2.polylines(out, [pts], False, color, 2)\n    return out\n'


# Align the embedded core with the pinned trackers 2.5 API.
EMBEDDED_CORE = EMBEDDED_CORE.replace(
    "tracker.update(det, timestamp=float(timestamp_s))", "tracker.update(det)"
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
    core_runtime = WORK / "phase7b_core.py"
    core_runtime.write_text(EMBEDDED_CORE, encoding="utf-8")
    print("[CORE] materialized:", core_runtime)
    sys.path.insert(0, str(WORK))
    from phase7b_core import (
        ClasswiseByteTrack,
        TrackerConfig,
        TrackHistory,
        append_jsonl,
        draw_tracks,
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
    video_out=OUT/"annotated_tracking.mp4"; jsonl_out=OUT/"tracks.jsonl"; summary_out=OUT/"summary.json"
    if jsonl_out.exists(): jsonl_out.unlink()
    writer=cv2.VideoWriter(str(video_out),cv2.VideoWriter_fourcc(*"mp4v"),fps,(width,height))
    if not writer.isOpened(): raise RuntimeError("Could not create output video")

    tracker=ClasswiseByteTrack(
        frame_rate=fps,
        config=TrackerConfig(
            detector_low_threshold=0.05,
            track_activation_threshold=0.25,
            high_conf_det_threshold=0.25,
            minimum_consecutive_frames=2,
            minimum_iou_threshold=0.10,
            lost_track_buffer=30,
        ),
    )
    history=TrackHistory(); trails={}
    raw_counts=Counter(); confirmed_counts=Counter()
    processed=0; total_tiles=0; frame_index=0; start=time.perf_counter()
    max_frames=int(round(MAX_SECONDS*fps)) if MAX_SECONDS>0 else total_frames

    while True:
        ok,frame=cap.read()
        if not ok: break
        if max_frames>0 and processed>=max_frames: break
        ts=frame_index/fps
        boxes,scores,labels,tile_count=detect_frame(model,transform,frame,selected_mode)
        for cid in labels.tolist():
            if cid in CLASS_NAMES: raw_counts[CLASS_NAMES[cid]]+=1
        obs=tracker.update(boxes,scores,labels,frame_index=frame_index,timestamp_s=ts)
        for item in obs: confirmed_counts[item.class_name]+=1
        history.update(obs); append_jsonl(jsonl_out,obs)
        annotated=draw_tracks(frame,obs,trails,max_trail_points=max(10,int(round(fps))))
        cv2.putText(annotated,f"mode={selected_mode} frame={frame_index} confirmed={len(obs)}",
                    (12,25),cv2.FONT_HERSHEY_SIMPLEX,0.6,(255,255,255),2,cv2.LINE_AA)
        writer.write(annotated)
        frame_index+=1; processed+=1; total_tiles+=tile_count
        if processed==1 or processed%max(1,int(fps*10))==0:
            elapsed=time.perf_counter()-start
            print(f"[RUN] frames={processed} time={processed/fps:.1f}s wall_fps={processed/max(elapsed,1e-9):.2f} avg_tiles={total_tiles/processed:.2f}")

    elapsed=time.perf_counter()-start
    cap.release(); writer.release()

    summary=history.summary()
    summary.update({
        "video_path":str(video_path),
        "checkpoint":str(checkpoint),
        "video_width":width,"video_height":height,"source_fps":fps,
        "processed_frames":processed,"processed_video_seconds":processed/fps,
        "wall_seconds":elapsed,"pipeline_fps":processed/max(elapsed,1e-9),
        "inference_mode":selected_mode,"average_tiles_per_frame":total_tiles/max(processed,1),
        "raw_detections_by_class":dict(raw_counts),
        "confirmed_observations_by_class":dict(confirmed_counts),
        "notes":"No MOT GT: do not claim IDF1/HOTA/MOTA from this run."
    })
    summary_out.write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf-8")

    print("\n"+"="*100)
    print("PHASE 7B TRACKING COMPLETE")
    print("="*100)
    print(json.dumps(summary,indent=2))
    print("Annotated:",video_out)
    print("Tracks:",jsonl_out)
    print("Summary:",summary_out)
    print("="*100)

if __name__=="__main__":
    main()
