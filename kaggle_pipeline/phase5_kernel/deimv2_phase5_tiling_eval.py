import os
import sys
import json
import csv
import time
import shutil
import subprocess
from pathlib import Path

import torch

# ============================================================
# PHASE 5 — SMALL-OBJECT INFERENCE ABLATION
# ============================================================
# Compare the SAME trained DEIMv2-S checkpoint on the SAME
# VisDrone validation set with:
#   A) baseline_640
#   B) tile640_no_overlap
#   C) tile640_overlap25
#
# No retraining. No S4. No YOLO. No VLM.
# Primary metrics: AP50:95, AP-small, AR-small, latency, FPS, VRAM.
# ============================================================

INPUT = Path('/kaggle/input')
WORK = Path('/kaggle/working')
REPO = WORK / 'DEIMv2'

DEIM_COMMIT = '0fff8d4dcdc272e6cf2d84be31399db471357941'
VITT_GOOGLE_DRIVE_ID = '1YMTq_woOLjAcZnHSYNTsNg7f0ahj5LPs'

NUM_CLASSES = 10
MODEL_INPUT_SIZE = 640
DEVICE = 'cuda:0'
USE_AMP = True

SCORE_THRESHOLD = 0.001
NMS_IOU_THRESHOLD = 0.60
MAX_DETECTIONS_AFTER_MERGE = 300

EXPECTED_BASELINE_AP = 0.2271
BASELINE_AP_TOLERANCE = 0.015

OUTPUT_DIR = WORK / 'phase5_deimv2_tiling'
NORMALIZED_VAL_ANN = WORK / 'visdrone_phase5_val_contiguous.json'
EVAL_CONFIG = WORK / 'visdrone_phase5_eval.yml'
SUMMARY_JSON = OUTPUT_DIR / 'phase5_summary.json'
SUMMARY_CSV = OUTPUT_DIR / 'phase5_summary.csv'
SUMMARY_MD = OUTPUT_DIR / 'phase5_summary.md'

EXPERIMENTS = [
    {
        'name': 'baseline_640',
        'mode': 'baseline',
        'tile_size': None,
        'overlap': 0.0,
    },
    {
        'name': 'tile640_no_overlap',
        'mode': 'tile',
        'tile_size': 640,
        'overlap': 0.0,
    },
    {
        'name': 'tile640_overlap25',
        'mode': 'tile',
        'tile_size': 640,
        'overlap': 0.25,
    },
]


def run(command, cwd=None, env=None, timeout=None):
    print('\n$ ' + ' '.join(map(str, command)), flush=True)
    return subprocess.run(
        command,
        cwd=cwd,
        env=env,
        check=True,
        timeout=timeout,
    )


def print_environment():
    print('=' * 80)
    print('PHASE 5 ENVIRONMENT')
    print('=' * 80)
    print('Python:', sys.version, flush=True)
    print('torch:', torch.__version__, flush=True)

    try:
        import torchvision
        print('torchvision:', torchvision.__version__, flush=True)
    except Exception as exc:
        print('[WARN] torchvision import failed:', repr(exc), flush=True)

    print('CUDA available:', torch.cuda.is_available(), flush=True)
    if not torch.cuda.is_available():
        raise RuntimeError('GPU is required. Enable Kaggle GPU accelerator.')

    print('Visible GPU count:', torch.cuda.device_count(), flush=True)
    for i in range(torch.cuda.device_count()):
        print(
            f'GPU {i}: {torch.cuda.get_device_name(i)} | '
            f'capability={torch.cuda.get_device_capability(i)}',
            flush=True,
        )

    print(
        '[INFO] Phase 5 intentionally uses ONE visible GPU so '
        'baseline vs tiling latency is comparable.',
        flush=True,
    )
    print('=' * 80)


def install_dependencies():
    # Do NOT install DEIMv2 requirements.txt: current Kaggle torch/torchvision
    # already passed the smoke/full workflow after compatibility patching.
    run([
        sys.executable,
        '-m',
        'pip',
        'install',
        '-q',
        'PyYAML',
        'gdown',
        'pycocotools',
    ])


