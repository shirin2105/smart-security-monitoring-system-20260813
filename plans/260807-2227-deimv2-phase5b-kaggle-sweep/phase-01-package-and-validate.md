---
phase: 1
title: "Package and validate"
status: pending
priority: P1
effort: 20m
dependencies: []
---

# Phase 1: Package and Validate

## Context Links

- Supplied source: `C:/Users/trand/Downloads/Others/deimv2_phase5b_tiling_sweep.py`
- Prior kernel contract: [kernel metadata](../../kaggle_pipeline/phase5_kernel/kernel-metadata.json)
- Prior evidence: [Phase 5 report](../../reports/deimv2_phase5_tiling_report.md)

## Overview

Create a separate, private Phase 5B kernel package. Copy the supplied source without text decoding/re-encoding, then prove byte identity and metadata correctness before any network mutation.

## Requirements

- Create: `kaggle_pipeline/phase5b_kernel/deimv2_phase5b_tiling_sweep.py` and `kernel-metadata.json`.
- Metadata: new unique kernel ID/title, script code file, private, GPU true, `NvidiaTeslaT4`, internet true, exactly the existing VisDrone and checkpoint dataset IDs.
- Do not modify/delete existing files. Source copy must use binary-preserving filesystem copy.

## Architecture and Data Flow

External source bytes -> filesystem copy -> SHA-256 equality -> AST/compile parse -> invariant scanner -> Kaggle package. Metadata is control-plane input only; model/data bytes remain dataset attachments.

## Implementation Steps

1. Record source path, size, modified time, SHA-256; copy into the new kernel directory; recompute SHA-256 and fail on mismatch.
2. Create metadata based on the verified Phase 5 contract (`kernel-metadata.json:2-16`) but with a new Phase 5B ID/title and Phase 5B code filename.
3. Parse source with `ast.parse` (no import/GPU execution). Parse metadata JSON. Assert `code_file` exists, private/GPU/internet flags, one-T4 shape, and exact two dataset IDs.
4. Assert eight unique experiment names and required constants/output paths (`source:44-105`); assert prohibited tokens/features were not introduced and source hash remains unchanged.
5. Verify Kaggle CLI availability/authentication without printing credentials; use the functioning project interpreter/module if the stale `.venv-deimv2` launcher cannot start.

## Test Matrix

| Level | Check | Pass condition |
|---|---|---|
| Unit/static | Python AST; JSON parse | no syntax/schema parse error |
| Contract | hash before/after copy | exact SHA-256 match |
| Contract | metadata/source linkage | `code_file` names existing copied file |
| Integration-static | input/GPU settings | exact datasets, private, internet, one T4 |
| Scope | experiment/invariant scan | eight expected rows; no training/out-of-scope additions |

## Failure Modes and Risks

| Failure | L×I | Mitigation |
|---|---|---|
| Copy changes bytes/newlines | M×H | binary copy + SHA-256 hard gate |
| Kernel ID overwrites Phase 5 | L×H | unique Phase 5B ID; reject prior ID |
| Wrong/multiple inputs break unique resolver | M×H | exact dataset list; no extra checkpoint dataset |
| Stale Kaggle launcher | H×M | locate working Python/Kaggle module; diagnose environment only, never alter source |

## Rollback

Delete only the new unsubmitted `phase5b_kernel` directory. Existing Phase 5 files remain unchanged.

## Success Criteria

- [ ] Hash identity proven.
- [ ] Static test matrix passes.
- [ ] Kernel identity is new and metadata contract exact.
- [ ] No implementation source edits.

## Next Steps

Phase 2 may start only after all gates pass.

## Unresolved Questions

None.
