"""Phase 11A hardened crowd GT extraction tests."""

from __future__ import annotations

from app.evaluation.phase11_gt_extractor import (
    GroundTruthExtractor,
    _crowd_events,
    ObjectSample,
)


def _s(object_id, frame, xc=200.0, yc=140.0, role="walker"):
    return ObjectSample(object_id=object_id, frame=frame, time_s=frame / 25.0,
                        xc=xc, yc=yc, role=role, context="walking", appearance="visible")


def test_crowd_trigger_is_window_start_plus_hold():
    # 3 people inside ROI from frame 100 onward (384x288, hold 4s = 100 frames).
    samples = [_s(i, f) for i in range(3) for f in range(100, 300)]
    events = _crowd_events(samples, threshold=3, hold_s=4.0, width=384, height=288,
                           roi=[[0.3, 0.4], [0.7, 0.4], [0.7, 0.9], [0.3, 0.9]])
    assert len(events) == 1
    seq, trigger, window_start = events[0]
    assert window_start == 100 / 25.0 == 4.0
    assert trigger == (100 + 100) / 25.0 == 8.0  # start + 4s hold


def test_crowd_counts_only_people_inside_roi():
    # 2 people inside ROI (200,140) but 1 outside (xc=40 -> outside ROI x range).
    inside = [_s(i, f, xc=200.0) for i in range(2) for f in range(100, 300)]
    outside = [_s(9, f, xc=40.0) for f in range(100, 300)]
    events = _crowd_events(inside + outside, threshold=3, hold_s=4.0, width=384, height=288,
                           roi=[[0.3, 0.4], [0.7, 0.4], [0.7, 0.9], [0.3, 0.9]])
    assert len(events) == 0  # only 2 inside, below threshold 3


def test_crowd_excludes_inanimate_leaving_object():
    samples = [_s(i, f, xc=200.0, role="leaving object") for i in range(3) for f in range(100, 300)]
    events = _crowd_events(samples, threshold=3, hold_s=4.0, width=384, height=288,
                           roi=[[0.3, 0.4], [0.7, 0.4], [0.7, 0.9], [0.3, 0.9]])
    assert len(events) == 0  # leaving objects are not people


def test_crowd_departure_resets_hold_window():
    # People present frames 100-199, gone 200-299 (full departure), back 300-459.
    samples = [_s(i, f) for i in range(3) for f in range(100, 200)]
    samples += [_s(i, f) for i in range(3) for f in range(300, 460)]
    events = _crowd_events(samples, threshold=3, hold_s=4.0, width=384, height=288,
                           roi=[[0.3, 0.4], [0.7, 0.4], [0.7, 0.9], [0.3, 0.9]])
    # Two distinct 4s windows (100 and 300), each triggers after a 100-frame hold.
    assert len(events) == 2
    _, t1, w1 = events[0]
    _, t2, w2 = events[1]
    assert w1 == 100 / 25.0 and w2 == 300 / 25.0


def test_crowd_below_threshold_no_event():
    samples = [_s(i, f) for i in range(2) for f in range(100, 300)]
    events = _crowd_events(samples, threshold=3, hold_s=4.0, width=384, height=288,
                           roi=[[0.3, 0.4], [0.7, 0.4], [0.7, 0.9], [0.3, 0.9]])
    assert events == []


def test_extractor_crowd_gt_hardened():
    ex = GroundTruthExtractor(crowd_threshold=3, crowd_hold_s=4.0)
    assert ex.crowd_hold_s == 4.0
    assert ex.crowd_threshold == 3
    assert ex.crowd_roi == ex.intrusion_roi