def prepare_repo():
    if REPO.exists():
        shutil.rmtree(REPO)

    run([
        'git',
        'clone',
        'https://github.com/Intellindust-AI-Lab/DEIMv2.git',
        str(REPO),
    ])

    run([
        'git',
        'checkout',
        '--detach',
        DEIM_COMMIT,
    ], cwd=REPO)

    actual = subprocess.check_output(
        ['git', 'rev-parse', 'HEAD'],
        cwd=REPO,
        text=True,
    ).strip()

    if actual != DEIM_COMMIT:
        raise RuntimeError(
            f'DEIMv2 commit mismatch: expected={DEIM_COMMIT}, actual={actual}'
        )

    print('[OK] DEIMv2 commit:', actual, flush=True)


def patch_torchvision_v2_compat():
    path = REPO / 'engine' / 'data' / 'transforms' / '_transforms.py'
    source = path.read_text(encoding='utf-8')
    sentinel = '# KAGGLE_TORCHVISION_V2_COMPAT_PATCH'

    if sentinel in source:
        print('[OK] torchvision compatibility patch already present')
        return

    patch = r'''

# KAGGLE_TORCHVISION_V2_COMPAT_PATCH
if hasattr(T.Transform, "transform"):
    if hasattr(ConvertPILImage, "_transform") and "transform" not in ConvertPILImage.__dict__:
        ConvertPILImage.transform = ConvertPILImage._transform

    if hasattr(ConvertBoxes, "_transform") and "transform" not in ConvertBoxes.__dict__:
        ConvertBoxes.transform = ConvertBoxes._transform

    if hasattr(PadToSize, "_transform") and "transform" not in PadToSize.__dict__:
        PadToSize.transform = PadToSize._transform

    if (
        hasattr(T.Transform, "make_params")
        and hasattr(PadToSize, "_get_params")
        and "make_params" not in PadToSize.__dict__
    ):
        PadToSize.make_params = PadToSize._get_params
'''

    path.write_text(source.rstrip() + patch + '\n', encoding='utf-8')
    print('[OK] Patched torchvision compatibility', flush=True)


def find_exactly_one(filename):
    matches = list(INPUT.rglob(filename))

    if len(matches) != 1:
        raise FileNotFoundError(
            f"Expected exactly one '{filename}' under /kaggle/input. "
            f'Found {len(matches)}: {matches[:20]}'
        )

    return matches[0]


def find_best_checkpoint():
    # Same Kaggle session: use Phase-4 output directly.
    same_session = (
        WORK
        / 'outputs'
        / 'deimv2_s_visdrone_full20_t4x2'
        / 'best.pth'
    )

    if same_session.is_file():
        print('[CHECKPOINT] Using same-session best.pth:', same_session)
        return same_session

    # New session: best.pth must be attached as Kaggle Input.
    best_matches = list(INPUT.rglob('best.pth'))
    if len(best_matches) == 1:
        print('[CHECKPOINT] Using Kaggle Input best.pth:', best_matches[0])
        return best_matches[0]

    stage_matches = list(INPUT.rglob('best_stg1.pth'))
    if len(best_matches) == 0 and len(stage_matches) == 1:
        print('[CHECKPOINT] Using Kaggle Input best_stg1.pth:', stage_matches[0])
        return stage_matches[0]

    raise FileNotFoundError(
        'Could not uniquely resolve Phase-4 best checkpoint.\n'
        f'Expected same-session path: {same_session}\n'
        'OR attach exactly one best.pth / best_stg1.pth under /kaggle/input.\n'
        f'best.pth candidates={best_matches}\n'
        f'best_stg1.pth candidates={stage_matches}'
    )


