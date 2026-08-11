from __future__ import annotations

import importlib.util
import json
import sys
import threading
from pathlib import Path
from typing import Any


class RealtimeEventAdapter:
    def __init__(self, config: dict[str, Any], event_log: Path, repo_root: Path):
        self.config = config
        self.lock = threading.RLock()
        self.event_log = event_log
        self.event_log.parent.mkdir(parents=True, exist_ok=True)
        self.intrusion_pending: dict[int, float] = {}
        self.intrusion_active: set[int] = set()
        self.crowd_pending: float | None = None
        self.crowd_recovery: float | None = None
        self.crowd_active = False
        self.track_rows: list[dict[str, Any]] = []
        self.abandoned_ids: set[str] = set()
        self.abandoned_signatures: set[tuple] = set()
        self.physical_by_track: dict[int, str] = {}
        self.last_phase7c_run_s = float("-inf")
        self.phase7c = self._load_phase7c(repo_root)

    @staticmethod
    def _load_phase7c(repo_root: Path):
        path = repo_root / "kaggle_pipeline/phase7c_kernel/phase7c_core.py"
        spec = importlib.util.spec_from_file_location("webcam_phase7c_core", path)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"Cannot load Phase7C core: {path}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module

    def update(self, tracks: list[dict[str, Any]], now_s: float, frame_width: int) -> list[dict]:
        with self.lock:
            transitions = []
            persons = [row for row in tracks if row["class_name"] == "person" and row["eligible"]]
            transitions.extend(self._update_intrusion(persons, now_s, frame_width))
            transitions.extend(self._update_crowd(len(persons), now_s))
            self.track_rows.extend(row for row in tracks if row["eligible"])
            transitions.extend(self._update_abandoned(now_s))
            for event in transitions:
                self._append(event)
            return transitions

    def _update_intrusion(self, persons: list[dict], now_s: float, width: int) -> list[dict]:
        cfg = self.config["intrusion"]
        if not cfg.get("enabled", True):
            return []
        inside = set()
        for row in persons:
            track_id = int(row["global_track_id"])
            x1, _, x2, _ = map(float, row["bbox_xyxy"])
            if (x1 + x2) / 2.0 >= width / 2.0:
                inside.add(track_id)
                self.intrusion_pending.setdefault(track_id, now_s)
        output = []
        hold_s = float(cfg["hold_s"])
        for track_id in inside:
            if track_id not in self.intrusion_active and now_s - self.intrusion_pending[track_id] >= hold_s:
                self.intrusion_active.add(track_id)
                output.append(self._event("ZONE_INTRUSION", "ACTIVE", now_s, track_id=track_id))
        for track_id in list(self.intrusion_pending):
            if track_id in inside:
                continue
            self.intrusion_pending.pop(track_id, None)
            if track_id in self.intrusion_active:
                self.intrusion_active.remove(track_id)
                output.append(self._event("ZONE_INTRUSION", "CLEARED", now_s, track_id=track_id))
        return output

    def _update_crowd(self, person_count: int, now_s: float) -> list[dict]:
        cfg = self.config["crowd"]
        if not cfg.get("enabled", True):
            return []
        output = []
        if person_count >= int(cfg["threshold"]):
            self.crowd_recovery = None
            self.crowd_pending = self.crowd_pending if self.crowd_pending is not None else now_s
            if not self.crowd_active and now_s - self.crowd_pending >= float(cfg["hold_s"]):
                self.crowd_active = True
                output.append(self._event("CROWD_THRESHOLD", "ACTIVE", now_s,
                                          person_count=person_count))
        else:
            self.crowd_pending = None
            self.crowd_recovery = self.crowd_recovery if self.crowd_recovery is not None else now_s
            if self.crowd_active and now_s - self.crowd_recovery >= float(cfg["recovery_s"]):
                self.crowd_active = False
                output.append(self._event("CROWD_THRESHOLD", "CLEARED", now_s,
                                          person_count=person_count))
        return output

    def _update_abandoned(self, now_s: float) -> list[dict]:
        cfg = self.config["abandoned"]
        if (not cfg.get("enabled", True) or not self.track_rows
                or now_s - self.last_phase7c_run_s < 0.5):
            return []
        self.last_phase7c_run_s = now_s
        cutoff = now_s - 120.0
        self.track_rows = [row for row in self.track_rows if float(row["timestamp_s"]) >= cutoff]
        phase_cfg = self.phase7c.Phase7CConfig(
            stationary=self.phase7c.StationaryConfig(hold_s=float(cfg["stationary_hold_s"])),
            owner=self.phase7c.OwnerConfig(away_hold_s=float(cfg["owner_away_hold_s"])),
        )
        result = self.phase7c.infer_phase7c(self.track_rows, phase_cfg)
        self.physical_by_track = {
            int(track_id): str(physical["physical_id"])
            for physical in result.get("physical_luggage", [])
            for track_id in physical["source_track_ids"]
        }
        output = []
        for candidate in result["events"]:
            signature = (tuple(candidate.get("source_track_ids", [])),
                         round(float(candidate["candidate_time_s"]), 3))
            if signature in self.abandoned_signatures:
                continue
            self.abandoned_signatures.add(signature)
            event_id = f"AO_{'_'.join(map(str, signature[0]))}_{signature[1]:.3f}"
            self.abandoned_ids.add(event_id)
            output.append(self._event("ABANDONED_OBJECT_CANDIDATE", "ACTIVE", now_s,
                                      evidence=candidate))
        return output

    def _event(self, event_type: str, state: str, now_s: float, **extra) -> dict:
        return {"camera_id": self.config["camera_id"], "event_type": event_type,
                "state": state, "timestamp_s": float(now_s), **extra}

    def _append(self, event: dict) -> None:
        with self.event_log.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False) + "\n")

    def status(self) -> dict:
        with self.lock:
            return {"intrusion_track_ids": sorted(self.intrusion_active),
                    "crowd_active": self.crowd_active,
                    "abandoned_candidate_ids": sorted(self.abandoned_ids)}

    def physical_id(self, track_id: int) -> str | None:
        with self.lock:
            return self.physical_by_track.get(int(track_id))

    def clear_log(self) -> None:
        with self.lock:
            self.event_log.write_text("", encoding="utf-8")
