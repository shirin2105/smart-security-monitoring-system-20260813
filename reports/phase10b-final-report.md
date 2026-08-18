# Phase 10B — Realtime Performance, Adaptive Inference & Multi-Camera Fairness

## Status: DONE

## Files created / modified

### Created
- `app/cv/runtime/__init__.py` — public API
- `app/cv/runtime/config.py` — `RuntimePerformanceConfig` (+ `LatencyBudget`,
  `AdaptiveTilingConfig`, `SchedulerConfig`, `OverloadConfig`)
- `app/cv/runtime/profiles.py` — FAST / BALANCED / ACCURATE profiles
- `app/cv/runtime/overload_state.py` — NORMAL / DEGRADED / OVERLOADED / RECOVERING
- `app/cv/runtime/adaptive_controller.py` — `AdaptiveInferenceController`
- `app/cv/runtime/tiling.py` — `AdaptiveTiling`, `plan_tiles`, `merge_detections`
- `app/cv/runtime/metrics.py` — `PerCameraMetrics`, `GlobalMetrics`, `MetricsCollector`
- `app/cv/runtime/scheduler.py` — `RealtimeScheduler`
- `configs/runtime_performance.yaml` — Phase 10B config (mirrors spec)
- `docs/phase10b/BASELINE.md` — frozen pre-Phase-10B baseline
- `scripts/phase10b_benchmark.py` — deterministic scheduler benchmark
- `artifacts/phase10b-benchmark.json` — benchmark output
- `tests/unit/test_phase10b_runtime.py` — unit tests (profiles, state, tiling,
  controller, metrics, scheduler)
- `tests/unit/test_phase10b_worker_integration.py` — worker integration tests

### Modified
- `app/config.py` — `runtime_performance` config property
- `app/cv/worker.py` — adaptive controller, scheduler, latency budget,
  freshness-first, tiling, metrics integration
- `app/cv/multi_camera_runner.py` — shared `RealtimeScheduler` + `MetricsCollector`

### Deleted
- none

## Scheduler architecture

`RealtimeScheduler` replaces naive lock contention with explicit turn granting:

- **policy** `round_robin` (default) or `weighted` (weight controls ring slots).
- **grant** happens only when a camera is next in the ring, or **preempts** the
  cursor when it has waited ≥ `starvation_threshold_ms` (anti-starvation).
- **`release_turn`** advances the cursor so the next camera gets the detector.
- **event-aware**: a camera with an active CV event is granted a boost turn.
- Shared `MetricsCollector` records per-camera `scheduler_wait_ms`,
  `inference_count` and global `starvation_count`.

## Adaptive policy

`AdaptiveInferenceController` (deterministic, no ML/RL) consumes a per-camera
signal (source resolution, detector/pipeline latency, actual FPS, dropped
ratio, GPU util, active-event flag) and returns a decision:

1. Overload state machine classifies latency/dropped-ratio/starvation/GPU.
2. **FPS**: NORMAL→profile FPS; DEGRADED→0.7×; OVERLOADED→0.5× (forced
   full-frame); RECOVERING→0.9×; active event→+1 (capped).
3. **Latency budget**: pipeline latency > overloaded → clamp FPS to ≤ 2.
4. **Tiling**: `AdaptiveTiling` picks `tile768_overlap20` for high-res scenes
   (area ≥ threshold) when load allows, else `full640`, with minimum-mode-hold
   hysteresis. OVERLOADED always forces `full640`.
5. **Freshness-first**: live frames older than the overloaded budget are
   dropped (not queued); DEGRADED/OVERLOADED drop frames beyond the acceptable
   budget.

## Profile mapping

| Profile | Target FPS | Tiling intent | Use |
|---------|-----------|---------------|-----|
| FAST | 10 | full640 | max throughput |
| BALANCED (default) | 7 | adaptive | default production |
| ACCURATE | 4 | tile768_overlap20 | max recall |

Profile switch only changes target FPS / tiling intent; it never resets
tracker, `TrackStore` or event state (verified by test).

