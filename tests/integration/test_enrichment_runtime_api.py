"""API integration: ingest endpoint runs enrichment after persistence.

Rules under test (SPEC §9 Agent spec, BRD RULE-03 persist-before-notify):
- a persisted candidate is enriched automatically;
- enrichment failure never fails the ingest response (FR-AI-07 fallback);
- enrichment runs even when the LLM is configured but unavailable.
"""

import copy
import json
import sys
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.common.schemas import EnrichmentOutput
from app.main import app
from app.services.enrichment import EnrichmentResult, EnrichmentService
from tests.unit.test_enrichment_agent import INTRUSION_EVENT
from tests.unit.test_llm_adapter import _make_adapter

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


class _SlowService(EnrichmentService):
    """EnrichmentService variant that sleeps before returning, simulating a slow LLM."""

    def __init__(self, output_dir: str, slow_seconds: float = 1.0):
        super().__init__(output_dir=output_dir)
        self.slow_seconds = slow_seconds

    async def enrich(self, candidate) -> EnrichmentResult:
        time.sleep(self.slow_seconds)
        return EnrichmentResult(
            output=EnrichmentOutput(
                recommendedSeverity="HIGH",
                rationale="slow",
                summary="slow",
                actionChecklist=["c"],
            ),
            fallback_used=True,
            error=None,
            telemetry={"latency_ms": self.slow_seconds * 1000.0},
        )


@pytest.fixture
def client(tmp_path):
    from app.api import events as events_api
    from app.services.intake import PersistedIntake

    original_service = events_api.enrichment_service
    original_intake = events_api.intake
    events_api.enrichment_service = EnrichmentService(
        output_dir=str(tmp_path / "enrichments"),
        llm_adapter=_make_adapter(available=False),
    )
    events_api.intake = PersistedIntake(storage_dir=str(tmp_path / "intake"))
    yield TestClient(app)
    events_api.enrichment_service = original_service
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


def test_ingest_responds_before_enrichment_runs(client, tmp_path):
    """C4: the ingest response must not block on the LLM.

    The endpoint schedules enrichment as a FastAPI background task: the
    response carries only the accepted status (no enrichment field), and the
    enrichment record is produced separately from the request path.
    """
    from app.api import events as events_api
    from app.services.intake import PersistedIntake

    original_service = events_api.enrichment_service
    original_intake = events_api.intake
    try:
        events_api.enrichment_service = _SlowService(
            output_dir=str(tmp_path / "enrichments"), slow_seconds=1.0
        )
        events_api.intake = PersistedIntake(storage_dir=str(tmp_path / "intake3"))

        resp = client.post("/internal/api/v1/event-candidates", json=_payload())

        assert resp.status_code == 201
        body = resp.json()
        assert body["status"] == "ACCEPTED"
        assert "enrichment" not in body
        assert body["candidateId"] == INTRUSION_EVENT["candidateId"]
    finally:
        events_api.enrichment_service = original_service
        events_api.intake = original_intake
