# Static-Region Demo Needed a Visual Reality Check

**Date**: 2026-08-01 09:57
**Severity**: High
**Component**: Abandoned-object detection and VLM validation
**Status**: Resolved

## What Happened

The abandoned-object path depended on YOLO luggage classes, so an object outside `[24, 26, 28]` could never become a candidate. We replaced that gate with a fixed-camera static-region detector: background subtraction, morphology, contour filtering, region association, media-time persistence, then person-distance context in the existing event engine.

The first “real” demo was still bad evidence. It produced alerts, but review rejected it because the highlighted region did not defensibly enclose an unattended bag. A technically valid MP4 and JSON file had fooled us into calling the result done.

## The Brutal Truth

That rejection was deserved. We optimized for an event appearing in the summary instead of verifying that the box meant what the slide would claim. Seeing a passing script after this much plumbing was relieving, but the relief made us careless. A false-positive demo is worse than no demo because it advertises a capability the pixels do not support.

## Technical Details

The corrected runner routes observations through `AbandonedObjectEngine.submit_static_regions()` instead of assembling candidates beside the engine. `HuggingFaceRegionValidator` now posts a JPEG data URI to the multimodal chat endpoint and strictly parses `verdict`, `confidence`, and `reason`; the earlier local heuristic is explicitly labeled non-semantic.

We selected `tests/clips/pets2006_3.mp4` after visual inspection because the first reported box, `[308, 426, 349, 469]` at frame 1335 (44.5s), encloses the actual unattended bag. The untouched 1,510-frame PETS clip produced three engine events.

## What We Tried

- Rejected class-only YOLO candidates: simple, but blind to unknown bag classes.
- Rejected the first demo clip/result: alerts existed, visual grounding did not.
- Kept heuristic validation for offline operation, but stopped calling it a VLM.
- Added a genuine Hugging Face multimodal adapter; remote failure returns `unavailable` rather than pretending inference happened.

## Root Cause Analysis

We confused pipeline success with semantic correctness. Automated checks validated files, determinism, and contracts; nobody initially required the event bbox to visibly cover the claimed object.

## Lessons Learned

Every vision demo needs human bbox inspection. Generated artifacts are evidence only when the pixels, event route, and disclosed inference mode agree.

## Next Steps

- CV owner, before demo submission: visually review every emitted PETS box and suppress fragmented duplicates.
- ML owner, before enabling remote mode: run an authenticated Hugging Face smoke test and record the semantic verdict without tokens.
- QA owner, next test pass: add a curated negative-clip false-positive gate and coverage tooling.

Limitations remain: the detector assumes a fixed camera; PETS yields three regions for one scene; heuristic mode does not identify objects; semantic VLM was not executed in the recorded artifact; repository-wide starter tests still fail independently, while relevant unit/integration tests passed `31 passed` in 1.12s.
