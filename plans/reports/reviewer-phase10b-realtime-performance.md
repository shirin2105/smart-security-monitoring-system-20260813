# Reviewer Report — Phase 10B Realtime-Performance Runtime

Scope: 8 new runtime modules + worker.py / multi_camera_runner.py / config.py integration + 2 test files.
Status: **DONE_WITH_CONCERNS** — 2 critical bugs, several medium/high findings. No files modified.

---

## Critical Findings

### C1 — Tiled inference breaks the real detector contract (numpy vs FrameData)
`app/cv/runtime/tiling.py:197-205` + `app/cv/worker.py:270-283`

`infer_tiles` calls `detector.detect(tile.image)` passing a raw `numpy.ndarray`, and the no-tile fallback calls `detector.detect(frame)` with the same. But `DEIMv2Detector.detect(frame_data: FrameData)` (`app/cv/detector.py:55-56`) dereferences `frame_data.image` — a numpy array has no `.image` attribute → `AttributeError` at runtime.

In production the worker's `self.detector` is a `LockedDetector` (`multi_camera_runner.py:29-31`) forwarding to `DEIMv2Detector.detect`, so any frame routed to `infer_tiles` crashes:
- ACCURATE profile forces `TILE_MODE` for **every** frame (profiles.py:48-50), including frames smaller than 768px where `plan_tiles` returns `[]` and the full-frame fallback runs on a numpy array (`tiling.py:198-199`) → crash.
- BALANCED with a >1.5M-px scene and idle load also selects TILE_MODE.

The unit tests miss this because they use `Mock(detect=...)` lambdas that accept numpy directly (`test_phase10b_worker_integration.py:97-102`).

**Fix:** Make `infer_tiles` adapt the detector call — either (a) construct a minimal `FrameData(camera_id=..., frame_id=..., captured_at=..., source_type=..., source_fps=..., inference_fps=..., image=tile.image)` per tile, or (b) have `_run_inference` pass a wrapper whose `.detect` accepts arrays. Add an integration test using the real `DEIMv2Detector.detect` signature, not a numpy-accepting mock.

---

### C2 — Compounding FPS decay drives camera to 0 FPS under sustained overload
`app/cv/runtime/adaptive_controller.py:91-94`

```
if state is OverloadState.OVERLOADED:
    mode = FULL_FRAME_MODE
    fps = min(fps, self.target_inference_fps / 2.0)
self.target_inference_fps = fps
```

`self.target_inference_fps` starts at the profile target and is **reassigned to the returned fps on every call**, so the `min(fps, target/2)` halves the *running* value each overloaded frame:
- call1: `min(3.5, 7/2)=3.5`, target=3.5
- call2: `min(3.5, 3.5/2)=1.75`
- call3: `min(3.5, 0.875)`
- …→ 0

Because the worker sets `frame_sampler.inference_fps = decision.target_inference_fps` (worker.py:144), a sustained overload makes the camera asymptotically stop processing — the controller **starves the camera to 0 FPS**, violating invariant 1 even though the scheduler itself is fair. The intended behavior was almost certainly `min(fps, base/2)` against the *profile* target.

**Fix:** cap against the profile base, not the running value:
```python
fps = min(fps, self.profile.target_inference_fps / 2.0)
```

---

## High Priority

### H1 — `MetricsCollector` is not actually thread-safe; lock only guards dict creation
`app/cv/runtime/metrics.py:103-126` vs worker mutations `worker.py:306-316, 318-334`

`camera()` returns the `PerCameraMetrics` object and releases the lock; all subsequent field mutations (`metrics.frames_dropped += 1`, `mark_infer()`, `frames_received += 1`) occur **outside** any lock, while `snapshot()` reads them under the lock. `record_drop` (`metrics.py:122-125`) and `mark_infer` (`metrics.py:35-40`) mutate unlocked. In CPython `+=` on int is not atomic; with concurrent workers + a reader thread this is a real data race. The module docstring ("mutations are guarded by a lock") is misleading.

**Fix:** Either hold the lock for the whole read-modify-write cycle in each `record_*`/`mark_*` method, or accept it as best-effort telemetry and say so. Since these feed the adaptive controller's `dropped_ratio` (`worker.py:284-289`), a torn read could produce wrong decisions.

### H2 — Event-boost feature is dead code end-to-end
`worker.py:291-300` (`_has_active_event`), `scheduler.py:84-89` (`set_active_event`), `adaptive_controller.py:121-122`

No adapter implements `has_active_event` (grep over `app/cv/events/` returns nothing), `_has_active_event` always returns `False`, and `set_active_event` is never called anywhere. So `AdaptiveSignal.has_active_event`, the `+1 fps` boost, and the scheduler `_boost` preemption path are all unreachable. Not a correctness bug but the advertised "event boost" feature does nothing and adds dead code.

**Fix:** Wire `scheduler.set_active_event(...)` from the worker based on `_has_active_event()`, or remove the dead paths and document the omission.

---

## Medium Priority

### M1 — `_record_inferred` dereferences `self.profile.name` unconditionally
`worker.py:329`

