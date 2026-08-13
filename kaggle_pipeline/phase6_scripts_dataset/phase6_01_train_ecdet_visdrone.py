"""Phase 6A: fine-tune ECDet-S (EdgeCrafter) on VisDrone for a fair DEIMv2-S comparison."""

# PATCH VERSION: v3 — fixes commented warmup import registration bug.

import os
import sys
import json
import shutil
import subprocess
import urllib.request
from pathlib import Path

import torch

INPUT = Path('/kaggle/input')
WORK = Path('/kaggle/working')
EDGE_REPO = WORK / 'EdgeCrafter'
ECDET_ROOT = EDGE_REPO / 'ecdetseg'
EDGE_COMMIT = '706d037c17c1703bb97f42a35d269959b511b5be'
ECDET_S_URL = 'https://github.com/capsule2077/edgecrafter/releases/download/edgecrafterv1/ecdet_s.pth'
ECDET_S_PRETRAIN = WORK / 'ecdet_s_coco.pth'

NUM_CLASSES = 10
EXPECTED_CATEGORY_NAMES = [
    'pedestrian', 'people', 'bicycle', 'car', 'van', 'truck',
    'tricycle', 'awning-tricycle', 'bus', 'motor'
]
EXPECTED_SPLIT_IMAGES = {'train': 6471, 'val': 548}
INPUT_SIZE = 640
EPOCHS = 20
TRAIN_TOTAL_BATCH = 16
VAL_TOTAL_BATCH = 16
NUM_WORKERS = 4
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

TRAIN_ANN = WORK / 'visdrone_phase6_train_contiguous.json'
VAL_ANN = WORK / 'visdrone_phase6_val_contiguous.json'
SMOKE_TRAIN_ANN = WORK / 'visdrone_phase6_smoke_train.json'
SMOKE_VAL_ANN = WORK / 'visdrone_phase6_smoke_val.json'
SMOKE_CFG = WORK / 'phase6_ecdet_s_smoke.yml'
FULL_CFG = WORK / 'phase6_ecdet_s_visdrone_full20.yml'
SMOKE_OUT = WORK / 'outputs' / 'phase6_ecdet_s_smoke'
FULL_OUT = WORK / 'outputs' / 'phase6_ecdet_s_visdrone_full20'


def run(cmd, cwd=None, env=None, timeout=None):
    print('\n$ ' + ' '.join(map(str, cmd)), flush=True)
    return subprocess.run(list(map(str, cmd)), cwd=cwd, env=env, check=True, timeout=timeout)


def print_env():
    import torchvision
    print('=' * 88)
    print('PHASE 6A — ECDET-S TRAIN ENVIRONMENT')
    print('=' * 88)
    print('Python:', sys.version)
    print('torch:', torch.__version__)
    print('torchvision:', torchvision.__version__)
    print('CUDA:', torch.cuda.is_available())
    if not torch.cuda.is_available():
        raise RuntimeError('CUDA GPU required')
    print('Visible GPUs:', torch.cuda.device_count())
    for i in range(torch.cuda.device_count()):
        print(f'GPU {i}: {torch.cuda.get_device_name(i)} | capability={torch.cuda.get_device_capability(i)}')
    print('=' * 88)


def install_deps():
    # Deliberately do not install repo requirements.txt: preserve working Kaggle torch/torchvision.
    run([
        sys.executable, '-m', 'pip', 'install', '-q',
        'faster-coco-eval>=1.6.7', 'PyYAML', 'pycocotools', 'scipy',
        'transformers', 'tensorboard', 'calflops', 'tabulate', 'opencv-python-headless'
    ])
    for name in ['yaml', 'pycocotools', 'faster_coco_eval', 'scipy', 'transformers', 'cv2']:
        module = __import__(name)
        print(f'[DEP OK] {name} version={getattr(module, "__version__", "unknown")}')


def prepare_repo():
    if EDGE_REPO.exists():
        shutil.rmtree(EDGE_REPO)
    run(['git', 'clone', 'https://github.com/Intellindust-AI-Lab/EdgeCrafter.git', str(EDGE_REPO)])
    run(['git', 'checkout', '--detach', EDGE_COMMIT], cwd=EDGE_REPO)
    actual = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=EDGE_REPO, text=True).strip()
    if actual != EDGE_COMMIT:
        raise RuntimeError(f'commit mismatch: expected={EDGE_COMMIT} actual={actual}')
    if not ECDET_ROOT.is_dir():
        raise FileNotFoundError(ECDET_ROOT)
    print('[OK] EdgeCrafter commit:', actual)