def prepare_backbone_weights():
    ckpt_dir = REPO / 'ckpts'
    ckpt_dir.mkdir(parents=True, exist_ok=True)
    destination = ckpt_dir / 'vitt_distill.pt'

    candidates = list(INPUT.rglob('vitt_distill.pt'))
    if candidates:
        print('[BACKBONE] Reusing:', candidates[0], flush=True)
        shutil.copy2(candidates[0], destination)
    else:
        print(
            '[BACKBONE] vitt_distill.pt not attached; downloading official file...',
            flush=True,
        )
        import gdown
        result = gdown.download(
            id=VITT_GOOGLE_DRIVE_ID,
            output=str(destination),
            quiet=False,
        )
        if result is None:
            raise RuntimeError(
                'Failed to download vitt_distill.pt. Kaggle Internet must be ON.'
            )

    if not destination.is_file():
        raise FileNotFoundError(destination)

    size_mb = destination.stat().st_size / 1024 / 1024
    if size_mb < 5:
        raise RuntimeError(
            f'Backbone file is suspiciously small: {size_mb:.2f} MB'
        )

    print(
        f'[OK] Backbone ready: {destination} ({size_mb:.2f} MB)',
        flush=True,
    )
    return destination


def load_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sorted_categories(data):
    return sorted(
        data.get('categories', []),
        key=lambda item: int(item['id']),
    )


def normalize_visdrone_val(source, destination):
    data = load_json(source)
    categories = sorted_categories(data)

    if len(categories) != NUM_CLASSES:
        raise RuntimeError(
            f'Expected {NUM_CLASSES} categories, got {len(categories)}'
        )

    declared_ids = [int(item['id']) for item in categories]
    annotation_ids = sorted({
        int(annotation['category_id'])
        for annotation in data.get('annotations', [])
    })

    print('\n[TAXONOMY AUDIT]', flush=True)
    print('Declared IDs :', declared_ids, flush=True)
    print('Annotation IDs:', annotation_ids, flush=True)

    # Current project Kaggle conversion: metadata 0..9 but raw annotations 0..11.
    if (
        declared_ids == list(range(10))
        and set(annotation_ids).issubset(set(range(12)))
        and (10 in annotation_ids or 11 in annotation_ids)
    ):
        mapping = {raw_id: raw_id - 1 for raw_id in range(1, 11)}
        ignored_ids = {0, 11}
        mode = 'VISDRONE_RAW_0_11_TO_MODEL_0_9'

    elif (
        declared_ids == list(range(10))
        and set(annotation_ids).issubset(set(range(10)))
    ):
        mapping = {i: i for i in range(10)}
        ignored_ids = set()
        mode = 'ALREADY_ZERO_BASED'

    else:
        raise RuntimeError(
            'Unsupported/ambiguous VisDrone category-ID scheme.\n'
            f'Declared={declared_ids}\nAnnotations={annotation_ids}'
        )

    print('Mapping mode:', mode, flush=True)
    print('Ignored IDs :', sorted(ignored_ids), flush=True)
    print('Mapping     :', mapping, flush=True)

    output_categories = []
    for model_id, category in enumerate(categories):
        converted = dict(category)
        converted['source_declared_category_id'] = int(category['id'])
        converted['id'] = model_id
        output_categories.append(converted)

    output_annotations = []
    drop0 = 0
    drop11 = 0

    for annotation in data.get('annotations', []):
        raw_id = int(annotation['category_id'])

        if raw_id in ignored_ids:
            if raw_id == 0:
                drop0 += 1
            elif raw_id == 11:
                drop11 += 1
            continue

        if raw_id not in mapping:
            raise RuntimeError(
                f"Unexpected category_id={raw_id} in annotation {annotation.get('id')}"
            )

        converted = dict(annotation)
        converted['source_annotation_category_id'] = raw_id
        converted['category_id'] = int(mapping[raw_id])
        output_annotations.append(converted)

    output = dict(data)
    output['categories'] = output_categories
    output['annotations'] = output_annotations

    destination.write_text(
        json.dumps(output, ensure_ascii=False),
        encoding='utf-8',
    )

    print(
        f"[OK] Normalized val: {len(output['images'])} images, "
        f'{len(output_annotations)} trainable objects, '
        f'drop0={drop0}, drop11={drop11}',
        flush=True,
    )

    return output


