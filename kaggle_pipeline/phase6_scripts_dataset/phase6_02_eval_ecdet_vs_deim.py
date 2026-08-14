"""Phase 6B: evaluate ECDet-S full640 and tile768/20 on VisDrone, compare with frozen DEIMv2 Phase-5B references."""

import os
import sys
import json
import csv
import time
import shutil
import subprocess
from pathlib import Path

import torch

INPUT = Path('/kaggle/input')
WORK = Path('/kaggle/working')
EDGE_REPO = WORK / 'EdgeCrafter'
ECDET_ROOT = EDGE_REPO / 'ecdetseg'
EDGE_COMMIT = '706d037c17c1703bb97f42a35d269959b511b5be'

NUM_CLASSES = 10
EXPECTED_CATEGORY_NAMES = [
    'pedestrian', 'people', 'bicycle', 'car', 'van', 'truck',
    'tricycle', 'awning-tricycle', 'bus', 'motor'
]
EXPECTED_VAL_IMAGES = 548
INPUT_SIZE = 640
TILE_SIZE = 768
TILE_OVERLAP = 0.20
SCORE_THRESHOLD = 0.001
NMS_IOU = 0.60
MAX_DETS = 300

VAL_ANN = WORK / 'visdrone_phase6_eval_val_contiguous.json'
EVAL_CFG = WORK / 'phase6_ecdet_s_eval.yml'
OUT = WORK / 'phase6_ecdet_vs_deim'
SUMMARY_JSON = OUT / 'phase6_comparison.json'
SUMMARY_CSV = OUT / 'phase6_comparison.csv'
SUMMARY_MD = OUT / 'phase6_comparison.md'

DEIM_FULL = {
    'name': 'DEIMv2-S full640 [Phase5B ref]',
    'model': 'DEIMv2-S', 'mode': 'full640',
    'AP50_95': 0.2271, 'AP50': 0.3876, 'AP75': 0.2210,
    'AP_small': 0.1313, 'AR_small': 0.2747,
    'AP_medium': 0.3374414878432185, 'AP_large': 0.5906534886114573,
    'AR_medium': 0.5217424405224486, 'AR_large': 0.7634788202359485,
    'mean_total_latency_ms_per_original_image': 46.5,
    'fps_original_images': 21.49,
    'mean_tiles_per_original_image': 1.0,
    'peak_vram_mb': 92.31689453125,
}
DEIM_TILE = {
    'name': 'DEIMv2-S tile768/20 [Phase5B ref]',
    'model': 'DEIMv2-S', 'mode': 'tile768_overlap20',
    'AP50_95': 0.2654, 'AP50': 0.4510, 'AP75': 0.2604,
    'AP_small': 0.1722, 'AR_small': 0.3403,
    'AP_medium': 0.3809223228970884, 'AP_large': 0.5815224617284779,
    'AR_medium': 0.5651921633601821, 'AR_large': 0.7537071272668727,
    'mean_total_latency_ms_per_original_image': 94.8,
    'fps_original_images': 10.55,
    'mean_tiles_per_original_image': 2.1386861313868613,
    'peak_vram_mb': 92.31689453125,
}

COCO_NAMES = [
    'AP50_95','AP50','AP75','AP_small','AP_medium','AP_large',
    'AR_1','AR_10','AR_100','AR_small','AR_medium','AR_large'
]


def run(cmd, cwd=None, env=None, timeout=None):
    print('\n$ ' + ' '.join(map(str, cmd)), flush=True)
    return subprocess.run(list(map(str, cmd)), cwd=cwd, env=env, check=True, timeout=timeout)


def setup():
    import torchvision
    print('=' * 90)
    print('PHASE 6B — ECDET-S EVALUATION')
    print('=' * 90)
    print('torch:', torch.__version__)
    print('torchvision:', torchvision.__version__)
    if not torch.cuda.is_available():
        raise RuntimeError('CUDA GPU required')
    print('GPU:', torch.cuda.get_device_name(0))
    run([sys.executable, '-m', 'pip', 'install', '-q', 'faster-coco-eval>=1.6.7', 'PyYAML', 'pycocotools', 'scipy', 'transformers', 'calflops'])
    OUT.mkdir(parents=True, exist_ok=True)


def ensure_repo():
    if not EDGE_REPO.is_dir():
        run(['git', 'clone', 'https://github.com/Intellindust-AI-Lab/EdgeCrafter.git', str(EDGE_REPO)])
    run(['git', 'checkout', '--detach', EDGE_COMMIT], cwd=EDGE_REPO)
    actual = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=EDGE_REPO, text=True).strip()
    if actual != EDGE_COMMIT:
        raise RuntimeError(f'EdgeCrafter commit mismatch: {actual}')
    print('[OK] EdgeCrafter commit:', actual)


