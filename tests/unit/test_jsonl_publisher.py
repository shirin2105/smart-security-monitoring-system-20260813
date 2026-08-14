import json
from concurrent.futures import ThreadPoolExecutor

import pytest

from app.cv.contracts import CVEventValidationError, build_intrusion_event
from app.publisher.base import CVEventPublisher
from app.publisher.jsonl_publisher import JsonlPublisher


def intrusion_event(event_id: str):
    return build_intrusion_event(
        event_id=event_id,
        event_state="START",
        camera_id="cam-1",
        event_time="2026-08-14T10:00:00+07:00",
        event_time_s=1.0,
        cv_confidence=0.9,
        persons=[{"track_id": 7, "bbox_xyxy": [1, 2, 3, 4]}],
        zone_id="right-half",
        inside_duration_s=0.5,
    )


def test_jsonl_publisher_implements_cv_event_boundary_and_appends(tmp_path):
    output_path = tmp_path / "events" / "cv-events.jsonl"
    publisher = JsonlPublisher(output_path)

    assert isinstance(publisher, CVEventPublisher)
    assert publisher.publish(intrusion_event("event-1")) is True
    assert publisher.publish(intrusion_event("event-2")) is True

    records = [json.loads(line) for line in output_path.read_text(encoding="utf-8").splitlines()]
    assert [record["event_id"] for record in records] == ["event-1", "event-2"]
    assert all(record["schema_version"] == "cv-event-v1" for record in records)


def test_jsonl_publisher_rejects_invalid_event_before_writing(tmp_path):
    output_path = tmp_path / "cv-events.jsonl"
    invalid = intrusion_event("event-1")
    object.__setattr__(invalid, "schema_version", "invalid")

    with pytest.raises(CVEventValidationError):
        JsonlPublisher(output_path).publish(invalid)

    assert not output_path.exists()


def test_jsonl_publisher_returns_false_when_append_fails(monkeypatch, tmp_path):
    def fail_append(*_args):
        raise OSError("disk full")

    monkeypatch.setattr("app.publisher.jsonl_publisher.append_event_jsonl", fail_append)

    assert JsonlPublisher(tmp_path / "cv-events.jsonl").publish(intrusion_event("event-1")) is False


def test_publishers_serialize_concurrent_writes_to_same_path(tmp_path):
    output_path = tmp_path / "cv-events.jsonl"
    publishers = [JsonlPublisher(output_path) for _ in range(4)]
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(
            lambda index: publishers[index % 4].publish(intrusion_event(f"event-{index}")),
            range(100),
        ))

    records = [json.loads(line) for line in output_path.read_text(encoding="utf-8").splitlines()]
    assert all(results)
    assert len(records) == 100
    assert len({record["event_id"] for record in records}) == 100
