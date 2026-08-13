---
phase: 4
title: "Download, audit, and hand off"
status: completed
priority: P1
effort: "30m"
dependencies: [3]
---

# Phase 4: Download, Audit, and Hand Off

## Context Links

- Required outputs: [guide](C:/Users/trand/Downloads/Others/PHASE7A_AGENT_GUIDE.md:195)
- Required return report: [guide](C:/Users/trand/Downloads/Others/PHASE7A_AGENT_GUIDE.md:209)
- Summary writer: [script](C:/Users/trand/Downloads/Others/phase7a_person_luggage_deimv2_kaggle.py:1408)

## Overview

Download the terminal kernel output into a new versioned local artifact directory, validate content/provenance, and report results without deciding Phase 7B prematurely.

## Requirements and Data Flow

Terminal Kaggle version → full output download → local immutable artifact bundle → JSON/schema/count/hash audit → concise report containing dataset readiness/counts, smoke proof, training/checkpoint, final evaluation, required per-class tile sections, paths, warnings/errors.

## Related Files and Ownership

- Create/own: `artifacts/phase7a-results/` and `reports/phase7a-person-luggage-deimv2-results.md` only after successful download.
- Do not overwrite prior `artifacts/phase7a-results/`; use version suffix if present.

## Implementation Steps

1. Download exact kernel version output; save console log/status where available.
2. Assert nonzero checkpoint and exact audit/summary paths; compute SHA-256 and record Kaggle slug/version/source hash.
3. Parse audit: validate category IDs/names, train/val source counts, class counts, and manifest files. Parse summary: exactly six unique dataset/mode pairs and required metric keys.
4. Cross-check required console sections against JSON; report discrepancies, warnings, single-GPU fallback, best-alias fallback, and any allowed fixes.
5. Present results for review. Do not start tracking, S4, or detector/data redesign.

## Test Matrix and Success Criteria

- Unit/schema: JSON parse and required-key assertions.
- Integration: checkpoint nonzero/hashable; paths align with summary provenance.
- E2E: console, audit, predictions, and summary agree on datasets/modes/classes.
- [x] Exact checkpoint, eval summary, dataset audit, predictions, and logs retained.
- [x] Report includes all eight guide-requested return items.
- [x] Phase 7B decision left pending human metric review.

## Risk Assessment and Rollback

- Medium × high: Kaggle “complete” but missing nested files. Mitigate recursive inventory and hard assertions before completion claim.
- Medium × medium: partial/overwritten local download. Mitigate new versioned directory, hashes, and no-overwrite policy.
- Rollback: remove only incomplete new download directory after preserving failure inventory; re-download exact version. Remote run/input artifacts remain unchanged.

## Backwards Compatibility

Additive artifacts/report only. Existing checkpoints, integrations, runtime detector, and abandoned-object pipeline remain unchanged.

## Next Steps

Human reviews high-angle person retention, meaningful luggage detection, and full-vs-tile choice before authorizing Phase 7B.

## Unresolved Questions

None.
