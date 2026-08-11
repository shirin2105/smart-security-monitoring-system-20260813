from phase7c_core import (
    Phase7CConfig,
    QualityConfig,
    StitchConfig,
    StationaryConfig,
    OwnerConfig,
    quality_profile,
    stitch_luggage_tracks,
    build_quality_report,
    infer_phase7c,
)

def row(frame, t, cls, gid, cx, cy, conf, w=20, h=30):
    return {
        "frame_index": frame,
        "timestamp_s": t,
        "class_id": 0 if cls == "person" else 1,
        "class_name": cls,
        "global_track_id": gid,
        "local_track_id": gid % 1_000_000,
        "bbox_xyxy": [cx-w/2, cy-h/2, cx+w/2, cy+h/2],
        "center_xy": [cx, cy],
        "confidence": conf,
    }

def test_false_person_quality_rejected():
    rs = [row(i, i/10, "person", 1000001, 50, 50, 0.20) for i in range(50)]
    # only 2 accidental high hits
    rs[10]["confidence"] = 0.45
    rs[20]["confidence"] = 0.45
    q = quality_profile(rs, QualityConfig())
    assert not q.passed

def test_good_luggage_quality_passes():
    rs = [row(i, i/10, "luggage", 2000001, 50, 50, 0.70) for i in range(40)]
    q = quality_profile(rs, QualityConfig())
    assert q.passed

def test_stitch_two_luggage_segments():
    rows = []
    for i in range(20):
        rows.append(row(i, i/10, "luggage", 2000001, 100+i*0.5, 100, 0.7))
    for i in range(23, 50):
        rows.append(row(i, i/10, "luggage", 2000002, 112+(i-23)*0.1, 101, 0.75))
    q = build_quality_report(rows, QualityConfig())
    phys = stitch_luggage_tracks(rows, q, StitchConfig())
    assert len(phys) == 1
    assert phys[0].source_track_ids == [2000001, 2000002]

def test_end_to_end_abandoned_candidate():
    rows = []
    fps = 10

    # Owner carries bag for 5 seconds.
    for i in range(0, 50):
        t = i/fps
        px = 100 + i*1.0
        py = 150
        rows.append(row(i, t, "person", 1000001, px, py, 0.9, w=60, h=100))
        rows.append(row(i, t, "luggage", 2000001, px, py+20, 0.75, w=24, h=30))

    # New tracker ID for same physical bag after placement.
    # Owner moves away for ~2 seconds then disappears.
    for i in range(53, 75):
        t = i/fps
        px = 150 + (i-53)*8
        rows.append(row(i, t, "person", 1000001, px, 150, 0.9, w=60, h=100))
        rows.append(row(i, t, "luggage", 2000002, 150, 170, 0.8, w=28, h=34))

    # Bag remains stationary long enough after owner is gone.
    for i in range(75, 150):
        t = i/fps
        rows.append(row(i, t, "luggage", 2000002, 150, 170, 0.8, w=28, h=34))

    cfg = Phase7CConfig(
        stationary=StationaryConfig(
            window_s=1.0,
            min_samples=5,
            max_spread_norm=0.15,
            max_net_displacement_norm=0.20,
            hold_s=2.0,
        ),
        owner=OwnerConfig(
            near_norm=0.5,
            min_overlap_s=0.7,
            min_association_score=0.6,
            away_hold_s=3.0,
        ),
    )
    result = infer_phase7c(rows, cfg, fps_hint=fps)
    assert result["summary"]["physical_luggage_objects"] == 1
    assert result["summary"]["stitch_links"] == 1
    assert result["summary"]["abandoned_candidates"] == 1
    ev = result["events"][0]
    assert ev["owner_person_track_id"] == 1000001

if __name__ == "__main__":
    test_false_person_quality_rejected()
    test_good_luggage_quality_passes()
    test_stitch_two_luggage_segments()
    test_end_to_end_abandoned_candidate()
    print("PHASE7C CORE TESTS: PASS")
