"""EvaluationReporter tests: AI evaluation metrics (SPEC §15 protocol, PRD §10).

The reporter aggregates per-candidate telemetry records into machine-readable
evaluation output: schema-valid rate, fallback rate, severity caps, and
latency percentiles.
"""

from app.agents.record import AssessmentRecord, AssessmentRecordStore
from app.services.enrichment_eval import (
    EvaluationRecord,
    EvaluationReporter,
    summarize_records,
)
from tests.unit.test_assessment_record import _outcome
from tests.unit.test_assessment_runtime import _candidate


def _record(
    candidate_id: str,
    *,
    fallback_used: bool = False,
    output_valid: bool = True,
    latency_ms: float = 100.0,
    severity: str = "high",
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
        _record("a", severity="high"),
        _record("b", severity="critical"),
        _record("c", severity="high"),
    ]
    summary = summarize_records(records)

    assert summary["severity_counts"] == {"high": 2, "critical": 1}


def test_reporter_loads_records_through_record_store(tmp_path):
    store = AssessmentRecordStore(tmp_path)
    first = _candidate().model_copy(update={"candidateId": "cand-1"})
    second = _candidate().model_copy(update={"candidateId": "cand-2"})
    assert (
        store.save(AssessmentRecord.from_outcome(candidate=first, outcome=_outcome(first)))
        is None
    )
    assert (
        store.save(AssessmentRecord.from_outcome(candidate=second, outcome=_outcome(second)))
        is None
    )

    summary = EvaluationReporter(str(tmp_path)).report()

    assert summary["total"] == 2
    assert summary["schema_valid_rate"] == 1.0
    assert summary["severity_counts"] == {"high": 2}
