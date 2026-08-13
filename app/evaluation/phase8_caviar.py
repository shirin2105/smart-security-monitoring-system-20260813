from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path


FPS_FALLBACK = 25.0
ROI = [[96, 58], [288, 58], [288, 270], [96, 270]]
NEGATIVE_ROI = [[330, 5], [380, 5], [380, 50], [330, 50]]
PERSON_ROLES = {"walker", "walkers", "browser", "browsers", "meeter", "meeters"}


@dataclass(frozen=True)
class Observation:
    frame: int
    object_id: str
    foot_x: float
    foot_y: float
    role: str


def parse_observations(xml_path: Path) -> tuple[list[Observation], int]:
    root = ET.parse(xml_path).getroot()
    observations: list[Observation] = []
    last_frame = 0
    for frame_node in root.findall("frame"):
        frame = int(frame_node.attrib["number"])
        last_frame = max(last_frame, frame)
        for obj in frame_node.findall("./objectlist/object"):
            box = obj.find("box")
            if box is None:
                continue
            role_node = obj.find("./hypothesislist/hypothesis/role")
            role = (role_node.text or "").strip().lower() if role_node is not None else ""
            observations.append(Observation(
                frame=frame,
                object_id=obj.attrib["id"],
                foot_x=float(box.attrib["xc"]),
                foot_y=float(box.attrib["yc"]) + float(box.attrib["h"]) / 2,
                role=role,
            ))
    return observations, last_frame + 1


def _inside(observation: Observation, roi: list[list[int]]) -> bool:
    xs = [point[0] for point in roi]
    ys = [point[1] for point in roi]
    return min(xs) <= observation.foot_x <= max(xs) and min(ys) <= observation.foot_y <= max(ys)


def _runs(frames: list[int], max_gap: int = 1) -> list[tuple[int, int]]:
    if not frames:
        return []
    ordered = sorted(set(frames))
    runs: list[tuple[int, int]] = []
    start = previous = ordered[0]
    for frame in ordered[1:]:
        if frame - previous > max_gap:
            runs.append((start, previous))
            start = frame
        previous = frame
    runs.append((start, previous))
    return runs


def derive_events(clip_id: str, camera_id: str, observations: list[Observation],
                  fps: float, intrusion_roi: list[list[int]],
                  crowd_roi: list[list[int]]) -> list[dict]:
    events: list[dict] = []
    by_person: dict[str, list[int]] = {}
    leaving_frames: dict[str, list[int]] = {}
    people_per_frame: dict[int, set[str]] = {}
    for obs in observations:
        if obs.role == "leaving object":
            leaving_frames.setdefault(obs.object_id, []).append(obs.frame)
        if obs.role in PERSON_ROLES:
            if _inside(obs, intrusion_roi):
                by_person.setdefault(obs.object_id, []).append(obs.frame)
            if _inside(obs, crowd_roi):
                people_per_frame.setdefault(obs.frame, set()).add(obs.object_id)

    hold_frames = max(1, round(fps))
    for object_id, frames in sorted(by_person.items()):
        for index, (start, end) in enumerate(_runs(frames)):
            if end - start + 1 < hold_frames:
                continue
            events.append(_event(clip_id, camera_id, f"GT_INTR_{object_id}_{index}",
                                 "ZONE_INTRUSION", start, start + hold_frames - 1,
                                 end, fps, "ROI_MAIN", "CAVIAR person foot-point in project ROI."))

    crowd_frames = [frame for frame, ids in people_per_frame.items() if len(ids) >= 2]
    for index, (start, end) in enumerate(_runs(crowd_frames)):
        if end - start + 1 < hold_frames:
            continue
        events.append(_event(clip_id, camera_id, f"GT_CROWD_{index}",
                             "CROWD_THRESHOLD", start, start + hold_frames - 1,
                             end, fps, "ROI_MAIN", "At least two annotated people in project ROI."))

    owner_away_frames = max(1, round(5 * fps))
    for object_id, frames in sorted(leaving_frames.items()):
        for index, (start, end) in enumerate(_runs(frames)):
            trigger = min(end, start + owner_away_frames)
            events.append(_event(clip_id, camera_id, f"GT_AO_{object_id}_{index}",
                                 "ABANDONED_OBJECT", start, trigger, end, fps,
                                 "FLOOR_MAIN", "CAVIAR role='leaving object'; 5 s candidate dwell."))
    if clip_id == "LeftBag_BehindChair" and not leaving_frames:
        events.append(_event(clip_id, camera_id, "GT_AO_MANUAL_0",
                             "ABANDONED_OBJECT", 450, 575, 1066, fps,
                             "FLOOR_MAIN",
                             "Manual video review: bag occluded behind chair; XML has no bag object."))
    return events


def _event(clip_id: str, camera_id: str, event_id: str, event_type: str,
           start: int, trigger: int, end: int, fps: float, zone_id: str,
           notes: str) -> dict:
    return {
        "clip_id": clip_id,
        "camera_id": camera_id,
        "event_id": f"{clip_id}_{event_id}",
        "event_type": event_type,
        "start_s": round(start / fps, 6),
        "trigger_time_s": round(trigger / fps, 6),
        "end_s": round(end / fps, 6),
        "zone_id": zone_id,
        "notes": notes,
    }


def camera_config(camera_id: str, event_target: str) -> dict:
    intrusion_roi = ROI if event_target == "ZONE_INTRUSION" else NEGATIVE_ROI
    crowd_roi = ROI if event_target == "CROWD_THRESHOLD" else NEGATIVE_ROI
    return {
        "camera_id": camera_id,
        "inference_profile": "full640",
        "intrusion": {"enabled": True, "zone_id": "ROI_MAIN", "roi_polygon": intrusion_roi,
                      "hold_s": 1.0},
        "crowd": {"enabled": True, "zone_id": "ROI_MAIN", "roi_polygon": crowd_roi,
                  "threshold": 2, "hold_s": 1.0, "release_s": 1.0},
        "abandoned": {"enabled": True, "zone_id": "FLOOR_MAIN",
                      "valid_floor_roi_polygon": ROI, "stationary_hold_s": 3.0,
                      "owner_away_hold_s": 5.0},
    }
