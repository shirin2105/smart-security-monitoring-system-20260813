from types import SimpleNamespace

from app.common.schemas import FrameData
from app.cv.contracts.builders import build_intrusion_event
from app.cv.worker import CVWorker


def test_worker_shares_one_track_snapshot_across_all_adapters(monkeypatch):
    frame = FrameData(camera_id="cam", frame_id=1, captured_at="2026-01-01T00:00:00Z",
                      source_type="SIMULATED", source_fps=25, inference_fps=5)
    snapshots = []

    class Adapter:
        def evaluate(self, tracks, frame_data):
            snapshots.append(tracks)
            return []

    worker = CVWorker.__new__(CVWorker)
    worker.source = SimpleNamespace(read_frames=lambda: iter([frame]), release=lambda: None)
    worker.health_monitor = SimpleNamespace(update_frame_time=lambda value: None)
    worker.frame_sampler = SimpleNamespace(should_process=lambda value: True)
    worker.detector = SimpleNamespace(detect=lambda value: (["detection"], 1.0))
    worker.tracker = SimpleNamespace(track=lambda detections, value: ["track"])
    worker.track_store = SimpleNamespace(update_track=lambda track: "active-state")
    worker.adapters = (Adapter(), Adapter(), Adapter())
    worker.event_manager = SimpleNamespace(process=lambda signal: None)
    worker.publisher = SimpleNamespace(publish=lambda event: True)

    assert worker.run(max_frames=1) == []
    assert len(snapshots) == 3
    assert isinstance(snapshots[0], tuple)
    assert snapshots[0] is snapshots[1] is snapshots[2]


def test_worker_publishes_validated_cv_event(monkeypatch):
    event = build_intrusion_event(
        event_id="cam-ZONE_INTRUSION-000001", event_state="START", camera_id="cam",
        event_time="2026-01-01T00:00:00Z", event_time_s=1767225600.0,
        cv_confidence=0.9, persons=[{"track_id": 1, "bbox_xyxy": [0, 0, 10, 10]}],
        zone_id="zone-1", inside_duration_s=2.0,
    )
    published = []
    worker = CVWorker.__new__(CVWorker)
    worker.source = SimpleNamespace(
        read_frames=lambda: iter([FrameData(camera_id="cam", frame_id=1,
            captured_at="2026-01-01T00:00:00Z", source_type="SIMULATED",
            source_fps=25, inference_fps=5)]), release=lambda: None)
    worker.health_monitor = SimpleNamespace(update_frame_time=lambda value: None)
    worker.frame_sampler = SimpleNamespace(should_process=lambda value: True)
    worker.detector = SimpleNamespace(detect=lambda value: ([], 0.0))
    worker.tracker = SimpleNamespace(track=lambda detections, value: [])
    worker.track_store = SimpleNamespace(update_track=lambda track: track)
    worker.adapters = (SimpleNamespace(evaluate=lambda tracks, frame: ["signal"]),)
    worker.event_manager = SimpleNamespace(process=lambda signal: event)
    worker.event_id_namespace = lambda value: value
    worker.publisher = SimpleNamespace(publish=lambda value: published.append(value) or True)

    assert worker.run(max_frames=1) == [event]
    assert published == [event]
