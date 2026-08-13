"""
PHASE 7A — Person + luggage detector for abandoned-object MVP
==============================================================

Goal
----
Stop optimizing generic VisDrone AP and build the detector actually needed by
the abandoned-object pipeline:

    0 person
    1 backpack
    2 handbag
    3 suitcase

Data strategy
-------------
- VisDrone contributes high-angle / distant PERSON examples.
  raw VisDrone 1=pedestrian and 2=people are merged -> person=0.
- COCO contributes luggage semantics.
  Only COCO images containing >=1 backpack/handbag/suitcase are selected.
  On those selected images, annotations for person + luggage are retained.

This avoids letting COCO's huge person class dominate the high-angle signal.

Important
---------
Attach ONE COCO 2017 dataset to Kaggle containing:
  instances_train2017.json
  instances_val2017.json
  train2017 images
  val2017 images

Also attach the existing VisDrone dataset and the Phase-4 DEIMv2 best checkpoint.

The script:
  1) builds 4-class COCO-format train/val manifests using absolute image paths;
  2) smoke-tests DEIMv2-S;
  3) fine-tunes for 20 epochs from Phase-4 VisDrone best.pth;
  4) evaluates best checkpoint full640 + tile768/20;
  5) reports combined metrics, VisDrone-person metrics, COCO-luggage metrics,
     plus per-class AP/AR.

No S4. No EdgeCrafter. No tracking yet.
"""

import os
import sys
import json
import time
import shutil
import subprocess
from pathlib import Path
from collections import Counter, defaultdict

import torch

INPUT = Path("/kaggle/input")
WORK = Path("/kaggle/working")
REPO = WORK / "DEIMv2"

DEIM_COMMIT = "0fff8d4dcdc272e6cf2d84be31399db471357941"
VITT_GOOGLE_DRIVE_ID = "1YMTq_woOLjAcZnHSYNTsNg7f0ahj5LPs"

TARGET_CATEGORIES = [
    {"id": 0, "name": "person", "supercategory": "person"},
    {"id": 1, "name": "backpack", "supercategory": "luggage"},
    {"id": 2, "name": "handbag", "supercategory": "luggage"},
    {"id": 3, "name": "suitcase", "supercategory": "luggage"},
]
TARGET_NAMES = ["person", "backpack", "handbag", "suitcase"]
NUM_CLASSES = 4

VISDRONE_TO_TARGET = {
    1: 0,  # pedestrian -> person
    2: 0,  # people -> person
}
COCO_TO_TARGET = {
    1: 0,   # person
    27: 1,  # backpack
    31: 2,  # handbag
    33: 3,  # suitcase
}
COCO_LUGGAGE_IDS = {27, 31, 33}

INPUT_SIZE = 640
EPOCHS = 20
TRAIN_TOTAL_BATCH = 16
VAL_TOTAL_BATCH = 16
NUM_WORKERS_PER_RANK = 4

BACKBONE_LR = 1e-5
MODEL_LR = 2e-4
WEIGHT_DECAY = 1e-4
WARMUP_STEPS = 500
LR_MILESTONES = [16]
LR_GAMMA = 0.1
CHECKPOINT_FREQ = 5

PHOTO_DISTORT_P = 0.30
IOU_CROP_P = 0.50

RUN_SMOKE = True
SMOKE_TRAIN_IMAGES_PER_SOURCE = 32
SMOKE_VAL_IMAGES_PER_SOURCE = 8

DATA_DIR = WORK / "phase7a_person_luggage_dataset"
TRAIN_ANN = DATA_DIR / "train_4class.json"
VAL_ANN = DATA_DIR / "val_4class.json"
VAL_VISDRONE_ANN = DATA_DIR / "val_visdrone_person.json"
VAL_COCO_ANN = DATA_DIR / "val_coco_luggage.json"
DATA_AUDIT = DATA_DIR / "dataset_audit.json"

SMOKE_TRAIN_ANN = DATA_DIR / "smoke_train.json"
SMOKE_VAL_ANN = DATA_DIR / "smoke_val.json"

CONFIG_FILE = WORK / "phase7a_deimv2_s_person_luggage.yml"
SMOKE_CONFIG = WORK / "phase7a_deimv2_s_smoke.yml"

OUTPUT_DIR = WORK / "outputs" / "phase7a_deimv2_s_person_luggage"
SMOKE_OUTPUT = WORK / "outputs" / "phase7a_deimv2_s_smoke"

EVAL_DIR = WORK / "phase7a_eval"
EVAL_SUMMARY = EVAL_DIR / "phase7a_eval_summary.json"

TILE_SIZE = 768
TILE_OVERLAP = 0.20
SCORE_THRESHOLD = 0.001
NMS_IOU = 0.60
MAX_DETS = 300

COCO_METRIC_NAMES = [
    "AP50_95", "AP50", "AP75",
    "AP_small", "AP_medium", "AP_large",
    "AR_1", "AR_10", "AR_100",
    "AR_small", "AR_medium", "AR_large",
]


def run(cmd, cwd=None, env=None, timeout=None):
    print("\n$ " + " ".join(map(str, cmd)), flush=True)
    return subprocess.run(
        list(map(str, cmd)),
        cwd=cwd,
        env=env,
        check=True,
        timeout=timeout,
    )


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save_json(path, data, indent=None):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(
        json.dumps(data, ensure_ascii=False, indent=indent),
        encoding="utf-8",
    )