def patch_torchvision_compat():
    path = ECDET_ROOT / 'engine' / 'data' / 'transforms' / '_transforms.py'
    if not path.is_file():
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
    print('[OK] torchvision compatibility patch applied')


def find_checkpoint():
    same_session = WORK / 'outputs' / 'phase6_ecdet_s_visdrone_full20' / 'best.pth'
    if same_session.is_file():
        print('[CKPT] same-session best.pth:', same_session)
        return same_session
    # For a new notebook/session, save/upload the Phase-6A checkpoint using this explicit name.
    explicit = list(INPUT.rglob('ecdet_s_visdrone_best.pth'))
    if len(explicit) == 1:
        print('[CKPT] Kaggle Input:', explicit[0])
        return explicit[0]
    if len(explicit) > 1:
        raise RuntimeError('Multiple ecdet_s_visdrone_best.pth found')
    raise FileNotFoundError(
        'ECDet-S VisDrone best checkpoint not found. Run Phase 6A in this session, '
        'or upload best.pth renamed to ecdet_s_visdrone_best.pth as Kaggle Input.'
    )


def find_one(filename):
    matches = list(INPUT.rglob(filename))
    if len(matches) != 1:
        raise FileNotFoundError(f'Expected one {filename}; found {len(matches)}:\n' + '\n'.join(map(str, matches[:20])))
    return matches[0]


def load_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def normalize_val(source):
    data = load_json(source)
    declared = sorted(int(x['id']) for x in data['categories'])
    ann_ids = sorted({int(x['category_id']) for x in data['annotations']})
    print('[TAXONOMY] declared:', declared)
    print('[TAXONOMY] annotation IDs:', ann_ids)
    if declared != list(range(10)):
        raise RuntimeError('Unexpected category metadata')
    if 10 in ann_ids or 11 in ann_ids:
        mapping = {raw: raw - 1 for raw in range(1,11)}
        ignored = {0,11}
    elif set(ann_ids).issubset(set(range(10))):
        mapping = {i:i for i in range(10)}
        ignored = set()
    else:
        raise RuntimeError(f'Unsupported IDs {ann_ids}')
    anns = []
    dropped = {0:0, 11:0}
    for ann in data['annotations']:
        raw = int(ann['category_id'])
        if raw in ignored:
            if raw in dropped:
                dropped[raw] += 1
            continue
        item = dict(ann)
        item['category_id'] = int(mapping[raw])
        anns.append(item)
    cats = []
    for model_id, cat in enumerate(sorted(data['categories'], key=lambda x: int(x['id']))):
        item = dict(cat); item['id'] = model_id; cats.append(item)
    names = [str(cat['name']).strip().lower() for cat in cats]
    if names != EXPECTED_CATEGORY_NAMES:
        raise RuntimeError(f'Unexpected category names/order: {names}')
    if len(data['images']) != EXPECTED_VAL_IMAGES:
        raise RuntimeError(
            f'Unexpected val split size: {len(data["images"])}; '
            f'expected {EXPECTED_VAL_IMAGES}'
        )
    out = dict(data); out['annotations'] = anns; out['categories'] = cats
    VAL_ANN.write_text(json.dumps(out, ensure_ascii=False), encoding='utf-8')
    print(f'[OK] val normalized: images={len(out["images"])} objects={len(anns)} drop0={dropped[0]} drop11={dropped[11]}')
    return out


def resolve_val_root(images):
    sample = images[:30]
    first = Path(sample[0]['file_name'])
    matches = list(INPUT.rglob(first.name))
    if not matches:
        raise FileNotFoundError(first.name)
    roots, seen = [], set()
    for match in matches:
        current = match.parent
        for _ in range(8):
            key = str(current.resolve())
            if key not in seen:
                seen.add(key); roots.append(current)
            if current == INPUT: break
            current = current.parent
    roots.sort(key=lambda p: ('val' not in str(p).lower(), len(str(p))))
    for root in roots:
        if all((root / Path(x['file_name'])).is_file() for x in sample):
            return root, False
    for root in roots:
        if all((root / Path(x['file_name']).name).is_file() for x in sample):
            return root, True
    raise FileNotFoundError('Could not resolve val root')


