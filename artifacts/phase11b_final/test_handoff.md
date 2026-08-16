# Phase 11B-FINAL Test Handoff

- Real CUDA DEIMv2 v3 benchmark: 15/15 generic negative clips completed, 443 lifecycle records, 796.1 seconds.
- Frozen benchmark ROI: `CENTRAL_ROI`; diagnostic no-ROI override disabled.
- Abandoned-object START records: 0; false alarms/hour: 0.0.
- Provenance: `production-roi-run-v3.json` records per-clip completion and source hashes plus prediction, dataset-manifest, event-rule, inference-script, and ROI identity.
- Focused final artifact/trace tests: 12 passed.
- Durable focused test output: `focused-tests-v4.xml` (12 passed).
- In-scope CV regression after dependency restoration: 159 passed, 1 skipped; one unrelated production-VLM compatibility test fails because current `CVWorker` has no legacy `abandoned_engine` attribute.
- Whole repository suite: 366 passed, 1 skipped, 8 subtests passed; 10 pre-existing/out-of-scope failures remain in assessment-policy and web-demo compatibility tests.
- Expected terminal behavior: final analyzer returns nonzero while status is `ROI_POLICY_UNRESOLVED`, even when negative safety passes.
