"""API integration: ingest endpoint runs enrichment after persistence.

Rules under test (SPEC §9 Agent spec, BRD RULE-03 persist-before-notify):
- a persisted candidate is enriched automatically;
- enrichment failure never fails the ingest response (FR-AI-07 fallback);
- enrichment runs even when the LLM is configured but unavailable.
"""

import copy
import json
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from tests.integration.test_enrichment_pipeline import INTRUSION_EVENT
from tests.unit.test_llm_adapter import _make_adapter

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


@pytest.fixture
def client(tmp_path):
    from app.agents import AssessmentRunner
    from app.api import events as events_api
    from app.services.intake import PersistedIntake

    original_runner = events_api.assessment_runner
    original_intake = events_api.intake
    events_api.assessment_runner = AssessmentRunner(
        output_dir=str(tmp_path / "enrichments"),
        llm_adapter=_make_adapter(available=False),
    )
    events_api.intake = PersistedIntake(storage_dir=str(tmp_path / "intake"))
    yield TestClient(app)
    events_api.assessment_runner = original_runner
    events_api.intake = original_intake


def _payload() -> dict:
    return copy.deepcopy(INTRUSION_EVENT)


def test_ingest_persists_candidate_and_enrichment(client, tmp_path):
    resp = client.post("/internal/api/v1/event-candidates", json=_payload())
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "ACCEPTED"

    enrichment_files = list(tmp_path.glob("enrichments/enrichment_*.json"))
    assert len(enrichment_files) == 1
    record = json.loads(enrichment_files[0].read_text(encoding="utf-8"))
    assert record["candidateId"] == INTRUSION_EVENT["candidateId"]
    assert record["assessment"]["severity"] == "high"
    assert record["assessment"]["recommended_action"] == "request_guard_verification"
    assert record["telemetry"]["fallbackUsed"] is True


def test_header_identity_flows_to_enrichment_file(client, tmp_path):
    """C2: canonical (header) identity must own the assessment handoff."""
    resp = client.post(
        "/internal/api/v1/event-candidates",
        json=_payload(),
        headers={"Idempotency-Key": "canonical-header-id"},
    )
    assert resp.status_code == 201
    assert resp.json()["candidateId"] == "canonical-header-id"

    files = list(tmp_path.glob("enrichments/enrichment_*.json"))
    assert len(files) == 1
    assert files[0].name == "enrichment_canonical-header-id.json"
    record = json.loads(files[0].read_text(encoding="utf-8"))
    assert record["candidateId"] == "canonical-header-id"
    assert record["assessment"]["incident_id"] == "canonical-header-id"


def test_duplicate_ingest_ignored_without_second_enrichment(client, tmp_path):
    resp1 = client.post("/internal/api/v1/event-candidates", json=_payload())
    assert resp1.status_code == 201
    resp2 = client.post("/internal/api/v1/event-candidates", json=_payload())
    assert resp2.status_code == 201
    assert resp2.json()["status"] == "DUPLICATE_IGNORED"

    enrichment_files = list(tmp_path.glob("enrichments/enrichment_*.json"))
    assert len(enrichment_files) == 1


def test_ingest_response_excludes_assessment(client):
    resp = client.post("/internal/api/v1/event-candidates", json=_payload())

    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "ACCEPTED"
    assert body["candidateId"] == INTRUSION_EVENT["candidateId"]
    assert "enrichment" not in body
    assert "assessment" not in body
