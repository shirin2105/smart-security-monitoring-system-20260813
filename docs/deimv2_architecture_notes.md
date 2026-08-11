# DEIMv2 Phase 0 Architecture Notes

## Scope and source pin

- Scope: reconnaissance only. No runtime detector, tracker, temporal rule, event
  state machine, dataset, encoder, or feature pyramid was changed.
- Upstream: `https://github.com/Intellindust-AI-Lab/DEIMv2`
- Pinned clone: `third_party/deimv2` at `0fff8d4dcdc272e6cf2d84be31399db471357941`.
- Starting configuration: `third_party/deimv2/configs/deimv2/deimv2_dinov3_s_coco.yml`.
- Source settings: ViT-Tiny (`embed_dim: 192`, `num_heads: 3`), interaction layers
  `[3, 7, 11]`, fixed evaluation size `[640, 640]`, and `num_top_queries: 300`.

## Environment and Phase 0 metric

| Check | Result | Evidence |
| --- | --- | --- |
| Official repository cloned | PASS | pinned SHA above |
| Requested symbols located | PASS | source locations below |
| Input/preprocess traced | PASS | S config and `tools/inference/torch_inf.py:38-51` |
| Python 3.11 + PyTorch 2.5.1 environment | BLOCKED | no Python 3.11 executable available; existing app venv is Python 3.14.4 and has no `torch` |
| Import all DEIMv2 modules | BLOCKED | cannot import `engine.*` without PyTorch |
| Synthetic no-grad DEIMv2-S forward | BLOCKED | requires the missing PyTorch environment and ViT-Tiny weights `ckpts/vitt_distill.pt` |
| Model-quality metrics | N/A | Phase 0 has no evaluation run |

The machine exposes one NVIDIA GeForce RTX 3050 Laptop GPU with 4 GiB VRAM. No
latency or VRAM measurement is recorded because a forward pass did not run.

## Input and preprocessing flow

`tools/inference/torch_inf.py:38-51` opens RGB images, stores the original
size in local `orig_size = [[width, height]]` (passed to the model as
`orig_target_sizes`), resizes to `[640, 640]`, converts
to float tensor `[B, 3, 640, 640]` in `[0, 1]`, then normalizes RGB channels using
ImageNet mean `[0.485, 0.456, 0.406]` and std `[0.229, 0.224, 0.225]`.

The COCO dataloader is `engine/data/dataset/coco_dataset.py:28` (`CocoDetection`),
with training and validation declarations in `configs/dataset/coco_detection.yml`.
The S config uses the same resize/float/normalization sequence and converts
training boxes to normalized `cxcywh` (`deimv2_dinov3_s_coco.yml:55-62`).

## Tensor flow (DEIMv2-S at batch B, 640 by 640)

| Stage | Tensor contract | Evidence |
| --- | --- | --- |
| Input | `[B, 3, 640, 640]`, float32, normalized RGB | config + inference script above |
| `DINOv3STAs` | ViT-Tiny token features reshaped at `H/16,W/16`, then resized and fused with STA | `engine/backbone/dinov3_adapter.py:133-169` |
| Backbone S8 | `c2: [B, 192, 80, 80]` | three interaction levels plus resize math at `:149-155`; 1x1 projection at `:121-125`; returned at `:167-171` |
| Backbone S16 | `c3: [B, 192, 40, 40]` | same proof |
| Backbone S32 | `c4: [B, 192, 20, 20]` | same proof |
| `HybridEncoder` | accepts exactly `len(in_channels)` features, produces three `[B, 192, H, W]` features at S8/S16/S32 | assertion `engine/deim/hybrid_encoder.py:456-458`; FPN/PAN loops `:475-498` |
| `DEIMTransformer` | flattens all levels to `[B, sum(H*W), 192]`, then returns `pred_logits [B,300,80]` and normalized `pred_boxes [B,300,4]` in eval mode | `engine/deim/deim_decoder.py:403-426`, `:525-592`; query count and classes from config/base config |
| `PostProcessor` | returns one dict per image: `labels [300]` (int64), `boxes [300,4]` (floating xyxy in original-pixel space), `scores [300]` (floating sigmoid scores) | `engine/deim/postprocessor.py:50-86` |

