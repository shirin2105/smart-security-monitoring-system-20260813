"""Deterministic Phase 11 ground-truth extractor from CAVIAR trajectory XML.

The phase8 clips carry CAVIAR per-frame trajectory labels (object box + role +
context). This module converts them into event-level ground truth for the three
Phase 11 event types using documented, deterministic heuristics. GT is
provisional (not visually verified) and marked as such in the freeze/report.

Heuristics (all thresholds are heuristic, documented in this docstring):
- ZONE_INTRUSION: an object's center first enters a central ROI (normalized
  polygon default [0.30,0.40],[0.70,0.40],[0.70,0.90],[0.30,0.90]).
- CROWD_THRESHOLD: >= ``crowd_threshold`` people present simultaneously for at
  least ``crowd_hold_s``.
- ABANDONED_OBJECT: an object whose role is "leaving object" stays within
  ``stationary_radius_px`` of its mean center for at least ``stationary_hold_s``.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.evaluation.phase11_schema import GroundTruthEvent, VALID_EVENT_TYPES

FRAME_FPS = 25.0
DEFAULT_INTRUSION_ROI = [[0.30, 0.40], [0.70, 0.40], [0.70, 0.90], [0.30, 0.90]]


@dataclass
class ObjectSample:
    object_id: int
    frame: int
    time_s: float
    xc: float
    yc: float
    role: str | None
    context: str | None
    appearance: str | None


def _parse_clip(path: str | Path) -> tuple[int, int, list[ObjectSample]]:
    """Parse XML into (frame_count, max_objects, samples)."""
    root = ET.parse(path).getroot()
    frames = root.findall("frame")
    samples: list[ObjectSample] = []
    max_objects = 0
    frame_count = 0
    for frame in frames:
        number = int(frame.get("number", frame_count))
        frame_count = max(frame_count, number + 1)
        objects = frame.findall("objectlist/object")
        max_objects = max(max_objects, len(objects))
        for obj in objects:
            obj_id = int(obj.get("id", 0))
            box = obj.find("box")
            if box is None:
                continue
            xc = float(box.get("xc"))
            yc = float(box.get("yc"))
            appearance = None
            node = obj.find("appearance")
            if node is not None and node.text:
                appearance = node.text
            role = context = None
            for hypothesis in obj.findall("hypothesislist/hypothesis"):
                role_node = hypothesis.find("role")
                context_node = hypothesis.find("context")
                if role_node is not None and role_node.text:
                    role = role_node.text
                if context_node is not None and context_node.text:
                    context = context_node.text
                if role and context:
                    break
            samples.append(
                ObjectSample(
                    object_id=obj_id,
                    frame=number,
                    time_s=number / FRAME_FPS,
                    xc=xc,
                    yc=yc,
                    role=role,
                    context=context,
                    appearance=appearance,
                )
            )
    return frame_count, max_objects, samples


def _point_in_polygon(x: float, y: float, polygon: list[list[float]]) -> bool:
    inside = False
    n = len(polygon)
    j = n - 1
    for i in range(n):
        xi, yi = polygon[i]
        xj, yj = polygon[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            inside = not inside
        j = i
    return inside


def _norm_roi_to_abs(roi: list[list[float]], width: int, height: int) -> list[list[float]]:
    return [[x * width, y * height] for x, y in roi]


def _intrusion_events(
    samples: list[ObjectSample],
    width: int,
    height: int,
    roi: list[list[float]],
) -> list[tuple[int, float]]:
    """Return (seq, trigger_time_s) for each person entering the ROI.

    Uses the CAVIAR per-object ID as track identity. A track emits exactly one
    intrusion when its center transitions from outside to inside the ROI.
    """
    abs_roi = _norm_roi_to_abs(roi, width, height)
    tracks: dict[int, list[ObjectSample]] = {}
    for sample in samples:
        tracks.setdefault(sample.object_id, []).append(sample)

    events: list[tuple[int, float]] = []
    seq = 0
    for trace in tracks.values():
        # Only people trigger intrusion; ignore inanimate objects (e.g. a bag).
        if _dominant_role(trace) in {"leaving object", "none", None}:
            continue
        entered = False
        for sample in sorted(trace, key=lambda s: s.frame):
            inside = _point_in_polygon(sample.xc, sample.yc, abs_roi)
            if inside and not entered:
                entered = True
                seq += 1
                events.append((seq, sample.time_s))
    return events


def _dominant_role(trace: list[ObjectSample]) -> str | None:
    roles = {}
    for sample in trace:
        if sample.role:
            roles[sample.role] = roles.get(sample.role, 0) + 1
    return max(roles, key=roles.get) if roles else None


def _crowd_events(
    samples: list[ObjectSample],
    threshold: int,
    hold_s: float,
    width: int,
    height: int,
    roi: list[list[float]],
) -> list[tuple[int, float]]:
    """Return (seq, trigger_time_s) for crowd windows of >= threshold people.

    Counts only people (not inanimate objects) whose center is inside the ROI,
    matching the runtime's central-ROI crowd semantic. ``hold_s`` is the frozen
    runtime hold policy; the trigger is the frame where the sustained count
    window begins.
    """
    abs_roi = _norm_roi_to_abs(roi, width, height)
    count_by_frame: dict[int, int] = {}
    for sample in samples:
        if sample.role == "leaving object" or sample.role is None:
            continue
        if not _point_in_polygon(sample.xc, sample.yc, abs_roi):
            continue
        count_by_frame[sample.frame] = count_by_frame.get(sample.frame, 0) + 1
    if not count_by_frame:
        return []
    # Iterate the contiguous frame range so a frame with zero people inside the
    # ROI (a full crowd departure) resets the hold window instead of being
    # silently bridged over.
    min_frame, max_frame = min(count_by_frame), max(count_by_frame)
    events: list[tuple[int, float, float]] = []
    seq = 0
    window_start: int | None = None
    min_hold_frames = int(hold_s * FRAME_FPS)
    for frame in range(min_frame, max_frame + 1):
        count = count_by_frame.get(frame, 0)
        if count >= threshold:
            if window_start is None:
                window_start = frame
            if (frame - window_start) >= min_hold_frames:
                seq += 1
                events.append((seq, (window_start + min_hold_frames) / FRAME_FPS, window_start / FRAME_FPS))
                window_start = None
        else:
            if window_start is not None and (frame - window_start) >= min_hold_frames:
                seq += 1
                events.append((seq, (window_start + min_hold_frames) / FRAME_FPS, window_start / FRAME_FPS))
            window_start = None
    return events


def _abandoned_events(samples: list[ObjectSample], stationary_hold_s: float, radius_px: float) -> list[tuple[int, float]]:
    """Return (seq, trigger_time_s) for each 'leaving object' that stays stationary."""
    leaving: dict[int, list[ObjectSample]] = {}
    for sample in samples:
        if sample.role == "leaving object":
            leaving.setdefault(sample.object_id, []).append(sample)
    events: list[tuple[int, float]] = []
    seq = 0
    min_hold_frames = int(stationary_hold_s * FRAME_FPS)
    for trace in leaving.values():
        trace = sorted(trace, key=lambda s: s.frame)
        if len(trace) < min_hold_frames:
            continue
        mean_x = sum(s.xc for s in trace) / len(trace)
        mean_y = sum(s.yc for s in trace) / len(trace)
        stationary_frames = [
            s.frame
            for s in trace
            if abs(s.xc - mean_x) <= radius_px and abs(s.yc - mean_y) <= radius_px
        ]
        if not stationary_frames:
            continue
        run = 0
        trigger = stationary_frames[0]
        for index, frame in enumerate(stationary_frames):
            run = run + 1 if index == 0 or frame == stationary_frames[index - 1] + 1 else 1
            if run == 1:
                trigger = frame
            if run >= min_hold_frames:
                seq += 1
                events.append((seq, trigger / FRAME_FPS))
                break
    return events


class GroundTruthExtractor:
    """Derive event-level GT from one CAVIAR clip's trajectory XML."""

    def __init__(
        self,
        frame_width: int = 384,
        frame_height: int = 288,
        intrusion_roi: list[list[float]] | None = None,
        intrusion_zone_id: str = "CENTRAL_ROI",
        crowd_threshold: int = 3,
        crowd_hold_s: float = 1.0,
        stationary_hold_s: float = 3.0,
        stationary_radius_px: float = 8.0,
    ) -> None:
        self.width = frame_width
        self.height = frame_height
        self.intrusion_roi = intrusion_roi or DEFAULT_INTRUSION_ROI
        self.intrusion_zone_id = intrusion_zone_id
        self.crowd_threshold = crowd_threshold
        self.crowd_hold_s = crowd_hold_s
        self.stationary_hold_s = stationary_hold_s
        self.stationary_radius_px = stationary_radius_px
        self.crowd_roi = self.intrusion_roi

    def extract(self, clip_id: str, camera_id: str, xml_path: str | Path) -> list[GroundTruthEvent]:
        frame_count, _, samples = _parse_clip(xml_path)
        events: list[GroundTruthEvent] = []
        seq = 0

        for seq, trigger in _intrusion_events(samples, self.width, self.height, self.intrusion_roi):
            events.append(
                GroundTruthEvent(
                    clip_id=clip_id, camera_id=camera_id,
                    event_id=f"GT-{clip_id}-ZONE_INTRUSION-{seq}",
                    event_type="ZONE_INTRUSION", start_s=max(0.0, trigger - 1.0),
                    trigger_time_s=trigger, end_s=min(frame_count / FRAME_FPS, trigger + 3.0),
                    zone_id=self.intrusion_zone_id,
                    notes="heuristic: person enters central ROI",
                )
            )

        for seq, trigger, window_start_s in _crowd_events(samples, self.crowd_threshold, self.crowd_hold_s,
                                          self.width, self.height, self.crowd_roi):
            events.append(
                GroundTruthEvent(
                    clip_id=clip_id, camera_id=camera_id,
                    event_id=f"GT-{clip_id}-CROWD_THRESHOLD-{seq}",
                    event_type="CROWD_THRESHOLD", start_s=max(0.0, window_start_s),
                    trigger_time_s=trigger, end_s=min(frame_count / FRAME_FPS, trigger + 5.0),
                    zone_id="CENTRAL_ROI",
                    notes=f"heuristic: >= {self.crowd_threshold} people inside central ROI held {self.crowd_hold_s}s",
                )
            )

        for seq, trigger in _abandoned_events(samples, self.stationary_hold_s, self.stationary_radius_px):
            events.append(
                GroundTruthEvent(
                    clip_id=clip_id, camera_id=camera_id,
                    event_id=f"GT-{clip_id}-ABANDONED_OBJECT-{seq}",
                    event_type="ABANDONED_OBJECT", start_s=max(0.0, trigger - 2.0),
                    trigger_time_s=trigger, end_s=min(frame_count / FRAME_FPS, trigger + 8.0),
                    zone_id=None,
                    notes="heuristic: leaving object stays stationary",
                )
            )
        return events