def resolve_image_root(images):
    sample = images[:30]
    if not sample:
        raise RuntimeError('No validation images')

    first_name = Path(sample[0]['file_name'])
    matches = list(INPUT.rglob(first_name.name))
    if not matches:
        raise FileNotFoundError(
            f'Cannot locate validation image {first_name.name}'
        )

    candidates = []
    seen = set()

    for match in matches:
        current = match.parent
        for _ in range(8):
            key = str(current.resolve())
            if key not in seen:
                seen.add(key)
                candidates.append(current)
            if current == INPUT:
                break
            current = current.parent

    candidates.sort(
        key=lambda path: (
            'val' not in str(path).lower(),
            len(str(path)),
        )
    )

    for root in candidates:
        if all(
            (root / Path(image['file_name'])).is_file()
            for image in sample
        ):
            print('[OK] val root:', root, flush=True)
            return root, False

    for root in candidates:
        if all(
            (root / Path(image['file_name']).name).is_file()
            for image in sample
        ):
            print('[OK] val root (basename mode):', root, flush=True)
            return root, True

    raise FileNotFoundError('Could not resolve validation image root')


def normalize_val_filenames(annotation_path, image_root, basename_mode):
    data = load_json(annotation_path)
    changed = False

    for image in data['images']:
        if basename_mode:
            image['file_name'] = Path(image['file_name']).name
            changed = True

        image_path = image_root / image['file_name']
        if not image_path.is_file():
            raise FileNotFoundError(image_path)

    if changed:
        annotation_path.write_text(
            json.dumps(data, ensure_ascii=False),
            encoding='utf-8',
        )

    return data


def write_eval_config(backbone_path):
    base_config = (
        REPO
        / 'configs'
        / 'deimv2'
        / 'deimv2_dinov3_s_coco.yml'
    )

    text = f"""
__include__: ['{base_config}']

num_classes: {NUM_CLASSES}
remap_mscoco_category: False

eval_spatial_size: [{MODEL_INPUT_SIZE}, {MODEL_INPUT_SIZE}]

DINOv3STAs:
  weights_path: "{backbone_path}"

PostProcessor:
  num_top_queries: 300
""".strip()

    EVAL_CONFIG.write_text(text + '\n', encoding='utf-8')
    print('[OK] Eval config:', EVAL_CONFIG, flush=True)


def load_model(checkpoint_path):
    sys.path.insert(0, str(REPO))
    from engine.core import YAMLConfig

    cfg = YAMLConfig(str(EVAL_CONFIG))
    checkpoint = torch.load(checkpoint_path, map_location='cpu')

    if 'ema' in checkpoint:
        state = checkpoint['ema']['module']
        state_source = 'ema.module'
    elif 'model' in checkpoint:
        state = checkpoint['model']
        state_source = 'model'
    else:
        raise RuntimeError(
            f"Checkpoint contains neither 'ema' nor 'model'. Keys={list(checkpoint.keys())}"
        )

    info = cfg.model.load_state_dict(state, strict=True)
    print('[CHECKPOINT] Loaded state:', state_source, flush=True)
    print('[CHECKPOINT] load_state_dict:', info, flush=True)

    model_core = cfg.model.deploy()
    postprocessor = cfg.postprocessor.deploy()

    class DeployModel(torch.nn.Module):
        def __init__(self, model, post):
            super().__init__()
            self.model = model
            self.post = post

        def forward(self, images, orig_sizes):
            outputs = self.model(images)
            return self.post(outputs, orig_sizes)

    model = DeployModel(model_core, postprocessor).to(DEVICE)
    model.eval()
    return model


def build_transform():
    import torchvision.transforms as T

    return T.Compose([
        T.Resize((MODEL_INPUT_SIZE, MODEL_INPUT_SIZE)),
        T.ToTensor(),
        T.Normalize(
            mean=[0.485, 0.456, 0.406],
            std=[0.229, 0.224, 0.225],
        ),
    ])


@torch.inference_mode()
def infer_pil(model, transform, image):
    tensor = transform(image).unsqueeze(0).to(DEVICE, non_blocking=True)
    width, height = image.size

    orig_size = torch.tensor(
        [[width, height]],
        dtype=torch.float32,
        device=DEVICE,
    )

    if DEVICE.startswith('cuda'):
        torch.cuda.synchronize()

    start = time.perf_counter()

    if USE_AMP and DEVICE.startswith('cuda'):
        with torch.autocast(device_type='cuda', dtype=torch.float16):
            labels, boxes, scores = model(tensor, orig_size)
    else:
        labels, boxes, scores = model(tensor, orig_size)

    if DEVICE.startswith('cuda'):
        torch.cuda.synchronize()

    elapsed = time.perf_counter() - start

    labels = labels[0].detach().long().cpu()
    boxes = boxes[0].detach().float().cpu()
    scores = scores[0].detach().float().cpu()

    keep = scores >= SCORE_THRESHOLD

    return (
        labels[keep],
        boxes[keep],
        scores[keep],
        elapsed,
    )


