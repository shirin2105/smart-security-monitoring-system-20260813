# Phase 5 result verification

Status: PASS

- Kaggle kernel terminal state: `COMPLETE`.
- Evaluator compiles with Python `py_compile`.
- Repository evaluator SHA-256 equals the user-provided source: `259452CA40ADA0FB180CD2E5AB841323D7C0F36422871B52FD33517685A3E664`.
- JSON contains exactly `baseline_640`, `tile640_no_overlap`, and `tile640_overlap25`; all numeric metrics are finite.
- JSON/CSV/Markdown summary values agree at their documented precision.
- All prediction files parse successfully and contain only `image_id`, `category_id`, `bbox`, and `score`.
- Prediction counts: baseline 164,400; no-overlap 164,123; overlap-25 164,123.
- Every prediction uses category ID 0–9, a positive-width/height bbox, and score within 0–1.
- Baseline AP50:95 `0.2271268` differs from reference `0.2271` by `0.0000268`, passing tolerance `0.015`.
- Report arithmetic and conclusions match downloaded metrics.

Limit: downloaded summaries do not retain checkpoint hash, taxonomy audit, normalized annotation, or provenance fields; this is disclosed in the report.

Unresolved questions: whether the roughly 4.09× latency cost is acceptable on deployment hardware.