The boxes are converted from normalized `cxcywh` to `xyxy` and multiplied by
`orig_target_sizes` at `postprocessor.py:54-55`. With `deploy()` it instead
returns the tuple `(labels, boxes, scores)` at `:73-74`; normal Python inference
returns `list[dict(labels=..., boxes=..., scores=...)]` at `:81-86`.

## Three-level assumptions and S4 insertion boundary

The current DINOv3-S config is explicitly three-level: `interaction_indexes:
[3, 7, 11]` is annotated as S8/S16/S32, while encoder `in_channels` and decoder
`feat_channels` both contain three values. `SpatialPriorModulev2` already computes
an internal S4 `c1`, but returns only `c2,c3,c4` at
`engine/backbone/dinov3_adapter.py:63-69`.

`HybridEncoder` is not hard-coded to three levels: its length assertion and FPN/PAN
construction scale with `len(in_channels)` (`hybrid_encoder.py:415-424,456-498`).
`DEIMTransformer` also supports a number of levels up to `num_levels`, but its S
baseline pins `num_levels: 3` and configures three strides/channels
(`deim_decoder.py:225-261`; `configs/base/deimv2.yml:24-50`). Therefore S4 cannot
be added as a backbone-only change: the backbone output contract, both feature
lists, stride lists, `num_levels`, and decoder attention-level settings must change
together in a later, isolated S4 experiment.

### Exact future S4 edit set (not performed)

1. `third_party/deimv2/engine/backbone/dinov3_adapter.py` — return STA `c1`, add a
   fourth semantic/detail fusion projection and norm, and ensure four selected
   interaction outputs map to S4/S8/S16/S32.
2. `configs/custom/deimv2_s_camera_s4.yml` — new experiment config only; set four
   interaction indices, `DINOv3STAs`/`HybridEncoder` channels and strides
   `[4,8,16,32]`, four decoder feature channels/strides, `num_levels: 4`, and an
   explicit four-entry decoder `num_points` value.
3. `third_party/deimv2/engine/deim/hybrid_encoder.py` — inspect and validate
   `use_encoder_idx`/positional embedding choice for four levels; generic loops
   likely support it, but this needs a real forward test.
4. `third_party/deimv2/engine/deim/deim_decoder.py` — no source change is proven
   necessary, but configuration must satisfy its level/stride assertions and
   multi-scale deformable attention must be validated with four levels.

## Integration boundary, preserved for later phases

The current application detector adapter is `app/cv/detector.py:13`; the worker
calls `detect()` then sends detections to the tracker at `app/cv/worker.py:124-127`.
The DEIMv2 postprocessor is the correct future conversion boundary to the existing
`DetectionResult` contract in `app/common/schemas.py:6`. No tracker or event code
is a Phase 0 target.

## Files modified and gate

- Added: `docs/deimv2_architecture_notes.md`
- Cloned, unmodified upstream source: `third_party/deimv2`

Phase 0 is **not complete**. The architecture gate remains blocked until an
isolated Python 3.11 environment installs the pinned upstream requirements, all
requested modules import, and a no-grad 640x640 DEIMv2-S forward records actual
tensor shapes and postprocessor output types. The source supports a randomly
initialized ViT-Tiny when `vitt_distill.pt` is absent, so that weight is not an
import/shape-forward prerequisite. A verified weight checksum is separately
required before the pretrained baseline's quality, latency, or memory metrics can
be accepted.

## Unresolved questions

- Which source and checksum will supply `vitt_distill.pt` for the reproducible
  baseline?
- Is the RTX 3050 4 GiB device the intended baseline benchmark target, or should
  Phase 1 run on a larger GPU?