def patch_torchvision_compat():
    path = ECDET_ROOT / 'engine' / 'data' / 'transforms' / '_transforms.py'
    if not path.is_file():
        print('[WARN] transform file not found; no torchvision patch applied')
        return
    source = path.read_text(encoding='utf-8')
    sentinel = '# KAGGLE_TV025_COMPAT_PHASE6'
    if sentinel in source:
        return
    patch = "\n".join([
        '', sentinel,
        'try:',
        '    import torchvision.transforms.v2 as _tv_v2',
        '    if hasattr(_tv_v2.Transform, "transform"):',
        '        if "ConvertPILImage" in globals() and hasattr(ConvertPILImage, "_transform") and "transform" not in ConvertPILImage.__dict__:',
        '            ConvertPILImage.transform = ConvertPILImage._transform',
        '        if "ConvertBoxes" in globals() and hasattr(ConvertBoxes, "_transform") and "transform" not in ConvertBoxes.__dict__:',
        '            ConvertBoxes.transform = ConvertBoxes._transform',
        '        if "PadToSize" in globals() and hasattr(PadToSize, "_transform") and "transform" not in PadToSize.__dict__:',
        '            PadToSize.transform = PadToSize._transform',
        '        if "PadToSize" in globals() and hasattr(_tv_v2.Transform, "make_params") and hasattr(PadToSize, "_get_params") and "make_params" not in PadToSize.__dict__:',
        '            PadToSize.make_params = PadToSize._get_params',
        'except Exception:',
        '    pass',
        ''
    ])
    path.write_text(source.rstrip() + patch, encoding='utf-8')
    print('[OK] torchvision 0.25 compatibility patch applied')



def patch_linear_warmup_compat():
    """
    EdgeCrafter commit 706d037 keeps generic lr_warmup_scheduler support in
    YAMLConfig/BaseSolver, but engine/optim/__init__.py comments out warmup
    registration and the repository does not ship warmup.py.

    Our controlled Phase-6 recipe intentionally uses MultiStepLR +
    LinearWarmup to match the DEIMv2 VisDrone protocol, so restore the small
    RT-DETR/DEIMv2-compatible warmup module instead of changing the experiment.
    """
    optim_dir = ECDET_ROOT / 'engine' / 'optim'
    init_path = optim_dir / '__init__.py'
    warmup_path = optim_dir / 'warmup.py'

    if not init_path.is_file():
        raise FileNotFoundError(init_path)

    warmup_source = r"""from torch.optim.lr_scheduler import LRScheduler

from ..core import register


class Warmup(object):
    def __init__(
        self,
        lr_scheduler: LRScheduler,
        warmup_duration: int,
        last_step: int = -1,
    ) -> None:
        self.lr_scheduler = lr_scheduler
        self.warmup_end_values = [
            pg['lr'] for pg in lr_scheduler.optimizer.param_groups
        ]
        self.last_step = last_step
        self.warmup_duration = warmup_duration
        self.step()

    def state_dict(self):
        return {
            k: v for k, v in self.__dict__.items()
            if k != 'lr_scheduler'
        }

    def load_state_dict(self, state_dict):
        self.__dict__.update(state_dict)

    def get_warmup_factor(self, step, **kwargs):
        raise NotImplementedError

    def step(self):
        self.last_step += 1
        if self.last_step >= self.warmup_duration:
            return
        factor = self.get_warmup_factor(self.last_step)
        for i, pg in enumerate(self.lr_scheduler.optimizer.param_groups):
            pg['lr'] = factor * self.warmup_end_values[i]

    def finished(self):
        return self.last_step >= self.warmup_duration


@register()
class LinearWarmup(Warmup):
    def __init__(
        self,
        lr_scheduler: LRScheduler,
        warmup_duration: int,
        last_step: int = -1,
    ) -> None:
        super().__init__(lr_scheduler, warmup_duration, last_step)

    def get_warmup_factor(self, step):
        return min(1.0, (step + 1) / self.warmup_duration)
"""

    warmup_path.write_text(warmup_source, encoding='utf-8')

    init_source = init_path.read_text(encoding='utf-8')

    # IMPORTANT:
    # Do not test with:
    #     if 'from .warmup import *' not in init_source
    # because the original repo already contains the COMMENTED string
    # '# from .warmup import *', which makes that substring test false.
    #
    # Force exactly one active import line.
    lines = init_source.splitlines()
    cleaned = []

    for line in lines:
        stripped = line.strip()

        if stripped in {
            'from .warmup import *',
            '# from .warmup import *',
        }:
            continue

        cleaned.append(line)

    cleaned.append('from .warmup import *')

    init_source = '\n'.join(cleaned).rstrip() + '\n'
    init_path.write_text(init_source, encoding='utf-8')

    active_imports = [
        line.strip()
        for line in init_source.splitlines()
        if line.strip() == 'from .warmup import *'
    ]

    if len(active_imports) != 1:
        raise RuntimeError(
            'Failed to install exactly one active warmup import. '
            f'active_import_count={len(active_imports)}'
        )

    print('[PATCH] engine/optim/__init__.py now actively imports warmup.py')

    # Preflight in a FRESH subprocess. Import warmup explicitly as an extra
    # guard, then verify registration in GLOBAL_CONFIG.
    verify_code = r"""
import sys
sys.path.insert(0, r'REPO_PATH')

import engine
import engine.optim.warmup

from engine.core.workspace import GLOBAL_CONFIG

warmup_keys = sorted(
    k for k in GLOBAL_CONFIG.keys()
    if 'Warmup' in k
)

print('[PREFLIGHT] warmup registry keys:', warmup_keys)

assert 'LinearWarmup' in GLOBAL_CONFIG, warmup_keys

schema = GLOBAL_CONFIG['LinearWarmup']

assert schema['_name'] == 'LinearWarmup'
assert 'lr_scheduler' in schema
assert 'warmup_duration' in schema

print('[OK] LinearWarmup registered:', schema['_name'])
""".replace('REPO_PATH', str(ECDET_ROOT))

    subprocess.run(
        [sys.executable, '-c', verify_code],
        cwd=ECDET_ROOT,
        check=True,
    )

    print('[OK] Restored LinearWarmup compatibility for controlled Phase-6 schedule')



