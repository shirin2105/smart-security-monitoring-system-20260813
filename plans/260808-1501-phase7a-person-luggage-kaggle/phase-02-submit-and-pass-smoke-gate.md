---
phase: 2
title: "Submit and pass smoke gate"
status: completed
priority: P1
effort: "30m plus runtime"
dependencies: [1]
---

# Phase 2: Submit and Pass Smoke Gate

## Context Links

- Smoke contract: [guide](C:/Users/trand/Downloads/Others/PHASE7A_AGENT_GUIDE.md:106)
- Smoke implementation: [script](C:/Users/trand/Downloads/Others/phase7a_person_luggage_deimv2_kaggle.py:915)

## Overview

Push one immutable kernel version, monitor logs, and treat `[SMOKE PASS] 4-class DEIMv2 pipeline works` as the sole authorization for full training.

## Requirements and Data Flow

Kaggle attachments → manifest preparation/audit → smoke subsets (32 VisDrone + 32 COCO train; 8 + 8 val) → one epoch, batch 2, `cuda:0`, AMP, Phase-4 `-t` → `last.pth` → smoke marker. The script then continues automatically; actively monitor so a missing marker or exception is caught before claiming success.

## Related Files and Ownership

- Own during submission: Phase 7A kernel directory only.
- Runtime outputs are Kaggle-version artifacts; no local source edits while a version runs.

## Implementation Steps

1. Push kernel; record kernel slug/version and packaged-source hash.
2. Tail status/logs through environment print, dependency install, dataset readiness/counts, config validation, and smoke completion.
3. If failure occurs before marker, preserve traceback and outputs. Classify as path, dependency/API compatibility, config serialization, GPU/runtime, or input defect.
4. Apply the minimum compatibility/path/runtime fix only; rerun Phase 1 checks and submit a new version. Never alter taxonomy, selection policy, architecture, augmentation, optimizer, schedule, or tuning loader strictness.

## Test Matrix and Success Criteria

- Unit/static: repaired code compiles; locked constants/source diff reviewed.
- Integration: all manifests verify referenced absolute images and IDs.
- Smoke/E2E: 64 train images, 16 val images, one epoch, batch 2, `last.pth`, exact smoke marker.
- [x] `PHASE 7A DATASET READY` and source/class counts captured.
- [x] `[SMOKE PASS] 4-class DEIMv2 pipeline works` captured before full-run acceptance.

## Risk Assessment and Rollback

- High × high: automatic continuation obscures failed smoke. Mitigate log-marker gate plus terminal artifact checks; never infer pass from kernel status alone.
- Medium × high: “fix” changes experiment. Mitigate constant diff and explicit allowed-fix classification.
- Rollback: retain failed version/logs, revert package diff, and resubmit; do not resume a partial run with `-r`.

## Next Steps

Phase 3 begins only with exact marker evidence.

## Unresolved Questions

None.