def normalize_filenames(data, root, basename):
    if basename:
        for image in data['images']:
            image['file_name'] = Path(image['file_name']).name
    for image in data['images']:
        if not (root / image['file_name']).is_file():
            raise FileNotFoundError(root / image['file_name'])
    VAL_ANN.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
    return data


def write_eval_config():
    base = ECDET_ROOT / 'configs' / 'ecdet' / 'ecdet_s.yml'
    text = f'''__include__: ['{base}']
task: detection
num_classes: {NUM_CLASSES}
remap_mscoco_category: False
eval_spatial_size: [{INPUT_SIZE}, {INPUT_SIZE}]
PostProcessor:
  num_top_queries: 300
'''
    EVAL_CFG.write_text(text, encoding='utf-8')
    print('[OK] eval config:', EVAL_CFG)


def load_model(checkpoint):
    for key in list(sys.modules):
        if key == 'engine' or key.startswith('engine.'):
            del sys.modules[key]
    sys.path.insert(0, str(ECDET_ROOT))
    from engine.core import YAMLConfig
    cfg = YAMLConfig(str(EVAL_CFG), resume=str(checkpoint))
    if 'ViTAdapter' in cfg.yaml_cfg:
        cfg.yaml_cfg['ViTAdapter']['skip_load_backbone'] = True
    state_obj = torch.load(checkpoint, map_location='cpu', weights_only=True)
    state = state_obj['ema']['module'] if 'ema' in state_obj else state_obj['model']
    info = cfg.model.load_state_dict(state, strict=True)
    print('[CKPT LOAD]', info)
    class Deploy(torch.nn.Module):
        def __init__(self, model, post):
            super().__init__(); self.model = model.deploy(); self.post = post.deploy()
        def forward(self, images, orig_sizes):
            return self.post(self.model(images), orig_sizes)
    model = Deploy(cfg.model, cfg.postprocessor).to('cuda:0').eval()
    return model


def build_transform():
    import torchvision.transforms as T
    return T.Compose([
        T.Resize((INPUT_SIZE, INPUT_SIZE)),
        T.ToTensor(),
        T.Normalize(mean=[0.485,0.456,0.406], std=[0.229,0.224,0.225]),
    ])


@torch.inference_mode()
def infer_pil(model, transform, image):
    tensor = transform(image).unsqueeze(0).to('cuda:0')
    w,h = image.size
    orig = torch.tensor([[w,h]], dtype=torch.float32, device='cuda:0')
    torch.cuda.synchronize(); start = time.perf_counter()
    with torch.autocast(device_type='cuda', dtype=torch.float16):
        labels, boxes, scores = model(tensor, orig)
    torch.cuda.synchronize(); elapsed = time.perf_counter() - start
    labels = labels[0].detach().cpu().long()
    boxes = boxes[0].detach().float().cpu()
    scores = scores[0].detach().float().cpu()
    keep = scores >= SCORE_THRESHOLD
    return labels[keep], boxes[keep], scores[keep], elapsed


def positions(length, window, overlap):
    if length <= window: return [0]
    stride = max(1, int(round(window * (1-overlap))))
    pos = list(range(0, max(1,length-window+1), stride))
    final = length-window
    if pos[-1] != final: pos.append(final)
    return sorted(set(pos))


def tiles(width, height):
    tw,th = min(TILE_SIZE,width), min(TILE_SIZE,height)
    result, seen = [], set()
    for y0 in positions(height,th,TILE_OVERLAP):
        for x0 in positions(width,tw,TILE_OVERLAP):
            x1=min(width,x0+tw); y1=min(height,y0+th)
            x0=max(0,x1-tw); y0=max(0,y1-th)
            t=(int(x0),int(y0),int(x1),int(y1))
            if t not in seen: seen.add(t); result.append(t)
    return result


def merge(labels, boxes, scores, width, height):
    import torchvision
    if len(scores)==0: return labels,boxes,scores
    boxes = boxes.clone()
    boxes = torch.stack([
        boxes[:,0].clamp(0,width), boxes[:,1].clamp(0,height),
        boxes[:,2].clamp(0,width), boxes[:,3].clamp(0,height)
    ], dim=1)
    valid=((boxes[:,2]-boxes[:,0])>0)&((boxes[:,3]-boxes[:,1])>0)&(scores>=SCORE_THRESHOLD)
    labels,boxes,scores=labels[valid],boxes[valid],scores[valid]
    if len(scores)==0: return labels,boxes,scores
    keep=torchvision.ops.batched_nms(boxes,scores,labels,NMS_IOU)[:MAX_DETS]
    return labels[keep],boxes[keep],scores[keep]