def print_env():
    import torchvision

    print("=" * 92)
    print("PHASE 7A — PERSON + LUGGAGE / DEIMv2-S")
    print("=" * 92)
    print("Python:", sys.version)
    print("torch:", torch.__version__)
    print("torchvision:", torchvision.__version__)
    print("CUDA available:", torch.cuda.is_available())

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA GPU is required.")

    print("Visible GPUs:", torch.cuda.device_count())
    for i in range(torch.cuda.device_count()):
        print(
            f"GPU {i}: {torch.cuda.get_device_name(i)} | "
            f"capability={torch.cuda.get_device_capability(i)}"
        )

    if torch.cuda.device_count() < 2:
        print(
            "[WARN] Only one GPU visible. Full train will fall back to "
            "global batch 8."
        )

    print("=" * 92)


def install_dependencies():
    run([
        sys.executable, "-m", "pip", "install", "-q",
        "faster-coco-eval>=1.6.7",
        "PyYAML",
        "tensorboard",
        "calflops",
        "scipy",
        "transformers",
        "gdown",
        "pycocotools",
    ])


def find_exactly_one(filename):
    matches = list(INPUT.rglob(filename))
    if len(matches) != 1:
        raise FileNotFoundError(
            f"Expected exactly one {filename} in Kaggle Input; "
            f"found {len(matches)}:\n"
            + "\n".join(map(str, matches[:30]))
        )
    return matches[0]


def find_phase4_checkpoint():
    explicit = list(INPUT.rglob("deimv2_phase4_best.pth"))
    if len(explicit) == 1:
        print("[CKPT] explicit Phase-4 checkpoint:", explicit[0])
        return explicit[0]
    if len(explicit) > 1:
        raise RuntimeError("Multiple deimv2_phase4_best.pth files found.")

    candidates = []
    for p in INPUT.rglob("best.pth"):
        s = str(p).lower()
        if "deim" in s and "visdrone" in s and "phase4" in s:
            candidates.append(p)

    if len(candidates) == 1:
        print("[CKPT] discovered Phase-4 checkpoint:", candidates[0])
        return candidates[0]

    preferred = (
        INPUT
        / "datasets"
        / "shirin21st"
        / "deimv2-s-visdrone-phase4-best"
        / "best.pth"
    )
    if preferred.is_file():
        print("[CKPT] preferred Phase-4 checkpoint:", preferred)
        return preferred

    raise FileNotFoundError(
        "Phase-4 DEIMv2 VisDrone best checkpoint not found.\n"
        "Attach it to Kaggle, preferably renamed to "
        "`deimv2_phase4_best.pth`."
    )


IMAGE_PATHS_BY_NAME = None


def build_image_path_index():
    global IMAGE_PATHS_BY_NAME
    if IMAGE_PATHS_BY_NAME is not None:
        return IMAGE_PATHS_BY_NAME

    index = defaultdict(list)
    print("[DATA] indexing Kaggle input paths once...", flush=True)
    for candidate in INPUT.rglob("*"):
        if candidate.is_file():
            index[candidate.name].append(candidate)
    IMAGE_PATHS_BY_NAME = index
    print(
        f"[DATA] indexed {sum(map(len, index.values()))} files ",
        f"across {len(index)} basenames",
        flush=True,
    )
    return IMAGE_PATHS_BY_NAME


def resolve_image_path(file_name, split_hint):
    p = Path(file_name)

    if p.is_absolute() and p.is_file():
        return p

    matches = list(build_image_path_index().get(p.name, []))
    if not matches:
        raise FileNotFoundError(
            f"Could not locate image {file_name!r} under /kaggle/input"
        )

    suffix_matches = [
        m for m in matches
        if str(m).endswith(str(p))
    ]
    if suffix_matches:
        matches = suffix_matches

    split_matches = [
        match for match in matches
        if split_hint.lower() in str(match).lower()
    ]
    if split_matches:
        matches = split_matches

    if len(matches) != 1:
        raise RuntimeError(
            f"Ambiguous image path for {file_name!r} ({split_hint}); "
            f"found {len(matches)} matches:\n"
            + "\n".join(map(str, sorted(matches)[:30]))
        )
    return matches[0]


def validate_coco_category_ids(coco):
    by_id = {
        int(cat["id"]): str(cat["name"]).strip().lower()
        for cat in coco["categories"]
    }
    expected = {
        1: "person",
        27: "backpack",
        31: "handbag",
        33: "suitcase",
    }
    for cid, name in expected.items():
        if by_id.get(cid) != name:
            raise RuntimeError(
                f"COCO category mismatch for id={cid}: "
                f"expected={name}, got={by_id.get(cid)}"
            )


def remap_annotation(ann, new_id, new_image_id, target_category):
    bbox = [float(x) for x in ann["bbox"]]
    if len(bbox) != 4 or bbox[2] <= 0 or bbox[3] <= 0:
        return None

    item = {
        "id": int(new_id),
        "image_id": int(new_image_id),
        "category_id": int(target_category),
        "bbox": bbox,
        "area": float(ann.get("area", bbox[2] * bbox[3])),
        "iscrowd": int(ann.get("iscrowd", 0)),
        "source_annotation_id": int(ann.get("id", -1)),
        "source_category_id": int(ann["category_id"]),
    }
    return item