## Benchmark matrix results (deterministic scheduler, CPU)

| Matrix | Case | Result |
|--------|------|--------|
| P10B-01/02 | 1 camera 30ms | 30/30, ~32.8 FPS, starvation 0 |
| P10B-03 | 2 cameras fair | 30/30 each, ~16.5 FPS, starvation 0 |
| P10B-04 | 2 cameras heavy (weighted) | 30/30 each (light via preemption), starvation 20 |
| P10B-05 | 4 cameras | 30/30 each, ~6.3 FPS, starvation 0 |
| P10B-06/07/08 | DEGRADED/OVERLOADED/recovery | state machine + hysteresis unit-tested |
| P10B-09 | stale drop | unit + integration tested (frames dropped, not queued) |
| P10B-10 | profile switch preserves state | integration tested |
| P10B-11 | RTSP reconnect + scheduler | coexist (RTSP suite PASS) |
| P10B-12 | event regression under skipping | full CV suite PASS |

## Fairness metrics

- Per camera: `source_fps`, `target_inference_fps`, `actual_inference_fps`,
  `detector_latency_ms`, `pipeline_latency_ms`, `frame_age_at_inference_ms`,
  `frames_received/inferred/dropped/skipped`, `scheduler_wait_ms`, `profile`,
  `inference_mode`, `overload_state`.
- Global: `total_inference_rate`, `detector_utilization`, `camera_count`,
  `starvation_count`, `total_frames_dropped`.

## Overload / recovery evidence

- State machine transitions NORMAL→DEGRADED→OVERLOADED→RECOVERING→NORMAL with
  two-sided hysteresis:
  - **upward debounce** (`min_degrade_hold_s`): a transient spike does not churn
    NORMAL→DEGRADED/OVERLOADED;
  - **recovery hold** (`recovery_hold_s`): return to NORMAL requires sustained
    good metrics (no downward flapping).
- Unit-tested: sustained latency spike → OVERLOADED; single spike debounced;
  held recovery → NORMAL; no flapping.
- FPS never compounds to 0 under sustained overload (regression-tested).

## Code review

Independently reviewed; all findings resolved:
- **C1** tiled inference now hands `FrameData` to the detector (DEIMv2 contract)
  instead of raw numpy; regression-tested.
- **C2** overload FPS clamp now caps against the profile base, not the running
  target, so sustained load cannot decay FPS to 0; regression-tested.
- **H1** per-camera metrics mutations are lock-protected.
- **H2** event-aware boost is wired via `CVEventManager.has_active_events()`.
- **M1** profile name access guarded for `__new__`-assembled workers.
- **M3** upward state transitions are debounced.

## Event regressions

Full CV unit suite after Phase 10B changes: **188 passed, 1 skipped**.

- Phase 10 runtime / RTSP source / multi-camera runner: PASS
- Intrusion / Crowd / Phase7C abandoned adapters: PASS
- cv-event-manager / jsonl publisher / bytetrack tracker: PASS
- Phase 10B additions (40 tests): PASS

## Hardware / GPU limitations

- Host: AMD Ryzen 5 6600H, 16 GB, integrated AMD Radeon (no CUDA).
- Real DEIMv2 model weights + CUDA are not available in this environment, so
  real-model latency/FPS baselines and real-tiling overhead were not captured;
  the scheduler/controller/freshness paths were verified deterministically.
- On target hardware, run the benchmark to capture real latency and tune
  `target_inference_fps` / latency budgets via `configs/runtime_performance.yaml`.

## Recommended default profile

**BALANCED** — adaptive tiling + balanced 7 FPS target is the correct production
default. FAST for max throughput on low-res-only feeds; ACCURATE only when
high recall is required on high-res scenes and hardware can afford 4 FPS.

## Merge readiness

**Ready.** All Phase 10B components implemented, unit/integration tested, and
the full CV regression suite passes. No scope creep: no retrain, S4,
EdgeCrafter, Re-ID, TensorRT/ONNX, backend/LLM, new events, or Phase 11.
