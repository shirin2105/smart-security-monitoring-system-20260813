import numpy as np

from app.cv.static_region_detector import StaticRegionDetector


def _frame(with_object=False):
    frame = np.zeros((100, 100, 3), dtype=np.uint8)
    if with_object:
        frame[40:60, 40:60] = 255
    return frame


def test_introduced_region_matures_but_baseline_and_transient_do_not():
    detector = StaticRegionDetector("cam", {"warmup_seconds": 1, "stationary_seconds": 2, "clear_grace_seconds": 1, "min_area_ratio": .005})
    assert detector.update(_frame(), "2026-08-01T00:00:00Z") == []
    assert detector.update(_frame(), "2026-08-01T00:00:01Z") == []
    assert detector.update(_frame(True), "2026-08-01T00:00:02Z") == []
    assert detector.update(_frame(), "2026-08-01T00:00:03Z") == []
    assert detector.update(_frame(True), "2026-08-01T00:00:04Z") == []
    observations = detector.update(_frame(True), "2026-08-01T00:00:06Z")
    assert len(observations) == 1
    assert observations[0].persistence_seconds == 2


def test_cleared_region_rearms_with_new_identity():
    detector = StaticRegionDetector("cam", {"warmup_seconds": 0, "stationary_seconds": 0, "clear_grace_seconds": 0})
    detector.update(_frame(), "2026-08-01T00:00:00Z")
    first = detector.update(_frame(True), "2026-08-01T00:00:01Z")[0]
    detector.update(_frame(), "2026-08-01T00:00:02Z")
    second = detector.update(_frame(True), "2026-08-01T00:00:03Z")[0]
    assert first.region_id != second.region_id