def build_split(split, visdrone_source, coco_source):
    vd = load_json(visdrone_source)
    coco = load_json(coco_source)
    validate_coco_category_ids(coco)

    vd_anns_by_image = defaultdict(list)
    for ann in vd["annotations"]:
        raw = int(ann["category_id"])
        if raw in VISDRONE_TO_TARGET:
            vd_anns_by_image[int(ann["image_id"])].append(ann)

    coco_anns_by_image = defaultdict(list)
    coco_luggage_images = set()

    for ann in coco["annotations"]:
        cid = int(ann["category_id"])
        image_id = int(ann["image_id"])

        if cid in COCO_LUGGAGE_IDS:
            coco_luggage_images.add(image_id)

        if cid in COCO_TO_TARGET:
            coco_anns_by_image[image_id].append(ann)

    out_images = []
    out_annotations = []
    source_counts = Counter()
    class_counts = Counter()
    image_id_next = 1
    ann_id_next = 1

    for image in vd["images"]:
        old_image_id = int(image["id"])
        anns = vd_anns_by_image.get(old_image_id, [])
        if not anns:
            continue

        source_path = resolve_image_path(
            image["file_name"],
            split_hint=split,
        )

        new_image_id = image_id_next
        image_id_next += 1

        out_image = dict(image)
        out_image["id"] = new_image_id
        out_image["file_name"] = str(source_path.resolve())
        out_image["source_dataset"] = "visdrone"
        out_image["source_image_id"] = old_image_id
        out_images.append(out_image)

        for ann in anns:
            target = VISDRONE_TO_TARGET[int(ann["category_id"])]
            item = remap_annotation(
                ann, ann_id_next, new_image_id, target
            )
            if item is None:
                continue
            item["source_dataset"] = "visdrone"
            out_annotations.append(item)
            ann_id_next += 1
            class_counts[TARGET_NAMES[target]] += 1

        source_counts["visdrone_images"] += 1

    for image in coco["images"]:
        old_image_id = int(image["id"])
        if old_image_id not in coco_luggage_images:
            continue

        anns = coco_anns_by_image.get(old_image_id, [])
        if not anns:
            continue

        source_path = resolve_image_path(
            image["file_name"],
            split_hint=f"{split}2017",
        )

        new_image_id = image_id_next
        image_id_next += 1

        out_image = dict(image)
        out_image["id"] = new_image_id
        out_image["file_name"] = str(source_path.resolve())
        out_image["source_dataset"] = "coco"
        out_image["source_image_id"] = old_image_id
        out_images.append(out_image)

        for ann in anns:
            source_cid = int(ann["category_id"])
            target = COCO_TO_TARGET[source_cid]
            item = remap_annotation(
                ann, ann_id_next, new_image_id, target
            )
            if item is None:
                continue
            item["source_dataset"] = "coco"
            out_annotations.append(item)
            ann_id_next += 1
            class_counts[TARGET_NAMES[target]] += 1

        source_counts["coco_luggage_images"] += 1

    result = {
        "info": {
            "description": (
                "Phase7A person+luggage: VisDrone person + "
                "COCO luggage-context images"
            ),
            "split": split,
        },
        "images": out_images,
        "annotations": out_annotations,
        "categories": TARGET_CATEGORIES,
    }

    audit = {
        "split": split,
        "images_total": len(out_images),
        "annotations_total": len(out_annotations),
        "source_counts": dict(source_counts),
        "class_counts": dict(class_counts),
    }
    return result, audit


def make_source_subset(data, source_name):
    image_ids = {
        int(img["id"])
        for img in data["images"]
        if img.get("source_dataset") == source_name
    }

    return {
        "info": dict(data.get("info", {})),
        "images": [
            img for img in data["images"]
            if int(img["id"]) in image_ids
        ],
        "annotations": [
            ann for ann in data["annotations"]
            if int(ann["image_id"]) in image_ids
        ],
        "categories": TARGET_CATEGORIES,
    }


def make_smoke_subset(data, per_source):
    chosen = []
    for source in ["visdrone", "coco"]:
        source_images = [
            img for img in data["images"]
            if img.get("source_dataset") == source
        ]
        chosen.extend(source_images[:per_source])

    ids = {int(img["id"]) for img in chosen}
    return {
        "info": dict(data.get("info", {})),
        "images": chosen,
        "annotations": [
            ann for ann in data["annotations"]
            if int(ann["image_id"]) in ids
        ],
        "categories": TARGET_CATEGORIES,
    }


def verify_manifest(path):
    data = load_json(path)

    ids = [int(c["id"]) for c in data["categories"]]
    names = [str(c["name"]) for c in data["categories"]]

    if ids != [0, 1, 2, 3] or names != TARGET_NAMES:
        raise RuntimeError(
            f"Invalid Phase7A taxonomy in {path}: ids={ids}, names={names}"
        )

    image_ids = {int(img["id"]) for img in data["images"]}
    missing = []
    per_class = Counter()

    for img in data["images"]:
        p = Path(img["file_name"])
        if not p.is_file():
            missing.append(str(p))
            if len(missing) >= 20:
                break

    if missing:
        raise FileNotFoundError(
            f"Missing images referenced by {path}:\n"
            + "\n".join(missing)
        )

    for ann in data["annotations"]:
        if int(ann["image_id"]) not in image_ids:
            raise RuntimeError("Annotation references missing image.")
        cid = int(ann["category_id"])
        if cid not in range(4):
            raise RuntimeError(f"Invalid target category id={cid}")
        per_class[TARGET_NAMES[cid]] += 1

    print(
        f"[OK] {path.name}: images={len(data['images'])}, "
        f"objects={len(data['annotations'])}, classes={dict(per_class)}"
    )