def prepare_pretrain():
    matches = list(INPUT.rglob('ecdet_s.pth'))
    if len(matches) == 1:
        shutil.copy2(matches[0], ECDET_S_PRETRAIN)
        print('[PRETRAIN] using Kaggle Input:', matches[0])
    elif len(matches) > 1:
        raise RuntimeError('Multiple ecdet_s.pth found:\n' + '\n'.join(map(str, matches)))
    else:
        print('[PRETRAIN] downloading official EdgeCrafter ECDet-S release...')
        urllib.request.urlretrieve(ECDET_S_URL, ECDET_S_PRETRAIN)
    if not ECDET_S_PRETRAIN.is_file():
        raise FileNotFoundError(ECDET_S_PRETRAIN)
    size_mb = ECDET_S_PRETRAIN.stat().st_size / 1024 / 1024
    if size_mb < 5:
        raise RuntimeError(f'checkpoint suspiciously small: {size_mb:.2f} MB')
    print(f'[OK] pretrained: {ECDET_S_PRETRAIN} ({size_mb:.2f} MB)')
    return ECDET_S_PRETRAIN


def find_one(filename):
    matches = list(INPUT.rglob(filename))
    if len(matches) != 1:
        raise FileNotFoundError(f'Expected exactly one {filename}; found {len(matches)}:\n' + '\n'.join(map(str, matches[:20])))
    return matches[0]


