---
phase: 3
title: "Retrieve and report"
status: pending
priority: P1
effort: 50m
dependencies: [2]
---

# Phase 3: Retrieve and Report

## Context Links

- [Monitoring phase](phase-02-submit-and-monitor.md)
- Summary writers and console renderer: `C:/Users/trand/Downloads/Others/deimv2_phase5b_tiling_sweep.py:998-1204`

## Overview

Download the completed output once into a run-specific directory, validate artifact completeness/consistency, and extract exact console evidence without rounding or editorial rewriting.

## Requirements

- Create a new run-specific directory under `artifacts/phase5b-results/`; do not overwrite prior outputs.
- Download via `kaggle kernels output <owner/slug> -p <run-dir>` and capture the complete kernel log separately because `BEST` lines are stdout-only (`source:1172-1195`).
- Retain summary JSON/CSV/Markdown and eight prediction JSON files expected under `phase5b_deimv2_tiling_sweep/` (`source:44-49`, `:929`).
- Final response/report includes the exact final table block, exact `[BEST ACCURACY]` line, and exact trade-off line or exact no-feasible line.

## Architecture and Data Flow

Kaggle output bundle -> run-specific local directory -> schema/completeness validators -> JSON as numeric source of truth. Kaggle log -> delimiter-based extraction from `PHASE 5B FINAL COMPARISON` through output footer -> verbatim table/BEST evidence. JSON recomputation independently checks the source-defined ranking: AP-small, AR-small, AP overall for accuracy; fastest feasible result for AP-small≥0.17 and AR-small≥0.33 (`source:1142-1169`).

## Implementation Steps

1. Download once; inventory paths, sizes, and SHA-256 hashes. Preserve raw log and output bundle.
2. Assert JSON is a list of exactly eight uniquely named results in source order; each row has finite AP/FPS/latency/tiles/VRAM values. Assert CSV and Markdown represent the same rows and rounded values.
3. Assert eight prediction files exist and are valid JSON. Treat missing/partial files as incomplete even if status says COMPLETE.
4. Extract the final console block verbatim using fixed delimiters. Do not reconstruct wording when the log is available. If the Kaggle CLI lacks logs, use the Kaggle version log surface; downloaded JSON may cross-check but cannot substitute for claiming verbatim stdout.
5. Independently recompute `BEST ACCURACY` and feasibility/trade-off selection from JSON, format with the source's exact precision, and compare byte-for-byte with captured lines.
6. Record baseline delta from 0.2271. If absolute difference >0.015, quote the warning and mark all tiling comparisons non-interpretable (`source:1116-1135`).
7. Produce concise final report: kernel/version/status, source hash, artifact path, eight-row table, two BEST lines, baseline gate, anomalies, and no GitHub activity.

## Test Matrix

| Level | Check | Pass condition |
|---|---|---|
| Unit | JSON schema/finite values | eight complete unique rows |
| Integration | artifact inventory | 3 summaries + 8 predictions + captured log |
| Consistency | JSON vs CSV vs Markdown | values/names agree at documented precision |
| Decision | ranking recomputation | exact match to both logged BEST outcomes |
| E2E | final evidence block | verbatim table and lines retained |

## Failure Modes and Risks

| Failure | L×I | Mitigation |
|---|---|---|
| Output download overwrites evidence | M×H | unique timestamp/version directory; hash inventory |
| COMPLETE but partial/corrupt artifacts | L×H | exact count/schema gates; report incomplete, do not infer |
| BEST stdout absent from downloaded files | H×M | capture kernel log separately; never falsely label reconstruction verbatim |
| NaN/Inf or row mismatch | L×H | finite-value/schema and cross-format validation |
| Baseline drift invalidates conclusions | L×H | enforce existing ±0.015 gate; report without recommending winner |

## Rollback

Retrieval is read-only remotely. A bad local download can be removed and re-downloaded into a new empty run directory; never overwrite the first bundle. Reporting rollback is replacement of only the new run report, preserving raw evidence.

## Success Criteria

- [ ] Complete artifact/hash inventory exists.
- [ ] Eight rows pass schema and cross-format checks.
- [ ] Final table and two BEST lines are verbatim and independently verified.
- [ ] Baseline interpretability gate explicitly passes or blocks conclusions.
- [ ] Final report lists any traceback/anomaly and confirms no GitHub commit/push.

## Unresolved Questions

None.