def prepare_dataset():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    vd_train = find_exactly_one("annotations_VisDrone_train.json")
    vd_val = find_exactly_one("annotations_VisDrone_val.json")
    coco_train = find_exactly_one("instances_train2017.json")
    coco_val = find_exactly_one("instances_val2017.json")

    print("\n[INPUT ANNOTATIONS]")
    print("VisDrone train:", vd_train)
    print("VisDrone val  :", vd_val)
    print("COCO train    :", coco_train)
    print("COCO val      :", coco_val)

    train, train_audit = build_split(
        "train", vd_train, coco_train
    )
    val, val_audit = build_split(
        "val", vd_val, coco_val
    )

    val_vd = make_source_subset(val, "visdrone")
    val_coco = make_source_subset(val, "coco")

    smoke_train = make_smoke_subset(
        train, SMOKE_TRAIN_IMAGES_PER_SOURCE
    )
    smoke_val = make_smoke_subset(
        val, SMOKE_VAL_IMAGES_PER_SOURCE
    )

    save_json(TRAIN_ANN, train)
    save_json(VAL_ANN, val)
    save_json(VAL_VISDRONE_ANN, val_vd)
    save_json(VAL_COCO_ANN, val_coco)
    save_json(SMOKE_TRAIN_ANN, smoke_train)
    save_json(SMOKE_VAL_ANN, smoke_val)

    audit = {
        "target_categories": TARGET_CATEGORIES,
        "selection_policy": {
            "visdrone": (
                "Keep images with raw category 1/2; merge both to person."
            ),
            "coco": (
                "Keep only images containing backpack/handbag/suitcase; "
                "retain target annotations person+backpack+handbag+suitcase."
            ),
        },
        "train": train_audit,
        "val": val_audit,
        "val_visdrone_images": len(val_vd["images"]),
        "val_coco_luggage_images": len(val_coco["images"]),
    }
    save_json(DATA_AUDIT, audit, indent=2)

    for path in [
        TRAIN_ANN,
        VAL_ANN,
        VAL_VISDRONE_ANN,
        VAL_COCO_ANN,
        SMOKE_TRAIN_ANN,
        SMOKE_VAL_ANN,
    ]:
        verify_manifest(path)

    print("\n" + "=" * 92)
    print("PHASE 7A DATASET READY")
    print("=" * 92)
    print(json.dumps(audit, indent=2))
    print("=" * 92)


def prepare_repo():
    if REPO.exists():
        shutil.rmtree(REPO)

    run([
        "git", "clone",
        "https://github.com/Intellindust-AI-Lab/DEIMv2.git",
        str(REPO),
    ])
    run(
        ["git", "checkout", "--detach", DEIM_COMMIT],
        cwd=REPO,
    )

    actual = subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO,
        text=True,
    ).strip()

    if actual != DEIM_COMMIT:
        raise RuntimeError(
            f"DEIMv2 commit mismatch expected={DEIM_COMMIT}, actual={actual}"
        )
    print("[OK] DEIMv2 commit:", actual)


def patch_profiler():
    path = REPO / "engine" / "solver" / "det_solver.py"
    source = path.read_text(encoding="utf-8")

    old = (
        "        n_parameters, model_stats = stats(self.cfg)\n"
        "        print(model_stats)"
    )
    new = (
        "        n_parameters = sum(p.numel() for p in self.model.parameters())\n"
        "        print(f\"[PHASE7A] FLOPs profiling skipped; "
        "parameters={n_parameters:,}\")"
    )

    if old in source:
        path.write_text(
            source.replace(old, new, 1),
            encoding="utf-8",
        )
        print("[OK] FLOPs profiler disabled")
    else:
        print("[WARN] FLOPs profiler patch pattern not found.")


def patch_torchvision():
    path = REPO / "engine" / "data" / "transforms" / "_transforms.py"
    source = path.read_text(encoding="utf-8")
    sentinel = "# KAGGLE_TORCHVISION_V2_COMPAT_PATCH"

    if sentinel in source:
        return

    patch = r"""
# KAGGLE_TORCHVISION_V2_COMPAT_PATCH
if hasattr(T.Transform, "transform"):
    if (
        hasattr(ConvertPILImage, "_transform")
        and "transform" not in ConvertPILImage.__dict__
    ):
        ConvertPILImage.transform = ConvertPILImage._transform

    if (
        hasattr(ConvertBoxes, "_transform")
        and "transform" not in ConvertBoxes.__dict__
    ):
        ConvertBoxes.transform = ConvertBoxes._transform

    if (
        hasattr(PadToSize, "_transform")
        and "transform" not in PadToSize.__dict__
    ):
        PadToSize.transform = PadToSize._transform

    if (
        hasattr(T.Transform, "make_params")
        and hasattr(PadToSize, "_get_params")
        and "make_params" not in PadToSize.__dict__
    ):
        PadToSize.make_params = PadToSize._get_params
"""

    path.write_text(
        source.rstrip() + "\n" + patch + "\n",
        encoding="utf-8",
    )
    print("[OK] torchvision compatibility patch applied")


def verify_torchvision_patch():
    check_code = r"""
import sys
import torchvision
sys.path.insert(0, "/kaggle/working/DEIMv2")
from engine.data.transforms._transforms import (
    ConvertPILImage, ConvertBoxes, PadToSize
)
assert "transform" in ConvertPILImage.__dict__
assert "transform" in ConvertBoxes.__dict__
if hasattr(torchvision.transforms.v2.Transform, "make_params"):
    assert "make_params" in PadToSize.__dict__
print("[OK] torchvision patch verified")
"""
    run([sys.executable, "-c", check_code], cwd=REPO)


def prepare_backbone():
    dest = REPO / "ckpts" / "vitt_distill.pt"
    dest.parent.mkdir(parents=True, exist_ok=True)

    candidates = list(INPUT.rglob("vitt_distill.pt"))

    if candidates:
        shutil.copy2(candidates[0], dest)
        print("[BACKBONE] reused:", candidates[0])
    else:
        import gdown
        print("[BACKBONE] downloading official vitt_distill.pt...")
        result = gdown.download(
            id=VITT_GOOGLE_DRIVE_ID,
            output=str(dest),
            quiet=False,
        )
        if result is None:
            raise RuntimeError(
                "Could not download backbone. Enable Kaggle Internet "
                "or attach vitt_distill.pt."
            )

    if not dest.is_file() or dest.stat().st_size < 5 * 1024 * 1024:
        raise RuntimeError("Invalid vitt_distill.pt")

    print(
        f"[OK] backbone={dest}, "
        f"size={dest.stat().st_size/1024/1024:.2f} MB"
    )
    return dest