def load_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def normalize_visdrone(source, destination, split):
    data = load_json(source)
    declared = sorted(int(x['id']) for x in data['categories'])
    ann_ids = sorted({int(x['category_id']) for x in data['annotations']})
    print(f'\n[TAXONOMY {split}] declared={declared} annotations={ann_ids}')
    if declared != list(range(10)):
        raise RuntimeError(f'Unexpected declared categories: {declared}')
    if 10 in ann_ids or 11 in ann_ids:
        mapping = {raw: raw - 1 for raw in range(1, 11)}
        ignored = {0, 11}
        mode = 'RAW_0_11_TO_0_9'
    elif set(ann_ids).issubset(set(range(10))):
        mapping = {i: i for i in range(10)}
        ignored = set()
        mode = 'ALREADY_ZERO_BASED'
    else:
        raise RuntimeError(f'Unsupported annotation IDs: {ann_ids}')
    out_anns = []
    dropped = {0: 0, 11: 0}
    for ann in data['annotations']:
        raw = int(ann['category_id'])
        if raw in ignored:
            if raw in dropped:
                dropped[raw] += 1
            continue
        if raw not in mapping:
            raise RuntimeError(f'Unexpected raw category {raw}')
        item = dict(ann)
        item['source_annotation_category_id'] = raw
        item['category_id'] = int(mapping[raw])
        out_anns.append(item)
    cats = []
    for model_id, cat in enumerate(sorted(data['categories'], key=lambda x: int(x['id']))):
        item = dict(cat)
        item['id'] = model_id
        cats.append(item)
    names = [str(cat['name']).strip().lower() for cat in cats]
    if names != EXPECTED_CATEGORY_NAMES:
        raise RuntimeError(f'Unexpected category names/order: {names}')
    if len(data['images']) != EXPECTED_SPLIT_IMAGES[split]:
        raise RuntimeError(
            f'Unexpected {split} split size: {len(data["images"])}; '
            f'expected {EXPECTED_SPLIT_IMAGES[split]}'
        )
    out = dict(data)
    out['annotations'] = out_anns
    out['categories'] = cats
    destination.write_text(json.dumps(out, ensure_ascii=False), encoding='utf-8')
    print(f'[OK] {split}: mode={mode}, images={len(out["images"])}, objects={len(out_anns)}, drop0={dropped[0]}, drop11={dropped[11]}')
    return out


def resolve_image_root(images, hint):
    sample = images[:30]
    first = Path(sample[0]['file_name'])
    matches = list(INPUT.rglob(first.name))
    if not matches:
        raise FileNotFoundError(first.name)
    candidates, seen = [], set()
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
    candidates.sort(key=lambda p: (hint.lower() not in str(p).lower(), len(str(p))))
    for root in candidates:
        if all((root / Path(x['file_name'])).is_file() for x in sample):
            print(f'[OK] {hint} root:', root)
            return root, False
    for root in candidates:
        if all((root / Path(x['file_name']).name).is_file() for x in sample):
            print(f'[OK] {hint} root basename-mode:', root)
            return root, True
    raise FileNotFoundError(f'cannot resolve {hint} image root')


def normalize_filenames(annotation_path, root, basename_mode):
    data = load_json(annotation_path)
    for image in data['images']:
        if basename_mode:
            image['file_name'] = Path(image['file_name']).name
        if not (root / image['file_name']).is_file():
            raise FileNotFoundError(root / image['file_name'])
    annotation_path.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
    return data


def make_subset(source, destination, n_images):
    data = load_json(source)
    images = data['images'][:n_images]
    ids = {int(x['id']) for x in images}
    anns = [x for x in data['annotations'] if int(x['image_id']) in ids]
    out = dict(data)
    out['images'] = images
    out['annotations'] = anns
    destination.write_text(json.dumps(out, ensure_ascii=False), encoding='utf-8')
    print(f'[OK] subset {destination.name}: images={len(images)} objects={len(anns)}')


