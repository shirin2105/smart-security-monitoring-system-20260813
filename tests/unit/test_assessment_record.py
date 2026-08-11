import json

from app.agents.assessment import AssessmentOutcome, AssessmentTelemetry
from app.agents.policy import build_agent_assessment
from app.agents.provider import ProviderDraft
from app.agents.record import AssessmentRecord, AssessmentRecordStore
from tests.unit.test_assessment_runtime import _candidate


def _outcome(candidate=None) -> AssessmentOutcome:
    candidate = candidate or _candidate()
    assessment = build_agent_assessment(
        candidate=candidate,
        draft=ProviderDraft(recommendedSeverity="HIGH", rationale="r"),
        model_name="test-model",
        prompt_version="assessment-v2",
        created_at="2026-08-10T02:00:04Z",
        assessment_id="assess-fixed",
    )
    return AssessmentOutcome(
        assessment=assessment,
        status="completed",
        telemetry=AssessmentTelemetry(
            provider_output_valid=True,
            fallback_used=False,
            latency_ms=12.5,
            model_name="test-model",
            provider_error=None,
        ),
    )


def test_record_store_round_trip_preserves_current_json_shape(tmp_path):
    candidate = _candidate()
    record = AssessmentRecord.from_outcome(candidate=candidate, outcome=_outcome())
    store = AssessmentRecordStore(tmp_path)

    assert store.save(record) is None
    loaded = store.load(candidate.candidateId)

    assert loaded == record
    payload = json.loads((tmp_path / f"enrichment_{candidate.candidateId}.json").read_text(encoding="utf-8"))
    assert set(payload) == {"candidateId", "eventType", "assessment", "telemetry"}
    assert set(payload["telemetry"]) == {
        "latencyMs",
        "model",
        "fallbackUsed",
        "outputValid",
        "error",
        "persistError",
    }


def test_record_store_reads_current_legacy_fixture(tmp_path):
    fixture = {
        "candidateId": "legacy-1",
        "eventType": "ZONE_INTRUSION",
        "assessment": {
            **_outcome().assessment.model_dump(mode="json"),
            "incident_id": "legacy-1",
            "prompt_version": "assessment-v1",
        },
        "telemetry": {
            "latencyMs": 20.0,
            "model": "legacy-model",
            "fallbackUsed": False,
            "outputValid": True,
            "error": None,
            "persistError": None,
        },
    }
    (tmp_path / "enrichment_legacy-1.json").write_text(json.dumps(fixture), encoding="utf-8")

    loaded = AssessmentRecordStore(tmp_path).load("legacy-1")

    assert loaded is not None
    assert loaded.assessment.prompt_version == "assessment-v1"
    assert loaded.telemetry.provider_output_valid is True


def test_iter_records_skips_malformed_files(tmp_path, caplog):
    (tmp_path / "enrichment_bad.json").write_text("not json", encoding="utf-8")

    records = list(AssessmentRecordStore(tmp_path).iter_records())

    assert records == []
    assert "assessment_record_invalid" in caplog.text