def sliding_positions(length, window, overlap):
    if window <= 0:
        raise ValueError('window must be > 0')
    if not (0.0 <= overlap < 1.0):
        raise ValueError('overlap must satisfy 0 <= overlap < 1')
    if length <= window:
        return [0]

    stride = max(1, int(round(window * (1.0 - overlap))))
    positions = list(range(0, max(1, length - window + 1), stride))
    final = length - window

    if positions[-1] != final:
        positions.append(final)

    return sorted(set(positions))


def generate_tiles(width, height, tile_size, overlap):
    tile_width = min(tile_size, width)
    tile_height = min(tile_size, height)

    xs = sliding_positions(width, tile_width, overlap)
    ys = sliding_positions(height, tile_height, overlap)

    tiles = []

    for y0 in ys:
        for x0 in xs:
            x1 = min(width, x0 + tile_width)
            y1 = min(height, y0 + tile_height)

            x0 = max(0, x1 - tile_width)
            y0 = max(0, y1 - tile_height)

            tiles.append((int(x0), int(y0), int(x1), int(y1)))

    unique = []
    seen = set()
    for tile in tiles:
        if tile not in seen:
            seen.add(tile)
            unique.append(tile)

    return unique


def merge_tile_detections(
    labels,
    boxes,
    scores,
    image_width,
    image_height,
):
    import torchvision

    if len(scores) == 0:
        return labels, boxes, scores

    boxes[:, 0::2] = boxes[:, 0::2].clamp(0, image_width)
    boxes[:, 1::2] = boxes[:, 1::2].clamp(0, image_height)

    widths = boxes[:, 2] - boxes[:, 0]
    heights = boxes[:, 3] - boxes[:, 1]

    valid = (
        (widths > 0)
        & (heights > 0)
        & (scores >= SCORE_THRESHOLD)
    )

    labels = labels[valid]
    boxes = boxes[valid]
    scores = scores[valid]

    if len(scores) == 0:
        return labels, boxes, scores

    keep = torchvision.ops.batched_nms(
        boxes,
        scores,
        labels,
        NMS_IOU_THRESHOLD,
    )

    keep = keep[:MAX_DETECTIONS_AFTER_MERGE]

    return labels[keep], boxes[keep], scores[keep]


def append_coco_predictions(output, image_id, labels, boxes, scores):
    for label, box, score in zip(
        labels.tolist(),
        boxes.tolist(),
        scores.tolist(),
    ):
        x1, y1, x2, y2 = map(float, box)
        width = max(0.0, x2 - x1)
        height = max(0.0, y2 - y1)

        if width <= 0 or height <= 0:
            continue

        output.append({
            'image_id': int(image_id),
            'category_id': int(label),
            'bbox': [x1, y1, width, height],
            'score': float(score),
        })


