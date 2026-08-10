import uuid

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.agents import AssessmentRunner
from app.main import app, create_app
from app.services.intake import PersistedIntake
from app.common.time_utils import utc_now_iso
from tests.unit.test_llm_adapter import _make_adapter


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