def write_config(
    path,
    train_ann,
    val_ann,
    output_dir,
    backbone,
    epochs,
    train_batch,
    val_batch,
    workers,
    smoke=False,
):
    base = REPO / "configs" / "deimv2" / "deimv2_dinov3_s_coco.yml"
    if not base.is_file():
        raise FileNotFoundError(base)

    warmup = 20 if smoke else WARMUP_STEPS
    milestone = [1] if smoke else LR_MILESTONES

    text = f"""
__include__: ['{base}']

num_classes: {NUM_CLASSES}
remap_mscoco_category: False
output_dir: "{output_dir}"
eval_spatial_size: [{INPUT_SIZE}, {INPUT_SIZE}]

DINOv3STAs:
  weights_path: "{backbone}"

epoches: {epochs}
print_freq: {1 if smoke else 50}
checkpoint_freq: {CHECKPOINT_FREQ}
sync_bn: False
find_unused_parameters: False

use_ema: True
ema:
  type: ModelEMA
  decay: 0.9999
  warmups: 1000
  start: 0

lrsheduler: null
warmup_iter: {warmup}
flat_epoch: 0
no_aug_epoch: 0

optimizer:
  type: AdamW
  params:
    -
      params: '^(?=.*.dinov3)(?!.*(?:norm|bn|bias)).*$'
      lr: {BACKBONE_LR:.8f}
    -
      params: '^(?=.*.dinov3)(?=.*(?:norm|bn|bias)).*$'
      lr: {BACKBONE_LR:.8f}
      weight_decay: 0.0
    -
      params: '^(?=.*(?:sta|encoder|decoder))(?=.*(?:norm|bn|bias)).*$'
      weight_decay: 0.0
  lr: {MODEL_LR:.8f}
  betas: [0.9, 0.999]
  weight_decay: {WEIGHT_DECAY}

lr_scheduler:
  type: MultiStepLR
  milestones: {milestone}
  gamma: {LR_GAMMA}

lr_warmup_scheduler:
  type: LinearWarmup
  warmup_duration: {warmup}

DEIMCriterion:
  matcher:
    change_matcher: False

train_dataloader:
  type: DataLoader
  total_batch_size: {train_batch}
  num_workers: {workers}
  shuffle: True
  drop_last: True

  dataset:
    type: CocoDetection
    img_folder: "/"
    ann_file: "{train_ann}"
    return_masks: False

    transforms:
      type: Compose
      ops:
        - {{type: RandomPhotometricDistort, p: {PHOTO_DISTORT_P}}}
        - {{type: RandomIoUCrop, p: {IOU_CROP_P}}}
        - {{type: SanitizeBoundingBoxes, min_size: 1}}
        - {{type: RandomHorizontalFlip}}
        - {{type: Resize, size: [{INPUT_SIZE}, {INPUT_SIZE}]}}
        - {{type: SanitizeBoundingBoxes, min_size: 1}}
        - {{type: ConvertPILImage, dtype: 'float32', scale: True}}
        - {{type: Normalize, mean: [0.485, 0.456, 0.406], std: [0.229, 0.224, 0.225]}}
        - {{type: ConvertBoxes, fmt: 'cxcywh', normalize: True}}
      policy: null
      mosaic_prob: 0.0

  collate_fn:
    type: BatchImageCollateFunction
    base_size: {INPUT_SIZE}
    base_size_repeat: null
    stop_epoch: 999999
    mixup_prob: 0.0
    mixup_epochs: [999999, 999999]
    copyblend_prob: 0.0
    copyblend_epochs: [999999, 999999]
    ema_restart_decay: 0.9999

val_dataloader:
  type: DataLoader
  total_batch_size: {val_batch}
  num_workers: {workers}
  shuffle: False
  drop_last: False

  dataset:
    type: CocoDetection
    img_folder: "/"
    ann_file: "{val_ann}"
    return_masks: False

    transforms:
      type: Compose
      ops:
        - {{type: Resize, size: [{INPUT_SIZE}, {INPUT_SIZE}]}}
        - {{type: ConvertPILImage, dtype: 'float32', scale: True}}
        - {{type: Normalize, mean: [0.485, 0.456, 0.406], std: [0.229, 0.224, 0.225]}}

  collate_fn:
    type: BatchImageCollateFunction
    base_size: {INPUT_SIZE}
    base_size_repeat: null
""".strip()

    path.write_text(text + "\n", encoding="utf-8")
    print("[OK] config:", path)


def validate_config(path, expected_epochs, train_batch):
    import yaml
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))

    assert raw["num_classes"] == 4
    assert raw["remap_mscoco_category"] is False
    assert raw["epoches"] == expected_epochs
    assert raw["train_dataloader"]["total_batch_size"] == train_batch
    assert raw["lr_warmup_scheduler"]["type"] == "LinearWarmup"
    assert abs(float(raw["optimizer"]["lr"]) - MODEL_LR) < 1e-12
    assert (
        abs(
            float(raw["optimizer"]["params"][0]["lr"])
            - BACKBONE_LR
        )
        < 1e-12
    )
    print("[OK] YAML validated:", path.name)


