from unittest.mock import MagicMock
import pytest

from app.cv.contracts import build_intrusion_event
from app.publisher.base import CVEventPublisher
from app.publisher.composite_publisher import CompositePublisher


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


def test_composite_publisher_implements_cv_event_publisher():
    composite = CompositePublisher([])
    assert isinstance(composite, CVEventPublisher)


def test_composite_publisher_fans_out_events():
    pub1 = MagicMock()
    pub1.publish.return_value = True
    pub2 = MagicMock()
    pub2.publish.return_value = True

    composite = CompositePublisher([pub1, pub2])
    event = intrusion_event("evt-1")
    assert composite.publish(event) is True

    pub1.publish.assert_called_once_with(event)
    pub2.publish.assert_called_once_with(event)


def test_composite_publisher_returns_false_if_any_publish_fails():
    pub1 = MagicMock()
    pub1.publish.return_value = True
    pub2 = MagicMock()
    pub2.publish.return_value = False

    composite = CompositePublisher([pub1, pub2])
    event = intrusion_event("evt-1")
    assert composite.publish(event) is False


def test_composite_publisher_fans_out_telemetry():
    pub1 = MagicMock()
    pub1.publish_telemetry.return_value = True
    pub2 = MagicMock(spec=[])  # doesn't have publish_telemetry
    pub3 = MagicMock()
    pub3.publish_telemetry.return_value = True

    composite = CompositePublisher([pub1, pub2, pub3])
    telemetry = {"cameraId": "cam_01", "tracks": []}
    assert composite.publish_telemetry(telemetry) is True

    pub1.publish_telemetry.assert_called_once_with(telemetry)
    pub3.publish_telemetry.assert_called_once_with(telemetry)


def test_composite_publisher_returns_false_if_any_telemetry_fails():
    pub1 = MagicMock()
    pub1.publish_telemetry.return_value = True
    pub2 = MagicMock()
    pub2.publish_telemetry.return_value = False

    composite = CompositePublisher([pub1, pub2])
    telemetry = {"cameraId": "cam_01", "tracks": []}
    assert composite.publish_telemetry(telemetry) is False