def append_preds(out, image_id, labels, boxes, scores):
    for label, box, score in zip(labels.tolist(), boxes.tolist(), scores.tolist()):
        x1,y1,x2,y2 = map(float,box); w=max(0.,x2-x1); h=max(0.,y2-y1)
        if w>0 and h>0:
            out.append({'image_id':int(image_id),'category_id':int(label),'bbox':[x1,y1,w,h],'score':float(score)})


def coco_eval(pred_path):
    from pycocotools.coco import COCO
    from pycocotools.cocoeval import COCOeval
    gt=COCO(str(VAL_ANN)); preds=json.loads(pred_path.read_text(encoding='utf-8'))
    dt=gt.loadRes(preds); ev=COCOeval(gt,dt,'bbox'); ev.params.imgIds=sorted(gt.getImgIds())
    ev.evaluate(); ev.accumulate(); ev.summarize()
    stats=ev.stats.tolist()
    return {COCO_NAMES[i]:float(stats[i]) for i in range(12)}


def evaluate_mode(name, mode, model, transform, data, root):
    from PIL import Image
    preds=[]; total_times=[]; model_times=[]; counts=[]
    torch.cuda.empty_cache(); torch.cuda.reset_peak_memory_stats()
    n=len(data['images'])
    for idx,info in enumerate(data['images'],1):
        image=Image.open(root/info['file_name']).convert('RGB'); w,h=image.size
        total_start=time.perf_counter()
        if mode=='full640':
            labels,boxes,scores,forward=infer_pil(model,transform,image); count=1
        else:
            ts=tiles(w,h); ls=[]; bs=[]; ss=[]; forward=0.
            for x0,y0,x1,y1 in ts:
                crop=image.crop((x0,y0,x1,y1))
                l,b,s,sec=infer_pil(model,transform,crop); forward+=sec
                if len(s)==0: continue
                b=b.clone()+torch.tensor([float(x0),float(y0),float(x0),float(y0)],dtype=b.dtype)
                ls.append(l.clone()); bs.append(b); ss.append(s.clone())
            count=len(ts)
            if ss:
                labels=torch.cat(ls); boxes=torch.cat(bs); scores=torch.cat(ss)
                labels,boxes,scores=merge(labels,boxes,scores,w,h)
            else:
                labels=torch.empty((0,),dtype=torch.long); boxes=torch.empty((0,4)); scores=torch.empty((0,))
        append_preds(preds,info['id'],labels,boxes,scores)
        elapsed=time.perf_counter()-total_start
        total_times.append(elapsed); model_times.append(forward); counts.append(count)
        if idx==1 or idx%50==0 or idx==n:
            print(f'[{name}] {idx}/{n} tiles={count} dets={len(scores)} latency={elapsed*1000:.1f} ms')
    pred_path=OUT/f'{name}_predictions.json'; pred_path.write_text(json.dumps(preds,ensure_ascii=False),encoding='utf-8')
    metrics=coco_eval(pred_path); mean=sum(total_times)/len(total_times)
    return {
        'name':name,'model':'ECDet-S','mode':mode,**metrics,
        'mean_total_latency_ms_per_original_image':mean*1000,
        'fps_original_images':1/mean,
        'mean_model_forward_ms_per_original_image':sum(model_times)/len(model_times)*1000,
        'mean_tiles_per_original_image':sum(counts)/len(counts),
        'peak_vram_mb':torch.cuda.max_memory_allocated()/1024/1024,
    }


