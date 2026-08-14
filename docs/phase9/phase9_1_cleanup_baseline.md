# Phase 9.1 cleanup baseline

- HEAD before cleanup: `c2dfe42278ebad0ee343a6af6fc08e1ea2be7c4b`.
- Active runtime: `CVWorker` uses DEIMv2, ByteTrack, one shared TrackStore,
  intrusion/crowd/Phase7C adapters, CVEventManager, CVEvent v1 and JsonlPublisher.
- Active rules: `configs/event_rules.yaml` contains only the validated Phase7C
  threshold tree for abandoned-object detection; no static-region or VLM key exists.
- Required regression: CV contract/manager/adapter/worker/publisher tests and the
  ABODA real-video runner. Webcam is manual hardware verification only.
- Dirty/untracked datasets, artifacts, virtual environments, and the temporary
  worktree are not cleanup targets.

## Final closure evidence — 2026-08-14

- Focused unified CV tests: **PASS** (`15 passed`): manager, JSONL publisher,
  worker publisher/configuration, Phase7C production adapter, unified baseline, and
  unified worker.
- ABODA real-video regression: **PASS** using `datasets/aboda-video1.avi` (SHA-256
  `a4b089eddc52631421c3bb834b62de95d11ac78684a69b69305ed9299e1477db`): 320
  processed frames and 320 detector calls, 11 TrackStore tracks, two schema-valid
  `ABANDONED_OBJECT` CVEvent v1 records, valid START-to-END lifecycle, and no duplicate
  record. Evidence: `artifacts/phase91-final-closure-aboda/report.json`.
- Webcam remains **NOT HARDWARE VERIFIED**; the manual checklist keeps it explicitly
  outside automated merge evidence.
- Final reference taxonomy is recorded in `phase9_1_reference_audit.md`. No stale
  active unified-CV runtime/config/current-doc reference remains.
