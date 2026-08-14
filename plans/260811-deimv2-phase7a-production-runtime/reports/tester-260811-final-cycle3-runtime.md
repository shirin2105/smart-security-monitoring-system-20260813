# Test Report — 2026-08-11 — DEIMv2 runtime final cycle 3

## Diff-aware scope

- Analyzed 26 changed/untracked paths; config/dependency/runtime changes auto-escalated to full suite.
- Targeted: DEIMv2 detector, ByteTrack tracker, multi-camera runner, DEIMv2 worker runtime.
- Legacy: intrusion, Phase 3, Phase 4, temporal worker EOS integration modules.

## Test Results Overview

- Static compile: PASS, `python -m compileall -q app tests`, 0.215s.
- Diff check: PASS, `git diff --check`.
- Targeted: 15 collected, 15 passed, 0 failed/skipped, 0.64s.
- Legacy integrations: 6 collected, 3 passed, 3 failed, 0 skipped, 2.35s.
- Full `tests/`: 135 items collected, then collection interrupted by 11 module errors in 2.38s; no tests executed.
- Initial targeted attempt: 9 passed, 6 setup errors from inaccessible default pytest temp root; clean rerun with explicit basetemp produced 15/15 pass. Environment-only, not code defect.

## Critical Issues

1. BLOCKER — pinned `trackers==2.5.0.post0` API mismatch. Runtime signature is `ByteTrackTracker.update(self, detections, frame=None)`, but `app/cv/tracker.py:61` calls `update(..., timestamp=timestamp)`. Breaks 3 legacy worker integrations even with empty detections.
2. BLOCKER — real-asset smoke cannot import configured DEIM source. With parent source/checkpoint/backbone and temporary matching YAML outside tracked files, `DEIMv2Detector` fails at `importlib.import_module("engine.core")`: `ModuleNotFoundError: No module named 'engine'`. Configured `source_path` is validated but never added to import resolution.
3. ENVIRONMENT — full suite collection lacks `langgraph`; 11 collection errors. Requirement declares `langgraph>=0.2.0`, but no available local runtime contains it.

## Coverage Metrics

- Unavailable: neither `coverage` nor `pytest-cov` installed in compatible Python 3.11 runtime. Full collection also blocked.

## Dependency Validation

- Requirements: torch 2.5.1; torchvision 0.20.1; Pillow 12.2.0; supervision 0.30.0; trackers 2.5.0.post0.
- Runtime: torch 2.5.1+cu124; torchvision 0.20.1+cu124; Pillow 12.2.0; supervision 0.30.0; trackers 2.5.0.post0. Versions match pins; tracker usage does not match pinned API.
- Warnings: trackers emits 2 deprecation warnings from BotSort/SORT decorators.

## Scope/Residue Checks

- Production/config/requirements scan: zero YOLO or Ultralytics matches.
- Backend/frontend diff: zero changed files.
- No production code or tracked runtime assets modified during QA.

## Recommendations / Next Steps

1. Fix ByteTrack call to the verified 2.5.0.post0 API; add non-mocked integration assertion exercising real tracker on empty and detected frames.
2. Make loader import `engine.core` from configured `source_path` without global/path ambiguity; rerun real CPU smoke.
3. Retest four legacy modules, targeted 15, then full suite in dependency-complete environment.
4. Install/use coverage tooling and report line/branch/function coverage after full suite passes.

## Unresolved Questions

- None; blockers reproducible and localized.

**Status:** DONE_WITH_CONCERNS
**Summary:** Final cycle 3 QA completed; targeted tests pass, but two production runtime blockers prevent approval.
**Concerns/Blockers:** ByteTrack pinned-API incompatibility; configured DEIM source not importable; full suite/coverage environment incomplete.
