import threading

from app.cv.multi_camera_runner import MultiCameraRunner


def test_supervisor_shares_detector_and_isolates_camera_failures():
    detector = object()
    seen_detectors = []
    lock = threading.Lock()

    class Worker:
        def __init__(self, camera_id, source_uri, detector):
            self.camera_id = camera_id
            with lock:
                seen_detectors.append(detector)
        def run(self, max_frames=None):
            if self.camera_id == "bad":
                raise RuntimeError("camera disconnected")
            return [self.camera_id]

    configs = [{"camera_id": value, "source_uri": value, "enabled": True}
               for value in ("a", "b", "c", "d", "e", "bad", "seventh")]
    results = MultiCameraRunner(configs, detector=detector, worker_factory=Worker).run(max_frames=1)
    assert len(results) == 6
    assert results["bad"]["status"] == "failed"
    assert results["a"] == {"status": "completed", "events": ["a"]}
    assert len({id(item) for item in seen_detectors}) == 1
