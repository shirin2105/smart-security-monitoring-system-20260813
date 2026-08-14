# System Architecture

## Computer vision runtime

This is the active production CV runtime. One DEIMv2 inference runs per processed
frame. Camera-local ByteTrack feeds one shared `TrackStore` snapshot to the intrusion,
crowd, and Phase7C abandoned-object adapters. `CVEventManager` owns stable event IDs,
`START`/`UPDATE`/`END` lifecycle state, update throttling, and duplicate suppression.

```text
DEIMv2 -> ByteTrack -> shared TrackStore -> three lifecycle adapters
       -> CVEventManager -> CVEvent v1 -> CVEventPublisher -> JsonlPublisher
```

`CVEventPublisher.publish(CVEvent)` is the final CV boundary. The canonical
`JsonlPublisher` appends schema-valid CVEvent v1 records to local JSONL (default
`artifacts/events/cv-events.jsonl`). Phase 9 does not require a backend endpoint;
backend and LLM behavior are outside the CV subsystem.

One lock-protected DEIMv2 Phase 7A detector is shared by camera workers. Its four raw
labels are normalized to `person` and `luggage`, then two camera-local ByteTrack
instances are updated once per processed frame. Disjoint ID namespaces prevent class
and camera state collisions.

DEIMv2 source is provisioned at `third_party/deimv2`. The Phase 7A checkpoint and
DINOv3 backbone are external, read-only release artifacts at the repository-relative
paths in `configs/models.yaml`. Mandatory SHA-256 values verify exact artifacts before loading.
Deployments can select another YAML directory with `CONFIG_DIR` or override individual
assets with `DEIMV2_SOURCE_PATH`, `DEIMV2_CONFIG_PATH`, `DEIMV2_CHECKPOINT_PATH`, and
`DEIMV2_BACKBONE_PATH`; no adjacent-worktree path is assumed. Missing files, digest
mismatches, incompatible weights, or unavailable explicit CUDA stop shared-runner
construction or a direct worker before its source reads begin. Frame inference errors fail that camera under the supervisor; there is
no empty-result or legacy detector fallback. Rollback restores runtime code, pinned
dependencies, config, image, and matching artifacts atomically; persisted contracts
need no migration.

`DEIMV2_BACKBONE_PATH` and `DINOv3STAs.weights_path` inside the YAML selected by
`DEIMV2_CONFIG_PATH` are one paired deployment contract and must resolve to the same
file. A custom backbone therefore requires a matching YAML change; startup rejects a
mismatched pair instead of rewriting deployment configuration at runtime.

The executable owners are `app/cv/detector.py`, `app/cv/tracker.py`,
`app/cv/track_store.py`, `app/cv/worker.py`, `app/cv/event_manager.py`, the adapters
under `app/cv/events/`, and publishers under `app/publisher/`. Deployment defaults live
in `configs/models.yaml` and `configs/deimv2-phase7a-runtime.yaml`.

## Abandoned-object pipeline

The active abandoned-object adapter reuses Phase7C track quality, physical-luggage
stitching, stationary, owner-association, and owner-away logic. It consumes the same
shared tracked-object snapshot as intrusion and crowd and emits lifecycle signals to
`CVEventManager`. The ABODA regression emitted valid abandoned-object `START` and
`END` records at media time 52.519 s, inside the exploratory 48-56 s label window.

The following static-region sequence is retained as legacy documentation only:

1. `StaticRegionDetector` builds a background model, ignores the warm-up baseline, tracks foreground regions by IoU, and exposes a region only after its configured stationary duration.
2. `AbandonedObjectEngine.submit_static_regions()` supplies the active observations to the event engine. With `candidate_source: static_regions`, the engine associates a nearby person when possible, waits for owner absence, validates the crop once per region, deduplicates it, captures evidence, and emits an `ABANDONED_OBJECT` candidate.
3. A cleared region is removed from engine state. If an object later reappears, the detector assigns a new region identity.

The earlier `StaticRegionDetector`, `candidate_source: static_regions`, `app.vlm`, and
Gemma/Hugging Face validation path is **LEGACY**. It may remain in historical demos or
tests, but the unified production worker does not execute it and explicitly ignores
legacy static-region/VLM settings.

## Region validation (LEGACY)

`app/vlm/region_validator.py` provides three modes:

| Mode | Behavior |
|---|---|
| `disabled` | Accepts the CV result without semantic validation. |
| `heuristic` | Deterministic crop-size and contrast checks. This is not VLM inference. |
| `huggingface` | In temporal mode, sends one ordered, multi-image request containing sampled full-scene JPEG frames to Hugging Face's OpenAI-compatible multimodal chat endpoint and accepts only a strict JSON response. Legacy temporal-disabled callers retain crop validation. |

This retained section describes a historical experiment, not the Phase 9 production
worker. Phase 9 has no active VLM dependency.

The Hugging Face adapter enforces a 12 MB aggregate request budget by lowering JPEG quality and, if needed, dropping frames while retaining temporal coverage. It makes no network request when the payload cannot fit the configured budget.