def run_smoke(tuning_checkpoint, backbone):
    if SMOKE_OUTPUT.exists():
        shutil.rmtree(SMOKE_OUTPUT)

    write_config(
        SMOKE_CONFIG,
        SMOKE_TRAIN_ANN,
        SMOKE_VAL_ANN,
        SMOKE_OUTPUT,
        backbone,
        epochs=1,
        train_batch=2,
        val_batch=2,
        workers=0,
        smoke=True,
    )
    validate_config(SMOKE_CONFIG, 1, 2)

    print("\n" + "=" * 92)
    print("PHASE 7A SMOKE — balanced VisDrone + COCO")
    print("=" * 92)

    env = os.environ.copy()
    env["TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD"] = "1"

    run([
        sys.executable,
        "train.py",
        "-c", str(SMOKE_CONFIG),
        "-t", str(tuning_checkpoint),
        "--use-amp",
        "--seed", "0",
        "-d", "cuda:0",
        "--output-dir", str(SMOKE_OUTPUT),
    ], cwd=REPO, env=env, timeout=30 * 60)

    if not (SMOKE_OUTPUT / "last.pth").is_file():
        raise RuntimeError("Smoke ended without last.pth.")

    print("[SMOKE PASS] 4-class DEIMv2 pipeline works")


def run_full_train(tuning_checkpoint, backbone):
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    gpu_count = torch.cuda.device_count()
    train_batch = TRAIN_TOTAL_BATCH if gpu_count >= 2 else 8
    val_batch = VAL_TOTAL_BATCH if gpu_count >= 2 else 8

    write_config(
        CONFIG_FILE,
        TRAIN_ANN,
        VAL_ANN,
        OUTPUT_DIR,
        backbone,
        epochs=EPOCHS,
        train_batch=train_batch,
        val_batch=val_batch,
        workers=NUM_WORKERS_PER_RANK,
        smoke=False,
    )
    validate_config(CONFIG_FILE, EPOCHS, train_batch)

    train_data = load_json(TRAIN_ANN)
    val_data = load_json(VAL_ANN)

    print("\n" + "=" * 92)
    print("PHASE 7A FULL TRAIN")
    print("=" * 92)
    print("Target classes:", TARGET_NAMES)
    print("Train images:", len(train_data["images"]))
    print("Val images:", len(val_data["images"]))
    print("Epochs:", EPOCHS)
    print("Input:", INPUT_SIZE)
    print("Global batch:", train_batch)
    print("Backbone LR:", BACKBONE_LR)
    print("Detector LR:", MODEL_LR)
    print("Tuning checkpoint:", tuning_checkpoint)
    print("=" * 92)

    env = {
        **os.environ,
        "PYTHONUNBUFFERED": "1",
        "TOKENIZERS_PARALLELISM": "false",
        "TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD": "1",
        "OMP_NUM_THREADS": "2",
        "MKL_NUM_THREADS": "2",
        "NCCL_ASYNC_ERROR_HANDLING": "1",
    }

    if gpu_count >= 2:
        env["CUDA_VISIBLE_DEVICES"] = "0,1"
        cmd = [
            sys.executable, "-m", "torch.distributed.run",
            "--standalone",
            "--nproc_per_node=2",
            "train.py",
            "-c", str(CONFIG_FILE),
            "-t", str(tuning_checkpoint),
            "--use-amp",
            "--seed", "0",
            "--output-dir", str(OUTPUT_DIR),
        ]
    else:
        cmd = [
            sys.executable,
            "train.py",
            "-c", str(CONFIG_FILE),
            "-t", str(tuning_checkpoint),
            "--use-amp",
            "--seed", "0",
            "-d", "cuda:0",
            "--output-dir", str(OUTPUT_DIR),
        ]

    run(cmd, cwd=REPO, env=env, timeout=10 * 60 * 60)

    last = OUTPUT_DIR / "last.pth"
    best_stg1 = OUTPUT_DIR / "best_stg1.pth"
    best = OUTPUT_DIR / "best.pth"

    if not last.is_file():
        raise RuntimeError("Full training finished without last.pth.")

    if not best_stg1.is_file():
        raise RuntimeError(
            "Full training finished without required best_stg1.pth; "
            "refusing to label last.pth as the best checkpoint."
        )
    shutil.copy2(best_stg1, best)

    print("[OK] Phase7A best checkpoint:", best)
    return best


def write_eval_config(backbone):
    path = WORK / "phase7a_deimv2_s_eval.yml"
    base = REPO / "configs" / "deimv2" / "deimv2_dinov3_s_coco.yml"

    text = f"""
__include__: ['{base}']
num_classes: 4
remap_mscoco_category: False
eval_spatial_size: [640, 640]

DINOv3STAs:
  weights_path: "{backbone}"

PostProcessor:
  num_top_queries: 300
""".strip()

    path.write_text(text + "\n", encoding="utf-8")
    return path


def load_model(checkpoint, eval_config):
    for key in list(sys.modules.keys()):
        if key == "engine" or key.startswith("engine."):
            del sys.modules[key]

    sys.path.insert(0, str(REPO))
    from engine.core import YAMLConfig

    cfg = YAMLConfig(str(eval_config), resume=str(checkpoint))

    checkpoint_obj = torch.load(
        checkpoint,
        map_location="cpu",
        weights_only=False,
    )

    state = (
        checkpoint_obj["ema"]["module"]
        if "ema" in checkpoint_obj
        else checkpoint_obj["model"]
    )

    info = cfg.model.load_state_dict(state, strict=True)
    print("[CHECKPOINT] load_state_dict:", info)

    class Deploy(torch.nn.Module):
        def __init__(self, model, post):
            super().__init__()
            self.model = model.deploy()
            self.post = post.deploy()

        def forward(self, images, orig_sizes):
            return self.post(self.model(images), orig_sizes)

    return Deploy(
        cfg.model,
        cfg.postprocessor,
    ).to("cuda:0").eval()


