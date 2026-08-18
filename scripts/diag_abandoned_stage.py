"""Diagnostic: dump Phase7C per-stage reasons for one clip under Product Policy v2.

Patches infer_phase7c to capture the full result (summary, owner prechecks,
owner associations) so we can see the FIRST failing stage for a trusted clip.

    third_party\\deimv2\\.python311\\python.exe scripts/diag_abandoned_stage.py <clip>
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import kaggle_pipeline.phase7c_kernel.phase7c_core as core

_CAPTURE: dict = {}


def _patched(rows, cfg, fps_hint=30.0):
    result = core.infer_phase7c.__wrapped__(rows, cfg, fps_hint) if hasattr(core.infer_phase7c, "__wrapped__") else None
    return result


def main() -> int:
    clip = Path(sys.argv[1])
    from app.config import settings
    from app.cv.detector import DEIMv2Detector
    from app.cv.worker import CVWorker
    from scripts.phase11_infer import _phase7c_config

    captured = {}

    import app.cv.events.phase7c_abandoned_adapter as adapter_mod
    import kaggle_pipeline.phase7c_kernel.phase7c_core as c

    orig = c.infer_phase7c

    def patched(rows, cfg, fps_hint=30.0):
        r = orig(rows, cfg, fps_hint)
        captured["result"] = r
        return r

    # The adapter binds infer_phase7c at import time, so patch it there.
    adapter_mod.infer_phase7c = patched
    c.infer_phase7c = patched

    _ptracks = {}

    orig_assoc = c.associate_owner

    def patched_assoc(physical, stationary_run, person_tracks, quality_profiles, cfg, fps_hint=30.0):
        _ptracks["person_tracks"] = person_tracks
        _ptracks["quality"] = quality_profiles
        return orig_assoc(physical, stationary_run, person_tracks, quality_profiles, cfg, fps_hint)

    c.associate_owner = patched_assoc

    camera_config = {
        "camera_id": clip.stem,
        "source_type": "FILE",
        "source_uri": str(clip),
        "inference_fps": 5.0,
        "enabled": True,
        "continuity": {"reset_after_s": 5.0},
    }
    rules = {
        "intrusion": {"dwell_seconds": 2.0},
        "crowd": {"count_threshold": 3, "hold_seconds": 4.0, "release_threshold": 2},
        "abandoned_object": {"phase7c": _phase7c_config()},
    }
    publisher = type("P", (), {"publish": lambda self, e: True})()
    worker = CVWorker(
        camera_id=clip.stem,
        camera_config=camera_config,
        detector=DEIMv2Detector(**settings.detector_config),
        zones_config=[],
        rules_config=rules,
        publisher=publisher,
    )
    worker.run()

    r = captured.get("result")
    if not r:
        print("NO RESULT CAPTURED")
        return 1
    s = r["summary"]
    print("=== SUMMARY ===")
    print(json.dumps(s, indent=2))
    print("=== OWNER PRECHECKS (first 3) ===")
    for pc in r["owner_prechecks"][:3]:
        print(json.dumps(pc))
    print(f"total prechecks={len(r['owner_prechecks'])} associations={len(r['owner_associations'])}")
    print("=== OWNER ASSOCIATIONS (reasons) ===")
    for oa in r["owner_associations"]:
        print({
            "physical_id": oa.get("physical_id"),
            "person_track_id": oa.get("person_track_id"),
            "rejection_reason": oa.get("rejection_reason"),
            "selection_reason": oa.get("selection_reason"),
            "association_score": oa.get("association_score"),
            "owner_last_near_s": oa.get("owner_last_near_s"),
            "owner_last_visible_s": oa.get("owner_last_visible_s"),
            "near_ratio": oa.get("near_ratio"),
            "inside_ratio": oa.get("inside_ratio"),
        })
        print("--- ALL CANDIDATES (sorted by score) ---")
        for cand in sorted(oa.get("candidates", []), key=lambda c: c.get("association_score", 0.0), reverse=True):
            print({
                "person_track_id": cand.get("person_track_id"),
                "association_score": round(cand.get("association_score", 0.0), 4),
                "inside_ratio": round(cand.get("inside_ratio", 0.0), 4),
                "near_ratio": round(cand.get("near_ratio", 0.0), 4),
                "overlap_frames": cand.get("overlap_frames"),
                "overlap_s": round(cand.get("overlap_s", 0.0), 3),
                "min_distance_norm": cand.get("min_distance_norm"),
                "track_age_s": round(cand.get("track_age_s", 0.0), 2),
                "quality_pass": cand.get("quality_pass"),
                "first_seen_s": round(cand.get("first_seen_s"), 2) if cand.get("first_seen_s") is not None else None,
                "last_seen_s": round(cand.get("last_seen_s"), 2) if cand.get("last_seen_s") is not None else None,
                "track_frame_min": cand.get("track_frame_min"),
                "track_frame_max": cand.get("track_frame_max"),
                "stationary_near_ratio": round(cand.get("stationary_near_ratio", 0.0), 4),
                "stat_near": cand.get("stat_near"),
                "stat_total": cand.get("stat_total"),
            })
    print("=== PERSON TRACK CONFIDENCE ===")
    pt = _ptracks.get("person_tracks", {})
    qp = _ptracks.get("quality", {})
    for tid in sorted(pt.keys()):
        rows = pt[tid]
        confs = [float(r.get("confidence", 0.0)) for r in rows if r.get("confidence") is not None]
        prof = qp.get(tid)
        # Confident-visibility window (detections with conf >= 0.3) to see if a
        # real person is masked by a persistent low-confidence false positive.
        hi = [int(r["frame_index"]) for r in rows if float(r.get("confidence", 0.0)) >= 0.3]
        hi_win = f"{min(hi)}-{max(hi)} ({len(hi)} frames)" if hi else "none"
        print({
            "track_id": tid,
            "detections": len(rows),
            "mean_conf": round(sum(confs) / len(confs), 3) if confs else None,
            "min_conf": round(min(confs), 3) if confs else None,
            "max_conf": round(max(confs), 3) if confs else None,
            "quality_passed": bool(prof.passed) if prof is not None else None,
            "conf03_window_frames": hi_win,
        })
    print("=== PHYSICAL LUGGAGE stationary runs ===")
    for pl in r["physical_luggage"]:
        print({
            "physical_id": pl["physical_id"],
            "duration_s": round(pl["duration_s"], 2),
            "stationary_runs": [
                {"start_s": round(x["start_s"], 2), "end_s": round(x["end_s"], 2), "duration_s": round(x["duration_s"], 2)}
                for x in pl["stationary_runs"]
            ],
        })
    print("=== TIMELINE STATE COUNTS ===")
    from collections import Counter
    states = Counter(t["state"] for t in r["timeline"])
    print(json.dumps(dict(states), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