def run_experiment(experiment, model, transform, val_data, image_root):
    from PIL import Image

    name = experiment['name']
    mode = experiment['mode']

    print('\n' + '=' * 80, flush=True)
    print('EXPERIMENT:', name, flush=True)
    print('=' * 80, flush=True)

    predictions = []
    per_image_latency = []
    model_forward_latency = []
    tile_counts = []

    if DEVICE.startswith('cuda'):
        torch.cuda.empty_cache()
        torch.cuda.reset_peak_memory_stats()

    images = val_data['images']
    total = len(images)

    for index, image_info in enumerate(images, start=1):
        image_path = image_root / image_info['file_name']
        image = Image.open(image_path).convert('RGB')
        image_width, image_height = image.size

        image_start = time.perf_counter()

        if mode == 'baseline':
            labels, boxes, scores, forward_seconds = infer_pil(
                model,
                transform,
                image,
            )
            tile_count = 1
            # No external NMS for baseline: preserve official DEIMv2 behavior.

        elif mode == 'tile':
            tile_size = int(experiment['tile_size'])
            overlap = float(experiment['overlap'])

            tiles = generate_tiles(
                image_width,
                image_height,
                tile_size,
                overlap,
            )

            all_labels = []
            all_boxes = []
            all_scores = []
            forward_seconds = 0.0

            for x0, y0, x1, y1 in tiles:
                crop = image.crop((x0, y0, x1, y1))

                tile_labels, tile_boxes, tile_scores, tile_forward = infer_pil(
                    model,
                    transform,
                    crop,
                )

                forward_seconds += tile_forward

                if len(tile_scores) == 0:
                    continue

                # tile-local xyxy -> original-image xyxy
                tile_boxes[:, [0, 2]] += float(x0)
                tile_boxes[:, [1, 3]] += float(y0)

                all_labels.append(tile_labels)
                all_boxes.append(tile_boxes)
                all_scores.append(tile_scores)

            tile_count = len(tiles)

            if all_scores:
                labels = torch.cat(all_labels, dim=0)
                boxes = torch.cat(all_boxes, dim=0)
                scores = torch.cat(all_scores, dim=0)

                labels, boxes, scores = merge_tile_detections(
                    labels,
                    boxes,
                    scores,
                    image_width,
                    image_height,
                )
            else:
                labels = torch.empty((0,), dtype=torch.long)
                boxes = torch.empty((0, 4), dtype=torch.float32)
                scores = torch.empty((0,), dtype=torch.float32)

        else:
            raise ValueError(f'Unknown experiment mode: {mode}')

        append_coco_predictions(
            predictions,
            image_info['id'],
            labels,
            boxes,
            scores,
        )

        image_elapsed = time.perf_counter() - image_start
        per_image_latency.append(image_elapsed)
        model_forward_latency.append(forward_seconds)
        tile_counts.append(tile_count)

        if index == 1 or index % 50 == 0 or index == total:
            print(
                f'[{name}] {index}/{total} | '
                f'tiles={tile_count} | detections={len(scores)} | '
                f'image_latency={image_elapsed * 1000:.1f} ms',
                flush=True,
            )

    prediction_file = OUTPUT_DIR / f'{name}_predictions.json'
    prediction_file.write_text(
        json.dumps(predictions, ensure_ascii=False),
        encoding='utf-8',
    )

    mean_latency = sum(per_image_latency) / len(per_image_latency)
    mean_forward_latency = (
        sum(model_forward_latency) / len(model_forward_latency)
    )
    mean_tiles = sum(tile_counts) / len(tile_counts)

    peak_vram_mb = 0.0
    if DEVICE.startswith('cuda'):
        peak_vram_mb = torch.cuda.max_memory_allocated() / 1024 / 1024

    timing = {
        'mean_total_latency_ms_per_original_image': mean_latency * 1000.0,
        'fps_original_images': 1.0 / mean_latency,
        'mean_model_forward_ms_per_original_image': mean_forward_latency * 1000.0,
        'mean_tiles_per_original_image': mean_tiles,
        'peak_vram_mb': peak_vram_mb,
        'prediction_count': len(predictions),
    }

    return prediction_file, timing


COCO_NAMES = [
    'AP50_95',
    'AP50',
    'AP75',
    'AP_small',
    'AP_medium',
    'AP_large',
    'AR_1',
    'AR_10',
    'AR_100',
    'AR_small',
    'AR_medium',
    'AR_large',
]


def evaluate_coco(gt_annotation_file, prediction_file):
    from pycocotools.coco import COCO
    from pycocotools.cocoeval import COCOeval

    coco_gt = COCO(str(gt_annotation_file))
    predictions = json.loads(prediction_file.read_text(encoding='utf-8'))

    if not predictions:
        raise RuntimeError(f'No predictions in {prediction_file}')

    coco_dt = coco_gt.loadRes(predictions)
    evaluator = COCOeval(coco_gt, coco_dt, 'bbox')
    evaluator.params.imgIds = sorted(coco_gt.getImgIds())
    evaluator.evaluate()
    evaluator.accumulate()
    evaluator.summarize()

    stats = evaluator.stats.tolist()

    return {
        name: float(stats[index])
        for index, name in enumerate(COCO_NAMES)
    }


