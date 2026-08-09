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
from app.services.enrichment import EnrichmentService
from tests.unit.test_enrichment_agent import INTRUSION_EVENT
from tests.unit.test_llm_adapter import _make_adapter

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


@pytest.fixture
def client(tmp_path):
    from app.api import events as events_api
    from app.common.idempotency import IdempotencyStore

    original_service = events_api.enrichment_service
    original_store = events_api.idempotency_store
    events_api.enrichment_service = EnrichmentService(
        output_dir=str(tmp_path / "enrichments"),
        llm_adapter=_make_adapter(available=False),
    )
    events_api.idempotency_store = IdempotencyStore(storage_file=str(tmp_path / "idempotency.json"))
    yield TestClient(app)
    events_api.enrichment_service = original_service
    events_api.idempotency_store = original_store


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
    assert record["enrichment"]["recommendedSeverity"] == "HIGH"
    assert record["telemetry"]["fallbackUsed"] is True


def test_duplicate_ingest_ignored_without_second_enrichment(client, tmp_path):
    resp1 = client.post("/internal/api/v1/event-candidates", json=_payload())
    assert resp1.status_code == 201
    resp2 = client.post("/internal/api/v1/event-candidates", json=_payload())
    assert resp2.status_code == 201
    assert resp2.json()["status"] == "DUPLICATE_IGNORED"

    enrichment_files = list(tmp_path.glob("enrichments/enrichment_*.json"))
    assert len(enrichment_files) == 1
