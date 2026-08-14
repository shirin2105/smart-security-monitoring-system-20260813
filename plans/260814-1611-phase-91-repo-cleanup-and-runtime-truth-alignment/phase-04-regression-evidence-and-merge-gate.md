---
phase: 4
title: "Regression, evidence, and merge gate"
status: complete
priority: P1
effort: "3h"
dependencies: [2, 3]
---

# Phase 4: Regression, evidence, and merge gate

## Overview

Prove cleanup did not change current Phase 9 behavior, update evidence docs, and issue a merge-readiness result. This phase is validation-only unless it discovers a Phase 2/3 defect; it must not expand scope.

## Inputs → transformations → outputs

Inputs: cleaned config/docs/code, the Phase 1 baseline, and known video assets/checksums from `reports/phase9-real-video-regression.md:29-41`. Transform: run focused tests, config load, static grep, ABODA regression, and optional manual webcam procedure. Outputs: test command/result table, remaining-hit classification, webcam state, before/after HEAD, modified/deleted file inventory, and merge decision appended to the Phase 1 audit/baseline documents.

## Related files and ownership

- Modify (exclusive): `docs/phase9/phase9_1_cleanup_baseline.md`, `docs/phase9/phase9_1_reference_audit.md`, `docs/architecture/current_cv_runtime.md`, `docs/phase9/WEBCAM_MANUAL_CHECKLIST.md` only for final evidence/status.
- Read only: `tools/phase9/real_video_regression.py`, `reports/phase9-real-video-regression.md:1-41`, all Phase 2/3 outputs.
- Do not modify test fixtures, datasets, video files, artifacts, or Phase 10 scope.

## Required validation matrix

| Layer | Command/scope | Pass condition | Failure handling |
|---|---|---|---|
| Config | load `settings.event_rules` | YAML object and CVWorker construction succeed | config failure blocks merge; restore Phase 2 change. |
| Contract | CVEvent v1 + manager + JSONL publisher tests | schema-valid START/UPDATE/END, dedup, append behavior | blocks merge; classify test defect vs cleanup regression. |
| Unified flow | worker publisher/config, unified worker, EOS, DEIMv2 runtime, intrusion, crowd, Phase7C production tests | one detector/tracker/store path, three adapters, source cleanup | blocks merge; revert Phase 3 first if causally linked. |
| Video | `tools/phase9/real_video_regression.py` with the pinned interpreter; minimum ABODA, then intrusion/crowd/negative when assets are available | validated `cv-event-v1`; expected ABODA lifecycle; detector calls = processed frames | missing optional runtime/assets = `ENVIRONMENT/DEPENDENCY`; behavioral mismatch = `CV TEST FAILURE`. |
| Hardware | `devtools/webcam_cv_test/app.py` manual checklist | human-recorded PASS, or `NOT HARDWARE VERIFIED` | never convert absence of camera into PASS. |
| Static | final grep taxonomy | zero active/current stale VLM/static-region/YOLO/StrongSORT claims | fix documentation/config only; do not delete uncertain code. |

## Implementation steps

1. Record HEAD before/after and exact changed/created/deleted paths. Confirm no tracked/untracked dataset/artifact was altered.
2. Run the focused suite with the repository’s established Phase 9 interpreter. Do not substitute mocks or skip failed tests; report optional backend dependency collection failures separately from CV failures, as baseline evidence does (`reports/phase9-real-video-regression.md:43-46`).
3. Run the known ABODA regression, validate JSONL with the CVEvent v1 contract, record input checksum, processed-frame/detector-call equality, lifecycle states, and emitted event count. Do not benchmark or retune.
4. Execute the checklist only on real hardware. Record user/manual result; cleanup remains mergeable with `NOT HARDWARE VERIFIED` because the completed Phase 9 evidence already classified webcam hardware as manual.
5. Run final grep and append every remaining reference, category, and rationale. Update architecture/current-runtime docs only to correct evidence wording, not to cover failures.
6. Declare `READY` only if all mandatory non-hardware gates pass, all remaining hits are non-active and explained, and no Phase 10/backend/LLM/DB/frontend/retraining file changed. Otherwise `NOT READY` with exact failing gate and rollback commit.

## Risk assessment

| Risk | Likelihood × impact | Mitigation / rollback |
|---|---|---|
| Optional dependency prevents full-suite collection | High × Medium | Preserve full-suite diagnosis but judge CV focused suite independently; never call the full suite pass. |
| Real-video assets/checkpoints unavailable | Medium × High | Mark environment failure, retain prior evidence, and block a new behavioral PASS until an authorized environment runs it. |
| Hardware claim is fabricated | Low × High | Fixed two-state vocabulary and checklist evidence only. |
| Cleanup changes contracts silently | Low × High | Contract/lifecycle/JSONL plus real-video gate; revert causal Phase 2/3 commit independently. |

## Success criteria

- [x] Focused CV tests pass with command/output recorded.
- [x] ABODA minimum regression passes; no fabricated pass.
- [x] Final audit lists residual-hit families and none are stale active unified-CV runtime/current docs.
- [x] Merge status includes the requested closure deliverables and an explicit no-Phase-10 assertion.

## Rollback

Revert the causally failing Phase 2 or Phase 3 commit, re-run the smallest failing gate, then repeat this phase. Documentation evidence changes revert independently.

## Next steps

No implementation of Phase 10 is authorized by this plan.