def save_and_print(ec_full, ec_tile):
    rows=[DEIM_FULL,ec_full,DEIM_TILE,ec_tile]
    fields=['name','model','mode','AP50_95','AP50','AP75','AP_small','AP_medium','AP_large','AR_small','AR_medium','AR_large','mean_total_latency_ms_per_original_image','fps_original_images','mean_tiles_per_original_image','peak_vram_mb']
    normalized_rows = [{key: row.get(key) for key in fields} for row in rows]
    SUMMARY_JSON.write_text(json.dumps(normalized_rows,ensure_ascii=False,indent=2),encoding='utf-8')
    with SUMMARY_CSV.open('w',newline='',encoding='utf-8') as f:
        wr=csv.DictWriter(f,fieldnames=fields); wr.writeheader()
        for row in rows: wr.writerow({k:row.get(k) for k in fields})
    md=['# Phase 6 — DEIMv2-S vs ECDet-S','', '| Model/mode | AP | AP50 | AP75 | AP-small | AP-medium | AP-large | AR-small | AR-medium | AR-large | ms/img | FPS | tiles/img | VRAM MB |','|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for row in rows:
        value = lambda key, precision=4: f"{row[key]:.{precision}f}" if row.get(key) is not None else '—'
        md.append(f"| {row['name']} | {value('AP50_95')} | {value('AP50')} | {value('AP75')} | {value('AP_small')} | {value('AP_medium')} | {value('AP_large')} | {value('AR_small')} | {value('AR_medium')} | {value('AR_large')} | {value('mean_total_latency_ms_per_original_image', 1)} | {value('fps_original_images', 2)} | {value('mean_tiles_per_original_image', 2)} | {value('peak_vram_mb', 1)} |")
    md += ['', '## Delta ECDet vs DEIM',
           f"- full640 ΔAP={ec_full['AP50_95']-DEIM_FULL['AP50_95']:+.4f}, ΔAPs={ec_full['AP_small']-DEIM_FULL['AP_small']:+.4f}, ΔARs={ec_full['AR_small']-DEIM_FULL['AR_small']:+.4f}",
           f"- tile768/20 ΔAP={ec_tile['AP50_95']-DEIM_TILE['AP50_95']:+.4f}, ΔAPs={ec_tile['AP_small']-DEIM_TILE['AP_small']:+.4f}, ΔARs={ec_tile['AR_small']-DEIM_TILE['AR_small']:+.4f}"]
    SUMMARY_MD.write_text('\n'.join(md)+'\n',encoding='utf-8')

    print('\n'+'='*100); print('PHASE 6 FINAL COMPARISON'); print('='*100)
    print(f"{'Model / mode':<38}{'AP':>8}{'AP50':>8}{'AP75':>8}{'APs':>8}{'APm':>8}{'APl':>8}{'ARs':>8}{'ARm':>8}{'ARl':>8}{'ms/img':>10}{'FPS':>8}{'tiles':>8}{'VRAM':>10}")
    print('-'*100)
    for row in rows:
        value = lambda key, width, precision: f"{row[key]:>{width}.{precision}f}" if row.get(key) is not None else f"{'—':>{width}}"
        print(f"{row['name']:<38}{value('AP50_95',8,4)}{value('AP50',8,4)}{value('AP75',8,4)}{value('AP_small',8,4)}{value('AP_medium',8,4)}{value('AP_large',8,4)}{value('AR_small',8,4)}{value('AR_medium',8,4)}{value('AR_large',8,4)}{value('mean_total_latency_ms_per_original_image',10,1)}{value('fps_original_images',8,2)}{value('mean_tiles_per_original_image',8,2)}{value('peak_vram_mb',10,1)}")
    print('='*100)
    print(f"full640 ECDet delta: ΔAP={ec_full['AP50_95']-DEIM_FULL['AP50_95']:+.4f} ΔAPs={ec_full['AP_small']-DEIM_FULL['AP_small']:+.4f} ΔARs={ec_full['AR_small']-DEIM_FULL['AR_small']:+.4f}")
    print(f"tile768 ECDet delta: ΔAP={ec_tile['AP50_95']-DEIM_TILE['AP50_95']:+.4f} ΔAPs={ec_tile['AP_small']-DEIM_TILE['AP_small']:+.4f} ΔARs={ec_tile['AR_small']-DEIM_TILE['AR_small']:+.4f}")
    print('Outputs:', SUMMARY_JSON, SUMMARY_CSV, SUMMARY_MD, sep='\n  ')


def main():
    os.environ['PYTHONUNBUFFERED']='1'; os.environ['TOKENIZERS_PARALLELISM']='false'
    setup(); ensure_repo(); patch_torchvision_compat(); checkpoint=find_checkpoint()
    val=normalize_val(find_one('annotations_VisDrone_val.json'))
    root,basename=resolve_val_root(val['images']); val=normalize_filenames(val,root,basename)
    print('[OK] val root:',root); write_eval_config(); model=load_model(checkpoint); transform=build_transform()
    from PIL import Image
    warm=Image.open(root/val['images'][0]['file_name']).convert('RGB')
    print('[WARMUP] 3 forwards')
    for _ in range(3): infer_pil(model,transform,warm)
    ec_full=evaluate_mode('ecdet_s_full640','full640',model,transform,val,root)
    ec_tile=evaluate_mode('ecdet_s_tile768_overlap20','tile768_overlap20',model,transform,val,root)
    save_and_print(ec_full,ec_tile)


if __name__=='__main__':
    main()
