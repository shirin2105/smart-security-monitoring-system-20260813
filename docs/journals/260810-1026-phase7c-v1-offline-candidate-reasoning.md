---
date: 2026-08-10
session: phase-7c-v1-offline-candidate-reasoning
---

# Journal: 2026-08-10 — Phase 7C v1 Offline Candidate Reasoning

## Context

Phase 7C v1 added an offline abandoned-object reasoning bundle over the completed Phase 7B.1 `tracks_v4.jsonl` output. The scope was intentionally narrow: no detector rerun, retraining, VLM, Re-ID, or cross-camera logic. The bundle was integrated for local replay and submitted as Kaggle v1 without waiting for remote completion.

## What Happened

The replay processed 5,019 rows across 17 tracks and emitted one candidate, `AO_0001`. Its contract status is `ABANDONED_OBJECT_CANDIDATE`; it retains source tracks `2000004` and `2000005`, owner track `1000005`, and owner-away evidence of 5.005 seconds. Quality screening passed 10 person tracks and two luggage tracks; stitching produced one physical object and one owner association.

The evaluator initially treated the candidate as an alert. That was wrong: this phase has no confirmation decision. The corrected `app/evaluation/phase7c_candidate_metrics.py` now sets `evaluation_scope` to `ABANDONED_OBJECT_CANDIDATE_ONLY`, reports false candidates per video-hour, and leaves false alarms per video-hour undefined. The focused compile and scenario suite passed 19/19.

## Reflection

The important constraint held: this is evidence for a backend or human review path, not an alarm claim. The earlier evaluator representation would have created misleading alarm metrics from candidate-only output. Correcting it before recording results prevented an invalid capability claim.

## Decisions Made

| Decision | Rationale | Impact |
|---|---|---|
| Keep Phase 7C offline and candidate-only | Existing tracks were sufficient for reasoning validation; confirmation requires separate evidence. | No detector, retraining, or VLM work was added. |
| Use candidate-only metrics | `ABANDONED_OBJECT_CANDIDATE` is not a confirmed alert. | Alarm-rate metrics are explicitly unavailable. |
| Do not tune thresholds on one ABODA clip | A single clip cannot justify per-camera defaults. | Baseline thresholds remain unchanged. |
| Submit Kaggle v1 without waiting | Submission is a delivery artifact, not a validation gate. | Remote result remains intentionally untracked. |

## Next Steps

- Video-review owner: review the annotated replay video and record whether the candidate and tracks are visually correct; next evaluation cycle.
- Evaluation owner: assemble a negative, multi-video set before any threshold tuning; retain or revise defaults from documented results.

## Unresolved Questions

- Does annotated-video review confirm `AO_0001` and its stitched source tracks?
- Do negative clips preserve the candidate rate without threshold changes?