def write_config(path, train_ann, val_ann, train_root, val_root, out_dir, epochs, train_batch, val_batch, smoke=False):
    base = ECDET_ROOT / 'configs' / 'ecdet' / 'ecdet_s.yml'
    if not base.is_file():
        raise FileNotFoundError(base)
    milestone = max(1, epochs - 4) if smoke else LR_MILESTONES[0]
    warmup = min(20, WARMUP_STEPS) if smoke else WARMUP_STEPS
    workers = 0 if smoke else NUM_WORKERS
    config = f'''__include__: ['{base}']

task: detection
num_classes: {NUM_CLASSES}
remap_mscoco_category: False
output_dir: "{out_dir}"
eval_spatial_size: [{INPUT_SIZE}, {INPUT_SIZE}]

epochs: {epochs}
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

# Controlled 20-epoch comparison. Disable ECDet's built-in flat-cosine path.
lrsheduler: null
warmup_iter: {warmup}
flat_epoch: 0

optimizer:
  type: AdamW
  params:
    -
      params: '^(?=.*.backbone)(?!.*(?:norm|bn|bias)).*$'
      lr: {BACKBONE_LR:.8f}
    -
      params: '^(?=.*.backbone)(?=.*(?:norm|bn|bias)).*$'
      lr: {BACKBONE_LR:.8f}
      weight_decay: 0.0
    -
      params: '^(?!.*\\.backbone)(?=.*(?:norm|bn|bias)).*$'
      weight_decay: 0.0
  lr: {MODEL_LR:.8f}
  betas: [0.9, 0.999]
  weight_decay: {WEIGHT_DECAY}

lr_scheduler:
  type: MultiStepLR
  milestones: [{milestone}]
  gamma: {LR_GAMMA}

lr_warmup_scheduler:
  type: LinearWarmup
  warmup_duration: {warmup}

train_dataloader:
  type: DataLoader
  total_batch_size: {train_batch}
  num_workers: {workers}
  shuffle: True
  drop_last: True
  dataset:
    type: CocoDetection
    img_folder: "{train_root}"
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
      policy: stop_epoch
      mosaic_epoch: 999999
      mosaic_prob: 0.0
      # Keep augmentation policy active through the whole controlled run.
      # EdgeCrafter validates stop_epoch against epochs and otherwise silently
      # rewrites it to epochs-2, which would trigger a best.pth reload in
      # ECSolver. Setting stop_epoch == epochs is valid and the epoch loop
      # never reaches it.
      stop_epoch: {epochs}
      remove_ops: ['Mosaic']
  collate_fn:
    type: BatchImageCollateFunction
    mixup_prob: 0.0
    mixup_epoch: 999999

val_dataloader:
  type: DataLoader
  total_batch_size: {val_batch}
  num_workers: {workers}
  shuffle: False
  drop_last: False
  dataset:
    type: CocoDetection
    img_folder: "{val_root}"
    ann_file: "{val_ann}"
    return_masks: False
    transforms:
      type: Compose
      ops:
        - {{type: Resize, size: [{INPUT_SIZE}, {INPUT_SIZE}]}}
        - {{type: ConvertPILImage, dtype: 'float32', scale: True}}
        - {{type: Normalize, mean: [0.485, 0.456, 0.406], std: [0.229, 0.224, 0.225]}}
      policy: default
  collate_fn:
    type: BatchImageCollateFunction

evaluator:
  type: CocoEvaluator
  iou_types: ['bbox']
  verbose: False
'''
    path.write_text(config, encoding='utf-8')
    print('[OK] wrote config:', path)


def validate_yaml(path):
    import yaml
    raw = yaml.safe_load(path.read_text(encoding='utf-8'))
    assert raw['num_classes'] == 10
    assert raw['remap_mscoco_category'] is False
    assert abs(float(raw['optimizer']['lr']) - MODEL_LR) < 1e-12
    assert abs(float(raw['optimizer']['params'][0]['lr']) - BACKBONE_LR) < 1e-12
    assert raw['lr_scheduler']['type'] == 'MultiStepLR'
    assert raw['lr_warmup_scheduler']['type'] == 'LinearWarmup'
    assert int(raw['lr_warmup_scheduler']['warmup_duration']) > 0
    print('[OK] raw YAML validated:', path.name)


def train_smoke(pretrain):
    if SMOKE_OUT.exists():
        shutil.rmtree(SMOKE_OUT)
    print('\n' + '=' * 88)
    print('PHASE 6A SMOKE — 64 train / 16 val / 1 epoch')
    print('=' * 88)
    run([
        sys.executable, 'train.py', '-c', SMOKE_CFG, '-t', pretrain,
        '--use-amp', '--seed', '0', '-d', 'cuda:0', '--output-dir', SMOKE_OUT
    ], cwd=ECDET_ROOT, env=os.environ.copy(), timeout=60 * 30)
    if not ((SMOKE_OUT / 'last.pth').is_file() or (SMOKE_OUT / 'best.pth').is_file()):
        raise RuntimeError('Smoke ended without checkpoint')
    print('[SMOKE PASS] ECDet-S training pipeline works')