def build_transform():
    import torchvision.transforms as T

    return T.Compose([
        T.Resize((640, 640)),
        T.ToTensor(),
        T.Normalize(
            mean=[0.485, 0.456, 0.406],
            std=[0.229, 0.224, 0.225],
        ),
    ])


@torch.inference_mode()
def infer_pil(model, transform, image):
    tensor = transform(image).unsqueeze(0).to("cuda:0")
    w, h = image.size
    orig = torch.tensor(
        [[w, h]],
        dtype=torch.float32,
        device="cuda:0",
    )

    torch.cuda.synchronize()
    start = time.perf_counter()

    with torch.autocast(
        device_type="cuda",
        dtype=torch.float16,
    ):
        labels, boxes, scores = model(tensor, orig)

    torch.cuda.synchronize()
    elapsed = time.perf_counter() - start

    labels = labels[0].detach().cpu().long()
    boxes = boxes[0].detach().float().cpu()
    scores = scores[0].detach().float().cpu()

    keep = scores >= SCORE_THRESHOLD
    return labels[keep], boxes[keep], scores[keep], elapsed


def positions(length, window, overlap):
    if length <= window:
        return [0]

    stride = max(1, int(round(window * (1.0 - overlap))))
    result = list(range(0, max(1, length - window + 1), stride))

    final = length - window
    if result[-1] != final:
        result.append(final)

    return sorted(set(result))


def make_tiles(width, height):
    tw = min(TILE_SIZE, width)
    th = min(TILE_SIZE, height)

    out = []
    seen = set()

    for y0 in positions(height, th, TILE_OVERLAP):
        for x0 in positions(width, tw, TILE_OVERLAP):
            x1 = min(width, x0 + tw)
            y1 = min(height, y0 + th)
            x0 = max(0, x1 - tw)
            y0 = max(0, y1 - th)

            tile = (int(x0), int(y0), int(x1), int(y1))
            if tile not in seen:
                seen.add(tile)
                out.append(tile)

    return out


def merge_tiles(labels, boxes, scores, width, height):
    import torchvision

    if len(scores) == 0:
        return labels, boxes, scores

    boxes = torch.stack([
        boxes[:, 0].clamp(0, width),
        boxes[:, 1].clamp(0, height),
        boxes[:, 2].clamp(0, width),
        boxes[:, 3].clamp(0, height),
    ], dim=1)

    valid = (
        ((boxes[:, 2] - boxes[:, 0]) > 0)
        & ((boxes[:, 3] - boxes[:, 1]) > 0)
    )

    labels = labels[valid]
    boxes = boxes[valid]
    scores = scores[valid]

    if len(scores) == 0:
        return labels, boxes, scores

    keep = torchvision.ops.batched_nms(
        boxes, scores, labels, NMS_IOU
    )[:MAX_DETS]

    return labels[keep], boxes[keep], scores[keep]


def append_predictions(output, image_id, labels, boxes, scores):
    for label, box, score in zip(
        labels.tolist(),
        boxes.tolist(),
        scores.tolist(),
    ):
        x1, y1, x2, y2 = map(float, box)
        w = x2 - x1
        h = y2 - y1

        if w <= 0 or h <= 0:
            continue

        output.append({
            "image_id": int(image_id),
            "category_id": int(label),
            "bbox": [x1, y1, w, h],
            "score": float(score),
        })


def evaluate_predictions(gt_path, pred_path):
    from pycocotools.coco import COCO
    from pycocotools.cocoeval import COCOeval

    gt = COCO(str(gt_path))
    preds = load_json(pred_path)

    if not preds:
        raise RuntimeError(f"No predictions in {pred_path}")

    dt = gt.loadRes(preds)
    ev = COCOeval(gt, dt, "bbox")
    ev.params.imgIds = sorted(gt.getImgIds())
    ev.evaluate()
    ev.accumulate()
    ev.summarize()

    overall = {
        COCO_METRIC_NAMES[i]: float(ev.stats[i])
        for i in range(12)
    }

    per_class = {}
    present_cat_ids = set(gt.getCatIds())

    for cat in TARGET_CATEGORIES:
        cat_id = int(cat["id"])
        if cat_id not in present_cat_ids:
            per_class[cat["name"]] = {
                "AP50_95": None,
                "AP50": None,
                "AP75": None,
                "AR_100": None,
            }
            continue

        class_ev = COCOeval(gt, dt, "bbox")
        class_ev.params.imgIds = sorted(gt.getImgIds())
        class_ev.params.catIds = [cat_id]
        class_ev.evaluate()
        class_ev.accumulate()
        class_ev.summarize()

        per_class[cat["name"]] = {
            "AP50_95": float(class_ev.stats[0]),
            "AP50": float(class_ev.stats[1]),
            "AP75": float(class_ev.stats[2]),
            "AR_100": float(class_ev.stats[8]),
        }

    return {
        "overall": overall,
        "per_class": per_class,
    }


