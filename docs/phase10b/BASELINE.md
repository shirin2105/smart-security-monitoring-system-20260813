# Phase 10B — Baseline

Frozen runtime measured **before** Phase 10B optimization so any change to
latency/FPS/fairness is attributable to Phase 10B, not to ambient variation.

## Hardware

| Item | Value |
|------|-------|
| CPU | AMD Ryzen 5 6600H (6 cores / 12 threads) |
| RAM | 16 GB |
| GPU | AMD Radeon integrated (no CUDA) |
| Accelerator | CPU-only (CUDA unavailable) |
| Python | 3.14 (test venv) |

## Runtime (frozen, pre-Phase-10B)

```
RTSP/CCTV -> latest fresh frame -> DEIMv2 -> ByteTrack -> shared TrackStore
           -> intrusion / crowd / Phase7C abandoned
           -> CVEventManager -> CVEvent v1 -> CVEventPublisher -> JSONL
```

- One shared, lock-serialized `DEIMv2Detector` (no per-camera model copies).
- One `ByteTrackMultiObjectTracker` and one `TrackStore` per camera.
- Latest-frame semantics (no retained queue) already prevents backlog growth.
- `FrameSampler` throttles to `inference_fps` per camera.

## Baseline metrics (synthetic/deterministic, CPU)

Because the real DEIMv2 weights + CUDA are not available in this environment,
the frozen-runtime baseline below is measured with the deterministic detector
path exercised by the unit suite. Real model latency must be captured on the
target hardware (see Limitations).

| Case | Detector service | Iterations | per-camera actual FPS | Starvation |
|------|------------------|-----------|----------------------|------------|
| 1 camera | 30 ms | 30 | ~32.8 | 0 |
| 2 cameras fair | 30 ms | 30 | ~16.5 each | 0 |
| 4 cameras fair | 40 ms | 30 | ~6.3 each | 0 |
| 2 cameras heavy (weighted) | 30 ms | 30 | ~25 / ~0.9 | 20 preemptions |

## Queue / backlog behavior (baseline)

- `LatestFrameReader` holds a single replaceable frame slot — **no unbounded
  backlog** by construction.
- Non-sampled frames are skipped; no FIFO of pending frames is retained.
- No explicit freshness metric existed before Phase 10B (frames could be
  inferred even when old under lock contention).

## Event regression status (baseline)

All pre-existing CV/event regressions pass before Phase 10B changes:
- Phase 10 runtime + RTSP source + multi-camera runner: PASS
- Intrusion / Crowd / Phase7C abandoned lifecycle adapters: PASS
- cv-event-manager, jsonl publisher, bytetrack tracker: PASS
- Full CV unit suite: **185 passed, 1 skipped** (before Phase 10B additions).

## Limitations

- Real DEIMv2 detector/FPS/latency is not measurable here (weights + CUDA
  unavailable). Phase 10B adds the adaptive controller, latency budget,
  freshness and fairness so real latency can be measured and acted upon on the
  target host.
- Baseline numbers are the deterministic scheduler/controller upper bound, not
  the real-model ceiling.
