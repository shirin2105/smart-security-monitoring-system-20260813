from phase7b_core import CLASS_NAMES, ID_NAMESPACE, TrackHistory, TrackObservation

def make_obs(frame, ts, cid, local_id, conf=0.8):
    return TrackObservation(
        frame_index=frame, timestamp_s=ts, class_id=cid, class_name=CLASS_NAMES[cid],
        global_track_id=(cid+1)*ID_NAMESPACE+local_id, local_track_id=local_id,
        bbox_xyxy=(10.0+frame,20.0,30.0+frame,50.0), confidence=conf
    )

def test_global_id_namespace():
    ids=set()
    for cid in CLASS_NAMES:
        for local in (0,1,99):
            gid=(cid+1)*ID_NAMESPACE+local
            assert gid not in ids
            ids.add(gid)

def test_track_history_duration():
    h=TrackHistory()
    h.update([make_obs(0,0.0,0,7)])
    h.update([make_obs(10,1.0,0,7)])
    s=h.summary()
    assert s["total_tracks"]==1
    assert abs(s["by_class"]["person"]["max_duration_s"]-1.0)<1e-9
    assert s["by_class"]["person"]["mean_observations"]==2.0

def test_class_separation():
    h=TrackHistory()
    h.update([make_obs(0,0.0,cid,1) for cid in CLASS_NAMES])
    s=h.summary()
    assert s["total_tracks"]==4
    for name in CLASS_NAMES.values():
        assert s["by_class"][name]["tracks"]==1

if __name__=="__main__":
    test_global_id_namespace()
    test_track_history_duration()
    test_class_separation()
    print("PHASE7B CORE TESTS: PASS")
