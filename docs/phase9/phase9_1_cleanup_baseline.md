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