## Temporal full-scene validation (LEGACY)

This retained flow belongs to the earlier static-region experiment and is not enabled
by the unified production worker. Its historical behavior was:

1. Samples full-scene frames at 1 FPS, resizing proportionally so the longest edge is at most 480 pixels.
2. Keeps the camera-local buffer in memory only, with a 12 MB ceiling.
3. When a static-region candidate matures at time `T`, freezes the candidate context and waits through `T+8s`.
4. Selects at most 17 ordered samples from the inclusive `[T-8s, T+8s]` window and sends them in one Hugging Face request.
5. Emits an accepted or fail-open event with the original candidate timestamp `T`; an explicit rejection emits no alert.

If `HF_TOKEN` is absent, the engine still completes the 8-second post-roll window before validation returns `huggingface_unavailable:missing_token`; it then fails open and emits the candidate with timestamp `T`. No Hugging Face network request occurs in this path.

At end-of-stream, `finalize()` drops incomplete temporal windows without calling the validator or emitting a partial-window event. It clears pending state and returns the affected region IDs so the demo can disclose the incomplete count.

## Deterministic video time

`video_timestamp_iso(source_start, frame_offset, source_fps)` derives UTC media time from a fixed source epoch plus the zero-based frame offset divided by FPS. Invalid FPS uses a deterministic 25 FPS fallback. This avoids wall-clock-dependent event IDs and makes repeated processing comparable.

## Multi-camera supervisor

`MultiCameraRunner` runs at most six enabled camera configurations in a thread pool. Workers share one `LockedDetector`, which serializes detector calls. Each camera returns an independent `completed` or `failed` result, so one camera exception does not terminate its peers.

DEIMv2 production startup is fail-closed: the checkpoint and DINOv3 backbone must match pinned 64-hex SHA-256 values before the checkpoint's pickle-bearing payload is deserialized. Detector startup remains inside the worker cleanup boundary, so source release and abandoned-object finalization also run when model construction fails. ByteTrack first-seen metadata is retained through its configured lost-track window and pruned after continuity can no longer be restored.

This is bounded supervision, not evidence of six-camera production throughput. The repository has a unit test for the six-camera cap, shared detector, and failure isolation, but no real six-camera benchmark, load test, latency target, or hardware capacity result.

## Canonical real-data demo (LEGACY)

From the repository root:

```bash
python scripts/generate_static_abandoned_demo.py
```

The default run uses a 6-second static-region threshold, reads the existing PETS clip without modifying it, and writes:

- `examples/static-abandoned-pets2006-demo.mp4` — annotated output video.
- `artifacts/static-abandoned-pets2006-summary.json` — source SHA-256, source-integrity flag, configuration, media metadata, events, evidence references, and validation disclosure.

Two committed summaries provide a direct comparison on the same untouched PETS source:

- `artifacts/static-abandoned-pets2006-summary.json` records a real Hugging Face temporal run using `google/gemma-3-4b-it`. One false-person region matured at `14.666667s`, was decided at `22.666667s`, used 16 ordered full-scene frames, and was rejected with confidence `0.99`. No alert was emitted. Processing stopped after the configured first VLM decision, so this artifact covers 681 of 1,510 source frames.
- `artifacts/static-abandoned-pets2006-detector-summary.json` records the detector/heuristic comparison over all 1,510 frames. It emitted three alerts; the first was at `45.5s`.

These are run observations, not labeled accuracy or benchmark claims. The Hugging Face summary reports `semantic_vlm_executed: true` from a successfully parsed `huggingface_vlm:` decision even though the decision suppresses the event; the heuristic comparison truthfully reports `false`.

The legacy standalone demo can select the semantic adapter. For an authenticated run,
set `HF_TOKEN` in the process environment and run:

```bash
python scripts/generate_static_abandoned_demo.py --validation huggingface
```

Provider availability and model access are external dependencies. Always inspect `semantic_vlm_executed` and `validation_disclosure` in the generated summary before claiming semantic inference occurred.

## Agent assessment

`AssessmentRunner.assess(EventCandidate)` is the Agent module interface. It owns a private once-compiled LangGraph workflow, the OpenAI-compatible provider adapter, deterministic fallback, advisory policy, and typed assessment-record persistence. Callers and behavioral tests do not access graph state.

The candidate-ingest route persists and canonicalizes an accepted candidate before scheduling `AssessmentHandoff`. The handoff is best-effort: provider and schema failures produce deterministic fallback records, while unexpected defects are logged with candidate/event identity and remain isolated from the `201` ingest response. A process crash after `201` can still lose an assessment job; the system does not claim durable background execution.

Assessment records retain the `enrichment_<candidateId>.json` filename and the existing `candidateId`, `eventType`, `assessment`, and `telemetry` JSON shape. Evaluation loads records through the same typed record implementation.

## References

- [`development-roadmap.md`](./development-roadmap.md)
- [`project-changelog.md`](./project-changelog.md)
- [`architecture_diagram.md`](./architecture_diagram.md)
