---
phase: 1
title: "Freeze and classify references"
status: complete
priority: P1
effort: "3h"
dependencies: []
---

# Phase 1: Freeze and classify references

## Overview

Produce an evidence-only baseline and a per-reference classification before changing config, docs, code, tests, or datasets. This phase owns no runtime change.

## Data flow

Inputs: current `git status`, HEAD, `configs/event_rules.yaml`, code imports/call sites, tests, scripts, current docs, and Phase 9 evidence. Transform: classify every legacy-term hit as `ACTIVE_RUNTIME`, `ACTIVE_CONFIG`, `CURRENT_DOC`, `LEGACY/HISTORICAL`, `TEST_ONLY`, or `DEAD_CODE`. Outputs: immutable baseline and deletion eligibility matrix; Phase 2/3 consume the matrix.

## Related files and ownership

- Create (exclusive): `docs/phase9/phase9_1_cleanup_baseline.md`, `docs/phase9/phase9_1_reference_audit.md`.
- Read only: `app/cv/worker.py:64-84`, `app/config.py:32-49`, `configs/event_rules.yaml:12-49`, `README.md:111-136`, `docs/system-architecture.md:3-18,49-123`, `reports/phase9-real-video-regression.md:1-41`.
- Do not modify: untracked datasets, `artifacts/**`, `reports/phase9-real-video-regression.md`, completed Phase 9 plan, or unrelated dirty files.

## Implementation steps

1. Record `git status --short`, `git rev-parse HEAD`, branch, interpreter/test commands, active data-flow, and an explicit list of every pre-existing dirty/untracked path. State that these files are excluded from the plan.
2. Re-grep `VLM`, `app.vlm`, `region_validator`, `HuggingFaceRegionValidator`, `StaticRegionDetector`, `candidate_source`, `static_regions`, `gemma`, `YOLO`, `yolo26m`, `ultralytics`, `StrongSORT`, `EventCandidate`, `cv-event-v1`, and `Phase7C` across code/config/docs/tests/scripts.
3. Trace—not just name-match—every candidate deletion to its imports and callers. Enumerate all direct callers; if more than 10, list the first 10 and total. Verify the active worker never imports legacy components (`app/cv/worker.py:7-20`).
4. Create an audit table: path:line, symbol, classification, execution entry point, action (`retain`, `rewrite as LEGACY`, `delete`), owner phase, and proof needed before deletion.
5. Lock the phase-specific ownership list. If a file has mixed active/legacy content, mark it `retain/split deferred`; Phase 9.1 must not refactor it just to make deletion convenient.

## Tests before / gate

- Run a read-only config load using `Settings.load_yaml`/`event_rules` (`app/config.py:32-49`) and capture success without writing artifacts.
- Confirm the baseline grep reflects the committed tree plus dirty state; no test result may be labelled a post-cleanup result.

## Risks and mitigation

| Risk | Likelihood × impact | Mitigation / rollback |
|---|---|---|
| Dirty/untracked dataset or artifact is mistaken for cleanup scope | Medium × High | Record exact paths first; never use recursive deletion; do not stage files in this phase. |
| A name-only search labels compatibility/backend code dead | Medium × High | Require import/call trace and active entry-point proof. Retain on ambiguity. |
| A historical doc is misrepresented as current | Medium × Medium | Classify headings and surrounding prose, not a single token; Phase 2 uses explicit `LEGACY` labels. |

## Success criteria

- [ ] Baseline and reference audit exist, cite file:line evidence, and identify all proposed deletions.
- [ ] Every deletion candidate has zero active config/import/script/test dependency or is excluded from deletion.
- [ ] Dirty/untracked paths are documented but untouched.

## Rollback

Revert only the two Phase 1 Markdown files; source/runtime is unchanged.

## Next steps

Unblocks Phases 2 and 3. Any unresolved classification blocks the corresponding delete, not documentation work.