def save_summary(results):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    SUMMARY_JSON.write_text(
        json.dumps(results, ensure_ascii=False, indent=2),
        encoding='utf-8',
    )

    fieldnames = [
        'name',
        'AP50_95',
        'AP50',
        'AP75',
        'AP_small',
        'AR_small',
        'AP_medium',
        'AP_large',
        'AR_medium',
        'AR_large',
        'mean_total_latency_ms_per_original_image',
        'fps_original_images',
        'mean_model_forward_ms_per_original_image',
        'mean_tiles_per_original_image',
        'peak_vram_mb',
        'prediction_count',
    ]

    with SUMMARY_CSV.open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for result in results:
            writer.writerow({key: result.get(key) for key in fieldnames})

    baseline = next(
        (item for item in results if item['name'] == 'baseline_640'),
        None,
    )

    lines = [
        '# DEIMv2 Phase 5 — Tiling / ROI inference comparison',
        '',
        '| Experiment | AP50:95 | AP50 | AP-small | AR-small | Latency ms/img | FPS | Avg tiles/img | Peak VRAM MB |',
        '|---|---:|---:|---:|---:|---:|---:|---:|---:|',
    ]

    for item in results:
        lines.append(
            f"| {item['name']} | {item['AP50_95']:.4f} | "
            f"{item['AP50']:.4f} | {item['AP_small']:.4f} | "
            f"{item['AR_small']:.4f} | "
            f"{item['mean_total_latency_ms_per_original_image']:.1f} | "
            f"{item['fps_original_images']:.2f} | "
            f"{item['mean_tiles_per_original_image']:.2f} | "
            f"{item['peak_vram_mb']:.1f} |"
        )

    if baseline is not None:
        lines.extend([
            '',
            '## Delta vs baseline',
            '',
            '| Experiment | ΔAP50:95 | ΔAP-small | ΔAR-small | Latency multiplier |',
            '|---|---:|---:|---:|---:|',
        ])

        for item in results:
            ratio = (
                item['mean_total_latency_ms_per_original_image']
                / baseline['mean_total_latency_ms_per_original_image']
            )
            lines.append(
                f"| {item['name']} | "
                f"{item['AP50_95'] - baseline['AP50_95']:+.4f} | "
                f"{item['AP_small'] - baseline['AP_small']:+.4f} | "
                f"{item['AR_small'] - baseline['AR_small']:+.4f} | "
                f"{ratio:.2f}x |"
            )

    SUMMARY_MD.write_text('\n'.join(lines) + '\n', encoding='utf-8')


def print_final_summary(results):
    baseline = next(
        item for item in results if item['name'] == 'baseline_640'
    )

    print('\n' + '=' * 96, flush=True)
    print('PHASE 5 FINAL COMPARISON', flush=True)
    print('=' * 96, flush=True)

    header = (
        f"{'Experiment':<24}"
        f"{'AP':>9}"
        f"{'APs':>9}"
        f"{'ARs':>9}"
        f"{'ms/img':>12}"
        f"{'FPS':>9}"
        f"{'tiles':>9}"
        f"{'VRAM MB':>11}"
    )
    print(header, flush=True)
    print('-' * len(header), flush=True)

    for item in results:
        print(
            f"{item['name']:<24}"
            f"{item['AP50_95']:>9.4f}"
            f"{item['AP_small']:>9.4f}"
            f"{item['AR_small']:>9.4f}"
            f"{item['mean_total_latency_ms_per_original_image']:>12.1f}"
            f"{item['fps_original_images']:>9.2f}"
            f"{item['mean_tiles_per_original_image']:>9.2f}"
            f"{item['peak_vram_mb']:>11.1f}",
            flush=True,
        )

    print('=' * 96, flush=True)

    ap_difference = abs(baseline['AP50_95'] - EXPECTED_BASELINE_AP)

    if ap_difference > BASELINE_AP_TOLERANCE:
        print(
            '\n[WARN] Baseline reproduction differs from Phase-4 '
            f'AP≈{EXPECTED_BASELINE_AP:.4f} by {ap_difference:.4f}.',
            flush=True,
        )
        print(
            '[WARN] Do NOT interpret tiling deltas until checkpoint, '
            'preprocessing, category mapping and evaluation are checked.',
            flush=True,
        )
    else:
        print(
            '\n[OK] Baseline sanity check passed: '
            f"phase5={baseline['AP50_95']:.4f}, "
            f'phase4≈{EXPECTED_BASELINE_AP:.4f}',
            flush=True,
        )

    print(
        '\nDecision priority: AP-small -> AR-small -> latency/FPS -> overall AP.',
        flush=True,
    )
    print(
        'Initial useful target: AP-small >= ~0.16-0.17 from ~0.1314 baseline.',
        flush=True,
    )
    print('\nOutputs:', flush=True)
    print(' ', SUMMARY_JSON, flush=True)
    print(' ', SUMMARY_CSV, flush=True)
    print(' ', SUMMARY_MD, flush=True)
    print('=' * 96, flush=True)