def train_full(pretrain):
    if FULL_OUT.exists():
        shutil.rmtree(FULL_OUT)
    env = os.environ.copy()
    env['OMP_NUM_THREADS'] = '2'
    env['MKL_NUM_THREADS'] = '2'
    print('\n' + '=' * 88)
    print('PHASE 6A FULL TRAIN — ECDet-S VisDrone 20 epochs')
    print('=' * 88)
    if torch.cuda.device_count() >= 2:
        cmd = [
            sys.executable, '-m', 'torch.distributed.run', '--standalone', '--nproc_per_node=2',
            'train.py', '-c', FULL_CFG, '-t', pretrain, '--use-amp', '--seed', '0',
            '--output-dir', FULL_OUT
        ]
    else:
        cmd = [
            sys.executable, 'train.py', '-c', FULL_CFG, '-t', pretrain, '--use-amp', '--seed', '0',
            '-d', 'cuda:0', '--output-dir', FULL_OUT
        ]
    run(cmd, cwd=ECDET_ROOT, env=env, timeout=60 * 60 * 10)
    best = FULL_OUT / 'best.pth'
    if not best.is_file():
        raise RuntimeError('Full training ended without required best.pth')
    print('[OK] ECDet-S VisDrone checkpoint:', best)
    return best


def parse_best():
    log_path = FULL_OUT / 'log.txt'
    if not log_path.is_file():
        return None
    names = ['AP50_95','AP50','AP75','AP_small','AP_medium','AP_large','AR_1','AR_10','AR_100','AR_small','AR_medium','AR_large']
    best = None
    for line in log_path.read_text(encoding='utf-8', errors='ignore').splitlines():
        try:
            item = json.loads(line)
        except Exception:
            continue
        vec = item.get('test_coco_eval_bbox')
        if not isinstance(vec, list) or len(vec) < 12:
            continue
        candidate = {'epoch': int(item.get('epoch', -1))}
        candidate.update({names[i]: float(vec[i]) for i in range(12)})
        if best is None or candidate['AP50_95'] > best['AP50_95']:
            best = candidate
    return best


def main():
    os.environ['PYTHONUNBUFFERED'] = '1'
    os.environ['TOKENIZERS_PARALLELISM'] = 'false'
    os.environ['OMP_NUM_THREADS'] = '2'
    os.environ['MKL_NUM_THREADS'] = '2'

    print_env()
    install_deps()
    prepare_repo()
    patch_torchvision_compat()
    patch_linear_warmup_compat()
    pretrain = prepare_pretrain()

    train_src = find_one('annotations_VisDrone_train.json')
    val_src = find_one('annotations_VisDrone_val.json')
    train_data = normalize_visdrone(train_src, TRAIN_ANN, 'train')
    val_data = normalize_visdrone(val_src, VAL_ANN, 'val')
    train_root, train_base = resolve_image_root(train_data['images'], 'train')
    val_root, val_base = resolve_image_root(val_data['images'], 'val')
    train_data = normalize_filenames(TRAIN_ANN, train_root, train_base)
    val_data = normalize_filenames(VAL_ANN, val_root, val_base)

    print(f'[DATA] train={len(train_data["images"])} val={len(val_data["images"])}')
    make_subset(TRAIN_ANN, SMOKE_TRAIN_ANN, 64)
    make_subset(VAL_ANN, SMOKE_VAL_ANN, 16)

    full_train_batch = TRAIN_TOTAL_BATCH if torch.cuda.device_count() >= 2 else 8
    full_val_batch = VAL_TOTAL_BATCH if torch.cuda.device_count() >= 2 else 8

    write_config(SMOKE_CFG, SMOKE_TRAIN_ANN, SMOKE_VAL_ANN, train_root, val_root, SMOKE_OUT, 1, 2, 2, smoke=True)
    write_config(FULL_CFG, TRAIN_ANN, VAL_ANN, train_root, val_root, FULL_OUT, EPOCHS, full_train_batch, full_val_batch, smoke=False)
    validate_yaml(SMOKE_CFG)
    validate_yaml(FULL_CFG)

    if RUN_SMOKE:
        train_smoke(pretrain)

    chosen = train_full(pretrain)
    best = parse_best()
    print('\n' + '=' * 88)
    print('PHASE 6A TRAINING COMPLETE')
    print('=' * 88)
    print('checkpoint:', chosen)
    if best:
        print(f"best epoch={best['epoch']} AP={best['AP50_95']:.4f} APs={best['AP_small']:.4f} ARs={best['AR_small']:.4f}")
    print('NEXT: run phase6_02_eval_ecdet_vs_deim.py in the SAME Kaggle session.')
    print('=' * 88)


if __name__ == '__main__':
    main()
