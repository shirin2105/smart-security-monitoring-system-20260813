import uuid
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.publisher.http_publisher import HttpEventPublisher
from app.common.schemas import EventCandidate, ObservationData, ArtifactData
from app.common.enums import EventType, SourceEngine, RedactionStatus
from app.common.time_utils import utc_now_iso


def test_fastapi_event_candidate_ingestion_and_idempotency():
    client = TestClient(app)
    now_iso = utc_now_iso()
    candidate_id = f"test-cand-http-{uuid.uuid4()}"

    payload = {
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
        "observations": {"personCount": 1, "dwellSeconds": 2.5, "insideZone": True},
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

    # 1. First Ingestion -> 201 Created (ACCEPTED)
    response1 = client.post("/internal/api/v1/event-candidates", json=payload, headers={"Idempotency-Key": candidate_id})
    assert response1.status_code == 201
    res_data1 = response1.json()
    assert res_data1["status"] == "ACCEPTED"

    # 2. Duplicate Ingestion -> Idempotent DUPLICATE_IGNORED
    response2 = client.post("/internal/api/v1/event-candidates", json=payload, headers={"Idempotency-Key": candidate_id})
    assert response2.status_code == 201
    res_data2 = response2.json()
    assert res_data2["status"] == "DUPLICATE_IGNORED"
