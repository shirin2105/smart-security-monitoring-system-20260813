import pytest
from app.common.schemas import EventCandidate, ObservationData, ArtifactData
from app.common.enums import EventType, SourceEngine, RedactionStatus
from app.common.time_utils import utc_now_iso


def test_event_candidate_schema_validation():
    now_iso = utc_now_iso()
    candidate = EventCandidate(
        candidateId="cam01-ZONE_INTRUSION-restricted_gate-track17-20260730T021528Z",
        sourceEngine=SourceEngine.CV,
        cameraId="cam_01",
        zoneId="restricted_gate",
        eventType=EventType.ZONE_INTRUSION,
        eventDetected=True,
        detectedAt=now_iso,
        firstSeenAt=now_iso,
        lastSeenAt=now_iso,
        confidence=0.92,
        trackCount=1,
        trackIds=[17],
        observations=ObservationData(personCount=1, dwellSeconds=3.5, insideZone=True),
        artifact=ArtifactData(
            available=True,
            contentType="image/jpeg",
            redactionStatus=RedactionStatus.COMPLETE,
            uri="/artifacts/evidence/candidate-001.jpg",
        ),
    )

    assert candidate.candidateId.startswith("cam01")
    assert candidate.sourceEngine == SourceEngine.CV
    assert candidate.eventType == EventType.ZONE_INTRUSION
    assert candidate.observations.dwellSeconds == 3.5
    assert candidate.artifact.redactionStatus == RedactionStatus.COMPLETE
