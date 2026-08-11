import numpy as np
from phase7b1_runtime_core import (
    TrackObservation,
    CandidateManager,
    QualityConfig,
    BackgroundConfig,
    bbox_iou,
)

def obs(frame, ts, cls, gid, box=(10,10,30,30), conf=0.8):
    return TrackObservation(
        frame_index=frame,
        timestamp_s=ts,
        class_id=cls,
        class_name="person" if cls == 0 else "luggage",
        global_track_id=gid,
        local_track_id=gid % 1000000,
        bbox_xyxy=tuple(map(float, box)),
        confidence=conf,
    )

def test_iou():
    assert abs(bbox_iou((0,0,10,10),(0,0,10,10)) - 1.0) < 1e-9
    assert bbox_iou((0,0,10,10),(20,20,30,30)) == 0.0

def test_quality_gate():
    m = CandidateManager(
        quality=QualityConfig(
            luggage_min_age_s=1.0,
            luggage_min_hits=3,
            luggage_high_conf_threshold=0.35,
            luggage_min_high_hits=2,
        ),
        # This unit isolates the quality gate. Runtime eligibility is
        # intentionally blocked until startup warmup has finalized.
        background=BackgroundConfig(warmup_s=0.0),
    )
    gid=2000001
    rows=[]
    rows += m.process([obs(0,0.0,1,gid,conf=0.5)],0.0)
    rows += m.process([obs(15,0.5,1,gid,conf=0.5)],0.5)
    rows = m.process([obs(30,1.0,1,gid,conf=0.2)],1.0)
    assert rows[0]["eligible"] is True

def test_background_anchor():
    m = CandidateManager(
        quality=QualityConfig(),
        background=BackgroundConfig(
            warmup_s=4.0,
            max_first_seen_s=0.5,
            min_duration_s=3.0,
            min_hits=4,
            max_stationary_norm=0.25,
            suppress_iou=0.5,
        ),
    )
    gid=2000002
    for i,ts in enumerate([0.0,1.0,2.0,3.0,4.0]):
        rows=m.process([obs(i,ts,1,gid,box=(100,100,130,130),conf=0.6)],ts)
    assert m.warmup_finalized
    assert len(m.anchors) == 1
    assert rows[0]["is_background"] is True
    # new fragmented ID in same place must also be suppressed by spatial anchor
    rows2=m.process([obs(10,5.0,1,2000099,box=(101,101,131,131),conf=0.8)],5.0)
    assert rows2[0]["is_background"] is True

if __name__=="__main__":
    test_iou()
    test_quality_gate()
    test_background_anchor()
    print("PHASE7B.1 CORE TESTS: PASS")