def main():
    # Set this before the first torch.cuda query.
    os.environ['CUDA_VISIBLE_DEVICES'] = '0'
    os.environ['PYTHONUNBUFFERED'] = '1'
    os.environ['TOKENIZERS_PARALLELISM'] = 'false'
    os.environ['TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD'] = '1'

    print_environment()
    install_dependencies()
    prepare_repo()
    patch_torchvision_v2_compat()

    backbone_path = prepare_backbone_weights()
    source_val_ann = find_exactly_one('annotations_VisDrone_val.json')
    best_checkpoint = find_best_checkpoint()

    print('\nINPUTS', flush=True)
    print('val annotation :', source_val_ann, flush=True)
    print('best checkpoint:', best_checkpoint, flush=True)
    print('backbone       :', backbone_path, flush=True)

    val_data = normalize_visdrone_val(
        source_val_ann,
        NORMALIZED_VAL_ANN,
    )

    image_root, basename_mode = resolve_image_root(val_data['images'])
    val_data = normalize_val_filenames(
        NORMALIZED_VAL_ANN,
        image_root,
        basename_mode,
    )

    write_eval_config(backbone_path)
    model = load_model(best_checkpoint)
    transform = build_transform()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Warm up CUDA/model kernels so the first measured image is not unfairly slow.
    from PIL import Image
    first_path = image_root / val_data['images'][0]['file_name']
    warm_image = Image.open(first_path).convert('RGB')

    print('\n[WARMUP] Running 3 forward passes...', flush=True)
    for _ in range(3):
        infer_pil(model, transform, warm_image)

    if DEVICE.startswith('cuda'):
        torch.cuda.empty_cache()

    results = []

    for experiment in EXPERIMENTS:
        prediction_file, timing = run_experiment(
            experiment,
            model,
            transform,
            val_data,
            image_root,
        )

        print(
            f"\n[EVAL] COCO evaluation for {experiment['name']}",
            flush=True,
        )

        metrics = evaluate_coco(
            NORMALIZED_VAL_ANN,
            prediction_file,
        )

        result = {
            'name': experiment['name'],
            'mode': experiment['mode'],
            'tile_size': experiment.get('tile_size'),
            'overlap': experiment.get('overlap'),
            **metrics,
            **timing,
        }

        results.append(result)
        save_summary(results)

        print(f"\n[RESULT] {experiment['name']}", flush=True)
        print(f"  AP50:95 = {metrics['AP50_95']:.4f}", flush=True)
        print(f"  AP50    = {metrics['AP50']:.4f}", flush=True)
        print(f"  AP-small= {metrics['AP_small']:.4f}", flush=True)
        print(f"  AR-small= {metrics['AR_small']:.4f}", flush=True)
        print(
            '  latency = '
            f"{timing['mean_total_latency_ms_per_original_image']:.1f} ms/img",
            flush=True,
        )
        print(f"  FPS     = {timing['fps_original_images']:.2f}", flush=True)
        print(
            f"  tiles   = {timing['mean_tiles_per_original_image']:.2f}/img",
            flush=True,
        )

    save_summary(results)
    print_final_summary(results)


if __name__ == '__main__':
    main()