def evaluate_mode(dataset_name, gt_path, mode, model, transform):
    from PIL import Image

    data = load_json(gt_path)
    preds = []
    latencies = []
    tile_counts = []

    torch.cuda.empty_cache()
    torch.cuda.reset_peak_memory_stats()

    for idx, image_info in enumerate(data["images"], 1):
        image = Image.open(
            image_info["file_name"]
        ).convert("RGB")

        w, h = image.size
        total_start = time.perf_counter()

        if mode == "full640":
            labels, boxes, scores, _ = infer_pil(
                model, transform, image
            )
            tile_count = 1

        elif mode == "tile768_overlap20":
            all_labels = []
            all_boxes = []
            all_scores = []
            ts = make_tiles(w, h)

            for x0, y0, x1, y1 in ts:
                crop = image.crop((x0, y0, x1, y1))
                labels_i, boxes_i, scores_i, _ = infer_pil(
                    model, transform, crop
                )

                if len(scores_i) == 0:
                    continue

                shift = torch.tensor(
                    [x0, y0, x0, y0],
                    dtype=boxes_i.dtype,
                )

                all_labels.append(labels_i.clone())
                all_boxes.append(boxes_i.clone() + shift)
                all_scores.append(scores_i.clone())

            tile_count = len(ts)

            if all_scores:
                labels = torch.cat(all_labels)
                boxes = torch.cat(all_boxes)
                scores = torch.cat(all_scores)

                labels, boxes, scores = merge_tiles(
                    labels, boxes, scores, w, h
                )
            else:
                labels = torch.empty((0,), dtype=torch.long)
                boxes = torch.empty((0, 4), dtype=torch.float32)
                scores = torch.empty((0,), dtype=torch.float32)

        else:
            raise ValueError(mode)

        append_predictions(
            preds, image_info["id"], labels, boxes, scores
        )

        elapsed = time.perf_counter() - total_start
        latencies.append(elapsed)
        tile_counts.append(tile_count)

        if (
            idx == 1
            or idx % 100 == 0
            or idx == len(data["images"])
        ):
            print(
                f"[{dataset_name}/{mode}] "
                f"{idx}/{len(data['images'])} "
                f"tiles={tile_count} dets={len(scores)} "
                f"latency={elapsed*1000:.1f} ms"
            )

    pred_path = EVAL_DIR / f"{dataset_name}_{mode}_predictions.json"
    save_json(pred_path, preds)

    metrics = evaluate_predictions(gt_path, pred_path)
    mean_latency = sum(latencies) / len(latencies)

    return {
        "dataset": dataset_name,
        "mode": mode,
        **metrics,
        "latency_ms_per_image": mean_latency * 1000,
        "fps": 1.0 / mean_latency,
        "tiles_per_image": sum(tile_counts) / len(tile_counts),
        "peak_vram_mb":
            torch.cuda.max_memory_allocated() / 1024 / 1024,
        "prediction_file": str(pred_path),
    }


def print_eval_summary(results):
    print("\n" + "=" * 110)
    print("PHASE 7A FINAL EVALUATION")
    print("=" * 110)
    print(
        f"{'dataset/mode':<38}"
        f"{'AP':>9}"
        f"{'APs':>9}"
        f"{'ARs':>9}"
        f"{'FPS':>9}"
        f"{'tiles':>9}"
    )
    print("-" * 110)

    for r in results:
        o = r["overall"]
        print(
            f"{(r['dataset'] + '/' + r['mode']):<38}"
            f"{o['AP50_95']:>9.4f}"
            f"{o['AP_small']:>9.4f}"
            f"{o['AR_small']:>9.4f}"
            f"{r['fps']:>9.2f}"
            f"{r['tiles_per_image']:>9.2f}"
        )

    print("=" * 110)

    for r in results:
        print(f"\n[PER CLASS] {r['dataset']} / {r['mode']}")
        for name in TARGET_NAMES:
            m = r["per_class"][name]
            if m["AP50_95"] is None:
                print(f"  {name:<10} N/A (class absent in this subset)")
            else:
                print(
                    f"  {name:<10} "
                    f"AP={m['AP50_95']:.4f} "
                    f"AP50={m['AP50']:.4f} "
                    f"AR100={m['AR_100']:.4f}"
                )

    print("\nOutputs:")
    print(" ", DATA_AUDIT)
    print(" ", OUTPUT_DIR / "best.pth")
    print(" ", EVAL_SUMMARY)
    print("=" * 110)


def main():
    os.environ["PYTHONUNBUFFERED"] = "1"
    os.environ["TOKENIZERS_PARALLELISM"] = "false"
    os.environ["TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD"] = "1"

    print_env()
    install_dependencies()

    prepare_dataset()
    tuning_checkpoint = find_phase4_checkpoint()

    prepare_repo()
    patch_profiler()
    patch_torchvision()
    verify_torchvision_patch()
    backbone = prepare_backbone()

    if RUN_SMOKE:
        run_smoke(tuning_checkpoint, backbone)

    best = run_full_train(tuning_checkpoint, backbone)

    print("\n" + "=" * 92)
    print("PHASE 7A DETECTION EVALUATION")
    print("=" * 92)

    EVAL_DIR.mkdir(parents=True, exist_ok=True)

    eval_config = write_eval_config(backbone)
    model = load_model(best, eval_config)
    transform = build_transform()

    from PIL import Image
    warm_data = load_json(VAL_ANN)
    warm = Image.open(
        warm_data["images"][0]["file_name"]
    ).convert("RGB")

    print("[WARMUP] 3 forward passes")
    for _ in range(3):
        infer_pil(model, transform, warm)

    jobs = [
        ("combined_val", VAL_ANN),
        ("visdrone_person_val", VAL_VISDRONE_ANN),
        ("coco_luggage_val", VAL_COCO_ANN),
    ]

    results = []
    for dataset_name, gt_path in jobs:
        for mode in ["full640", "tile768_overlap20"]:
            results.append(
                evaluate_mode(
                    dataset_name,
                    gt_path,
                    mode,
                    model,
                    transform,
                )
            )

    save_json(
        EVAL_SUMMARY,
        {
            "taxonomy": TARGET_CATEGORIES,
            "checkpoint": str(best),
            "results": results,
        },
        indent=2,
    )

    print_eval_summary(results)

    print(
        "\n[NEXT GATE] Do NOT start S4 yet. "
        "Use these metrics to decide whether detection is adequate enough "
        "to connect ByteTrack in Phase 7B."
    )


if __name__ == "__main__":
    main()
