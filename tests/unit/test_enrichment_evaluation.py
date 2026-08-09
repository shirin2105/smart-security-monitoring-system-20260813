"""EvaluationReporter tests: AI evaluation metrics (SPEC §15 protocol, PRD §10).

The reporter aggregates per-candidate telemetry records into machine-readable
evaluation output: schema-valid rate, fallback rate, severity caps, and
latency percentiles.
"""

import json

from app.services.enrichment_eval import (
    EvaluationRecord,
    EvaluationReporter,
    summarize_records,
)


def _record(
    candidate_id: str,
    *,
    fallback_used: bool = False,
    output_valid: bool = True,
    latency_ms: float = 100.0,
    severity: str = "HIGH",
) -> EvaluationRecord:
    return EvaluationRecord(
        candidate_id=candidate_id,
        event_type="ZONE_INTRUSION",
        fallback_used=fallback_used,
        output_valid=output_valid,
        latency_ms=latency_ms,
        model="test-model",
        severity=severity,
    )


def test_summary_valid_and_fallback_rates():
    records = [
        _record("a", fallback_used=False, output_valid=True),
        _record("b", fallback_used=True, output_valid=False),
        _record("c", fallback_used=False, output_valid=False),
    ]
    summary = summarize_records(records)

    assert summary["total"] == 3
    assert summary["schema_valid_rate"] == 1 / 3
    assert summary["fallback_rate"] == 1 / 3
    assert summary["schema_invalid_but_no_fallback"] == 1


def test_summary_empty_records():
    summary = summarize_records([])
    assert summary["total"] == 0
    assert summary["schema_valid_rate"] is None
    assert summary["fallback_rate"] is None


def test_latency_percentiles():
    records = [_record(str(i), latency_ms=float(i * 10)) for i in range(1, 5)]
    summary = summarize_records(records)

    assert summary["latency_ms"]["p50"] == 25.0
    assert summary["latency_ms"]["p95"] == 38.5

def test_severity_counts_and_caps():
    records = [
        _record("a", severity="HIGH"),
        _record("b", severity="CRITICAL"),
        _record("c", severity="HIGH"),
    ]
    summary = summarize_records(records)

    assert summary["severity_counts"] == {"HIGH": 2, "CRITICAL": 1}


def test_reporter_loads_records_from_directory(tmp_path):
    for i in range(2):
        record = _record(f"cand-{i}", latency_ms=50.0 + i)
        (tmp_path / f"enrichment_cand-{i}.json").write_text(
            json.dumps(
                {
                    "candidateId": record.candidate_id,
                    "eventType": record.event_type,
                    "telemetry": {
                        "fallbackUsed": record.fallback_used,
                        "outputValid": record.output_valid,
                        "latencyMs": record.latency_ms,
                        "model": record.model,
                    },
                    "enrichment": {"recommendedSeverity": record.severity},
                }
            ),
            encoding="utf-8",
        )

    reporter = EvaluationReporter(str(tmp_path))
    summary = reporter.report()

    assert summary["total"] == 2
    assert summary["schema_valid_rate"] == 1.0
    assert summary["severity_counts"]["HIGH"] == 2
