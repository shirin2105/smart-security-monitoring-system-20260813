# Scout report — DEIMv2 production runtime

Date: 2026-08-11

## Verified current flow

- `CVWorker` constructs YOLO and a greedy IoU tracker at `app/cv/worker.py:45-53`.
- Per processed frame: detector -> tracker -> track store -> event engines -> publisher at `app/cv/worker.py:96-115`.
- Stable detector/tracker boundary types are `DetectionResult`, `TrackResult`, and `FrameData` at `app/common/schemas.py:8-31`.
- Multi-camera runner creates one detector at `app/cv/multi_camera_runner.py:30-37`, but passes its private unlocked detector into workers at `app/cv/multi_camera_runner.py:44-47`; this bypasses the lock defined at lines 15-22.
- Current detector silently sets `model=None` on import/load failures and returns empty detections at `app/cv/detector.py:29-42`; unsafe for production health.
- Current config points to `yolo26m.pt` at `configs/models.yaml:1-6`; requirement declares Ultralytics at `requirements.txt:8-12`.

## Verified reusable behavior

- Webcam runtime validates checkpoint/backbone paths at `devtools/webcam_cv_test/model_runtime.py:24-32`.
- It strictly loads Phase 7A EMA/model state and deploys model/postprocessor at `devtools/webcam_cv_test/model_runtime.py:51-72`.
- It uses 4 raw classes, no COCO remap, 640 input at `devtools/webcam_cv_test/model_runtime.py:74-84`.
- It performs one inference, score filtering, luggage merge, then ByteTrack at `devtools/webcam_cv_test/model_runtime.py:87-113`.
- Its CandidateManager at lines 44-49 and 113-129 must not be ported into the production detector/tracker seam; production event engines already own temporal eligibility.
- Parent `model-CV-v1` workspace contains DEIM source/config, DINOv3 backbone, Phase 7A checkpoint, and Phase 7B.1 runtime core. These are absent/untracked in this worktree and require explicit provisioning.
- Parent Phase 7B.1 core defines two class-isolated trackers and namespaced global IDs at `kaggle_pipeline/phase7b1_kernel/phase7b1_runtime_core.py:132-215`.

## Overlapping plans

- Phase 8 plan is evaluation-only and freezes DEIMv2 Phase 7A + ByteTrack; no production runtime file ownership.
- CV/LLM/Guard integration plan preserves/ports CV seams but does not provide this replacement in the current worktree. Coordinate integration order if both branches later converge; no hard plan dependency established from live files.
- Older DEIM/Kaggle plans concern model evaluation/training artifacts, not this production adapter.

## Scope decision

- Hold narrow scope: detector, tracker, wiring, config/dependencies, tests, operational docs.
- Preserve ingest/backend/frontend and event schema.
- No full external E2E required; unit, integration-seam, clean dependency, and one real-asset smoke are sufficient.

## Unresolved questions

- None blocking.