Backward-compat claim (invariant 5) holds only when `metrics_collector` is also absent. If a `__new__`-built worker has `metrics_collector` set but no `profile` (or `performance_config`), `_record_inferred` raises `AttributeError` at `self.profile.name`. `_ensure_runtime` correctly no-ops on missing config, but the metrics path does not guard. Use `getattr(self.profile, "name", "BALANCED")` or guard on `self.profile is not None`.

### M2 — Stale-drop clock uses wall-clock vs source reader clock skew
`worker.py:259-268`, `rtsp_source.py:167-173`

`_frame_age_ms` computes `time.time() - captured.timestamp()`. RTSP `captured_at` is stamped from `LatestFrameReader` clock (`live_timestamp_iso`), which is wall time — OK if both are the same machine's wall clock. But if `captured_at` lands slightly in the future (clock skew, monotonic reader vs wall), `max(0.0, age)` yields 0 and stale-drop is silently disabled; if the reader clock lags, every frame may be treated as stale and dropped. Worth normalizing to a single clock source and confirming the RTSP clock is wall time at capture.

### M3 — `OverloadStateMachine` drops into DEGRADED/OVERLOADED without entry debounce
`overload_state.py:74-99`

Recovery has hysteresis (`recovery_hold_s`), but the *upward* transitions NORMAL→DEGRADED and NORMAL→OVERLOADED are immediate on a single sample. A single transient 2000 ms spike flips NORMAL→OVERLOADED, next good frame flips OVERLOADED→RECOVERING, then requires a 5 s hold. That's 2 transitions for one spike and mild churn under oscillating latency (OVERLOADED↔RECOVERING). The invariant (no flapping) is *mostly* satisfied by the recovery hold, but there is no minimum hold on entering degraded/overloaded. Consider adding `min_enter_hold` for symmetric hysteresis.

---

## Low Priority / Observations

- **L1** `overload_state.py:40` `_bad_since` is set in `_enter` but never read — dead field (also `_enter` writes it but no logic consumes it).
- **L2** `config.py:46-52` `LatencyBudget.classify` is never used anywhere; dead helper.
- **L3** `adaptive_controller.py:122` event boost `min(base+2, fps+1)` can override an overload degradation (raises fps during OVERLOADED by +1 when an event is active), which is contrary to "graceful degradation"; with H2 dead this is moot today but would bite if the boost is wired up.
- **L4** `metrics.py:40` `actual_inference_fps` is a cumulative rate since `_infer_started_at`, not a rolling window; over a long run it converges to a constant and stops reflecting current load. The controller doesn't use it, but consumers reading metrics should know it is not instantaneous.
- **L5** `worker.py:230` `actual_fps=self.health_monitor.frames_processed` assigns a raw frame *count* to the `actual_fps` field, not a rate.
- **L6** `test_phase10b_runtime.py:368-389` concurrent fairness test uses `time.sleep(0.001)` inside the critical section; it asserts `>0` on both counters so it won't falsely pass, but it is timing-sensitive — with `starvation_threshold_ms=500` and a 0.001 s sleep it never exercises the preemption path it claims to (elapsed per loop ~0.001 s << 0.5 s). Preemption is only really exercised by `test_scheduler_prevents_starvation_after_threshold`.

---

## Invariant Verdicts

1. **No camera starved to 0 FPS (scheduler)** — scheduler itself is fair (round-robin + 1.5 s preemption + weight tokens). ✅ but **violated end-to-end by C2** (controller drives `target_inference_fps`→0 under sustained overload).
2. **No unbounded backlog / stale frames dropped** — `_should_drop_stale` drops, `frame_sampler` throttles, RTSP source keeps no queue. ✅ (modulo M2 clock-skew edge).
3. **Hysteresis / no flapping** — recovery hold present; upward transitions unbounded (M3). ⚠️
4. **Profile switch preserves temporal state** — profiles are pure data; state machine + tiling + tracker/track_store untouched by `with_profile`/`resolve_profile`; verified by test. ✅
5. **Backward compat for `__new__`-built workers** — holds when runtime/metrics absent (M1 edge case aside). ✅
6. **Tiled inference offsets + NMS-merges correctly** — offset/NMS *logic* is correct, but the detector call site is **broken in production** (C1). ❌

---

## Recommended Actions (priority order)

1. Fix C1 — adapt `infer_tiles` to the `FrameData` detector contract; add a real-signature integration test.
2. Fix C2 — cap overload FPS against `self.profile.target_inference_fps`, not the running value.
3. Fix H1 — make `MetricsCollector` field mutations atomic (or document as best-effort).
4. Wire or remove the event-boost feature (H2).
5. Add `profile`/`metrics_collector` guards (M1), normalize the stale-drop clock (M2).
6. Consider entry-side hysteresis for overload states (M3).

## Unresolved Questions
- Confirm whether `LatestFrameReader`'s `captured_at` clock is the host wall clock (needed to validate M2).
- Is per-camera adaptive FPS ever expected to go *above* the profile target (L3 event-boost direction), or should overload strictly reduce FPS?

**Status:** DONE_WITH_CONCERNS
