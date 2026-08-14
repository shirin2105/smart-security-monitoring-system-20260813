---
phase: 2
title: "Port DEIMv2 detector and ByteTrack"
status: completed
priority: P1
effort: 6h
dependencies: [1]
---

# Phase 2: Port DEIMv2 detector and ByteTrack

## Context Links

- Webcam DEIM loader and inference: `devtools/webcam_cv_test/model_runtime.py:24-43`, `devtools/webcam_cv_test/model_runtime.py:51-112`
- Parent reusable ByteTrack core: `kaggle_pipeline/phase7b1_kernel/phase7b1_runtime_core.py:28-215` [parent `model-CV-v1` workspace; absent from this worktree]
- Parent merge logic: `kaggle_pipeline/phase7b1_kernel/phase7b1_kaggle_v4_generic_luggage.py:269-325` [parent `model-CV-v1` workspace]
- Current simple implementations: `app/cv/detector.py:13-69`, `app/cv/tracker.py:12-88`

## Overview

Port the smallest stable inference and tracking logic into production-owned modules. Remove YOLO/Ultralytics behavior; retain current application-level interfaces.

## Requirements

- Load frozen Phase 7A DEIMv2-S with `num_classes=4`, no COCO remap, 640x640 evaluation, strict checkpoint state load, EMA preference.
- Device selection: configured `auto|cpu|cuda`; `auto` selects CUDA when available. Explicit unavailable CUDA fails startup.
- Use `torch.inference_mode`; use FP16 autocast on CUDA only; synchronize only for accurate measured latency.
- Normalize backpack/handbag/suitcase to `luggage` with the existing cross-class suppression behavior.
- Use exactly two class-isolated ByteTrack instances and update each once per processed frame, including no-detection frames.
- Avoid `sys.path` mutation and runtime-generated YAML. Production config paths must be explicit and immutable after construction.

## Architecture

### Detector

`DEIMv2Detector` owns model, postprocessor, transform, device, thresholds, and immutable label map. Constructor validates all assets before model construction. `detect` performs one batched inference for one frame and returns current `DetectionResult` objects plus measured latency.

### Tracker

`ByteTrackMultiObjectTracker` owns two trackers and per-track first-seen timestamps. It converts `DetectionResult` arrays to tracker inputs, feeds empty detections to absent classes, validates returned class IDs, namespaces IDs, then emits sorted `TrackResult` values.

### Lifetime check

`CVWorker` constructs its tracker at `app/cv/worker.py:52`; therefore tracker state is per camera worker. `MultiCameraRunner` currently shares only a detector (`app/cv/multi_camera_runner.py:30-37`). Preserve that split: model weights may be shared/locked; tracker state must never be shared between cameras.

## Related Code Files — Exclusive Ownership

- Modify `app/cv/detector.py`: replace `YOLODetector` with production `DEIMv2Detector`; no compatibility alias unless a verified external caller requires it.
- Modify `app/cv/tracker.py`: replace greedy IoU implementation with ByteTrack adapter.
- Optional create `app/cv/deimv2_runtime_support.py` only if `detector.py` would exceed 200 lines; contain loader/transform/merge helpers, no stateful service.
- Do not modify worker, supervisor, config, dependencies, docs, backend, frontend, or tests in this phase.

## Refactor Steps

1. Re-grep all `YOLODetector` and `MultiObjectTracker` callers immediately before editing; enumerate any caller added after this plan.
2. Extract only stable behavior from webcam reference: asset validation, config/model construction, transform, deployed postprocessor, inference context, tensor-to-array conversion.
3. Port merge/NMS as pure helpers; preserve Phase 7A raw taxonomy and normalize output to the existing application vocabulary.
4. Implement detector dependency injection for unit tests without weakening production asset validation.
5. Port ByteTrack wrapper with class isolation and ID namespace. Store first-seen by global ID; remove state when the underlying tracker expires it.
6. Validate inputs: finite confidence, finite ordered `xyxy`, equal array lengths, known normalized classes.
7. Make constructor failures fatal and actionable. Runtime frame inference exceptions propagate to worker/supervisor; do not convert them to empty detections.
8. Run Phase 1 unit tests after each vertical slice.

## Failure Behavior

| Failure | Required behavior | Rationale |
|---|---|---|
| Missing source/config/checkpoint/backbone | startup exception with exact path | prevent silent zero-detection production |
| Incompatible checkpoint/schema | startup exception with cause | wrong weights are unsafe |
| CUDA requested but unavailable/OOM at load | startup failure | explicit operator choice |
| Per-frame inference/device error | camera worker fails; supervisor isolates peer cameras | existing isolation at `app/cv/multi_camera_runner.py:49-56` |
| Empty valid detector result | both trackers receive empty update; return `[]` | track aging must continue |
| Tracker class contamination | raise `RuntimeError` | prevent person/luggage ID corruption |
| Bad box/NaN | reject before tracker | protect native dependency boundary |

## Tests After

- Make all Phase 1 detector/tracker tests pass.
- Add regression for model called exactly once per frame and tracker called exactly once per class/frame.
- Add lifetime test: two tracker objects created for two camera workers; shared detector remains stateless across camera calls.
- Add CPU autocast/synchronize negative test and CUDA-path controlled test through injected torch facade/device.

## Success Criteria

- [x] `rg -n -i "ultralytics|YOLO" app/cv configs/models.yaml requirements.txt` returns no active runtime references after Phase 3.
- [x] Detector output uses only `person` and `luggage` and valid pixel `xyxy` boxes.
- [x] Tracker IDs cannot collide across classes or camera workers.
- [x] Missing/bad assets never yield an apparently healthy empty stream.
- [x] Phase 1 tests pass without real model assets.

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|---|---:|---:|---|
| DEIM source is not packaged in branch/container | H | H | Phase 3 defines explicit source/artifact provisioning and smoke gate |
| Native ByteTrack package version/API drift | M | H | Pin verified version and dependency smoke test |
| Shared detector called concurrently | M | H | Preserve locking wrapper; verify actual shared object flow in Phase 3 |
| Box size order mismatch (`[w,h]` vs `[h,w]`) | M | H | golden non-square frame test matching webcam `model_runtime.py:95-100` |
| Hidden duplicate filtering with CandidateManager | M | H | do not port CandidateManager; event engines remain sole policy owner |

## Security Considerations

- Treat checkpoint/config as trusted deploy artifacts; never download code or weights at request time.
- `torch.load(..., weights_only=False)` can execute pickle payloads. Accept only pinned, checksum-verified internal checkpoint; document SHA-256 in deployment config/report.
- No user-controlled filesystem paths or remote model repository execution.

## Rollback

Revert `app/cv/detector.py`, `app/cv/tracker.py`, and optional helper together. No persisted data or public contract changes.

## Next Steps

Phase 3 wires constructors/configuration and proves deployability.
