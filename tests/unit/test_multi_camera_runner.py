import threading
import time
from concurrent.futures import ThreadPoolExecutor

from app.cv.multi_camera_runner import LockedDetector, MultiCameraRunner


def test_locked_detector_serializes_real_concurrent_calls():
    state = {"in_flight": 0, "maximum": 0}
    state_lock = threading.Lock()
    start = threading.Barrier(5)

    class Detector:
        def detect(self, frame):
            with state_lock:
                state["in_flight"] += 1
                state["maximum"] = max(state["maximum"], state["in_flight"])
            time.sleep(0.02)
            with state_lock:
                state["in_flight"] -= 1
            return frame

    def call(frame):
        start.wait(timeout=2)
        return locked.detect(frame)

    locked = LockedDetector(Detector())
    with ThreadPoolExecutor(max_workers=5) as pool:
        results = list(pool.map(call, range(5)))
    assert results == list(range(5))
    assert state["maximum"] == 1


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
    assert all(item is not detector for item in seen_detectors)
    assert all(hasattr(item, "detect") for item in seen_detectors)
