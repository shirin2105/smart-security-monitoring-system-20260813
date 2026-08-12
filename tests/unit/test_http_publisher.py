import uuid
from unittest.mock import MagicMock, Mock

import httpx

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.agents import AssessmentRunner
from app.main import app, create_app
from app.services.intake import PersistedIntake
from app.common.time_utils import utc_now_iso
from tests.unit.test_llm_adapter import _make_adapter
from app.common.schemas import EventCandidate
from app.publisher.http_publisher import HttpEventPublisher


def test_global_app_import_remains_compatible():
    assert isinstance(app, FastAPI)


def _event_payload() -> dict:
    now_iso = utc_now_iso()
    candidate_id = f"test-cand-http-{uuid.uuid4()}"
    return {
        "candidateId": candidate_id,
        "sourceEngine": "CV",
        "cameraId": "cam_01",
        "zoneId": "restricted_gate",
        "sourceType": "SIMULATED",
        "eventType": "ZONE_INTRUSION",
        "eventDetected": True,
        "detectedAt": now_iso,
        "firstSeenAt": now_iso,
        "lastSeenAt": now_iso,
        "confidence": 0.95,
        "trackCount": 1,
        "trackIds": [10],
        "observations": {
            "personCount": 1,
            "dwellSeconds": 2.5,
            "insideZone": True,
        },
        "modelVersion": "yolo-v11n",
        "ruleVersion": "intrusion-rule-v1",
        "policyVersion": 1,
        "artifact": {
            "available": True,
            "contentType": "image/jpeg",
            "redactionStatus": "COMPLETE",
            "uri": f"/artifacts/evidence/{candidate_id}.jpg",
        },
    }


def test_fastapi_event_candidate_ingestion_and_idempotency(tmp_path):
    application = create_app(
        intake=PersistedIntake(storage_dir=str(tmp_path / "intake")),
        assessment_runner=AssessmentRunner(
            output_dir=str(tmp_path / "assessment"),
            llm_adapter=_make_adapter(available=False),
        ),
    )
    client = TestClient(application)
    payload = _event_payload()

    first = client.post(
        "/internal/api/v1/event-candidates",
        json=payload,
        headers={"Idempotency-Key": payload["candidateId"]},
    )
    second = client.post(
        "/internal/api/v1/event-candidates",
        json=payload,
        headers={"Idempotency-Key": payload["candidateId"]},
    )

    assert first.status_code == 201
    assert first.json()["status"] == "ACCEPTED"
    assert second.status_code == 201
    assert second.json()["status"] == "DUPLICATE_IGNORED"


@pytest.mark.parametrize("status_code", [400, 401, 403, 422])
def test_http_publisher_does_not_retry_permanent_client_errors(monkeypatch, status_code):
    client = MagicMock()
    client.__enter__.return_value = client
    client.post.return_value.status_code = status_code
    monkeypatch.setattr("app.publisher.http_publisher.httpx.Client", Mock(return_value=client))
    publisher = HttpEventPublisher("http://backend/ingest", bearer_token="secret", max_retries=3)

    assert publisher.publish(EventCandidate.model_validate(_event_payload())) is False
    assert client.post.call_count == 1
    assert client.post.call_args.kwargs["headers"]["Authorization"] == "Bearer secret"


@pytest.mark.parametrize("status_code", [408, 429, 500, 503])
def test_http_publisher_retries_transient_statuses(monkeypatch, status_code):
    client = MagicMock()
    client.__enter__.return_value = client
    client.post.side_effect = [Mock(status_code=status_code), Mock(status_code=201)]
    monkeypatch.setattr("app.publisher.http_publisher.httpx.Client", Mock(return_value=client))
    monkeypatch.setattr("app.publisher.http_publisher.time.sleep", Mock())
    publisher = HttpEventPublisher("http://backend/ingest", bearer_token="secret", max_retries=2)

    assert publisher.publish(EventCandidate.model_validate(_event_payload())) is True
    assert client.post.call_count == 2


def test_http_publisher_retries_transport_exception(monkeypatch):
    client = MagicMock()
    client.__enter__.return_value = client
    request = httpx.Request("POST", "http://backend/ingest")
    client.post.side_effect = [httpx.ConnectError("offline", request=request), Mock(status_code=201)]
    monkeypatch.setattr("app.publisher.http_publisher.httpx.Client", Mock(return_value=client))
    monkeypatch.setattr("app.publisher.http_publisher.time.sleep", Mock())
    publisher = HttpEventPublisher("http://backend/ingest", bearer_token="secret", max_retries=2)

    assert publisher.publish(EventCandidate.model_validate(_event_payload())) is True
    assert client.post.call_count == 2


def test_http_publisher_fails_closed_without_token(monkeypatch):
    client_factory = Mock()
    monkeypatch.setattr("app.publisher.http_publisher.httpx.Client", client_factory)
    publisher = HttpEventPublisher("http://backend/ingest", bearer_token="   ")

    assert publisher.publish(EventCandidate.model_validate(_event_payload())) is False
    client_factory.assert_not_called()


def test_http_publisher_exposes_backend_receipt_without_changing_boolean_contract(monkeypatch):
    client = MagicMock()
    client.__enter__.return_value = client
    response = Mock(status_code=201)
    response.json.return_value = {"status": "ACCEPTED", "incident": {"id": 42}}
    client.post.return_value = response
    monkeypatch.setattr("app.publisher.http_publisher.httpx.Client", Mock(return_value=client))
    publisher = HttpEventPublisher("http://backend/ingest", bearer_token="secret")
    candidate = EventCandidate.model_validate(_event_payload())

    assert publisher.publish(candidate) is True
    assert publisher.last_receipt.candidate_id == candidate.candidateId
    assert publisher.last_receipt.status == "ACCEPTED"
    assert publisher.last_receipt.incident == {"id": 42}
