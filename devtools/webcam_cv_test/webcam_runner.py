from __future__ import annotations

import threading
import time
import os
from pathlib import Path
from typing import Any

import cv2

from model_runtime import SharedCvRuntime
from webcam_event_adapter import RealtimeEventAdapter


class WebcamRunner:
    def __init__(self, config: dict[str, Any], tool_root: Path, repo_root: Path):
        self.config = config
        self.tool_root = tool_root
        self.repo_root = repo_root
        self.lock = threading.Lock()
        self.stop_signal = threading.Event()
        self.thread: threading.Thread | None = None
        self.capture = None
        self.latest_jpeg: bytes | None = None
        self.runtime = None
        self.adapter = RealtimeEventAdapter(config, tool_root / "outputs/events.jsonl", repo_root)
        self.stats = {"running": False, "fps": 0.0, "persons": 0, "processed_frames": 0,
                      "detector_latency_ms": 0.0, "pipeline_latency_ms": 0.0,
                      "dropped_frames": 0, **self.adapter.status()}

    def start(self, camera_index: int | None = None) -> None:
        if self.thread and self.thread.is_alive():
            return
        self.stop_signal.clear()
        self.adapter = RealtimeEventAdapter(
            self.config, self.tool_root / "outputs/events.jsonl", self.repo_root)
        index = self.config["camera_index"] if camera_index is None else camera_index
        self.thread = threading.Thread(target=self._run, args=(index,), daemon=True)
        self.thread.start()

    def stop(self) -> None:
        self.stop_signal.set()
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=10)
        if self.capture is not None:
            self.capture.release()
        with self.lock:
            self.stats["running"] = False

    def _run(self, camera_index: int) -> None:
        backends = ([cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_ANY]
                    if os.name == "nt" else [cv2.CAP_ANY])
        for backend in backends:
            candidate = cv2.VideoCapture(camera_index, backend)
            if candidate.isOpened():
                self.capture = candidate
                break
            candidate.release()
        else:
            self.capture = cv2.VideoCapture()
        if not self.capture.isOpened():
            with self.lock:
                self.stats.update(running=False, error=f"Cannot open webcam index {camera_index}")
            return
        fps_hint = float(self.capture.get(cv2.CAP_PROP_FPS)) or 30.0
        try:
            self.runtime = SharedCvRuntime(self.repo_root, fps_hint)
            started = previous = time.monotonic()
            frame_index = 0
            with self.lock:
                self.stats.update(running=True, error=None)
            while not self.stop_signal.is_set():
                ok, frame = self.capture.read()
                if not ok:
                    with self.lock:
                        self.stats["dropped_frames"] += 1
                    time.sleep(0.05)
                    continue
                now = time.monotonic()
                timestamp_s = now - started
                rows, detector_ms, pipeline_ms = self.runtime.process(
                    frame, frame_index, timestamp_s)
                self.adapter.update(rows, timestamp_s, frame.shape[1])
                elapsed = max(now - previous, 1e-6)
                previous = now
                annotated = self._draw(frame, rows, 1.0 / elapsed,
                                       detector_ms, pipeline_ms)
                encoded, buffer = cv2.imencode(".jpg", annotated)
                if encoded:
                    with self.lock:
                        self.latest_jpeg = buffer.tobytes()
                        self.stats.update(running=True, fps=1.0 / elapsed,
                                          persons=sum(r["class_name"] == "person" and r["eligible"] for r in rows),
                                          processed_frames=frame_index + 1,
                                          detector_latency_ms=detector_ms,
                                          pipeline_latency_ms=pipeline_ms,
                                          **self.adapter.status())
                frame_index += 1
        except Exception as error:
            with self.lock:
                self.stats.update(running=False, error=repr(error))
        finally:
            self.capture.release()
            self.capture = None
            with self.lock:
                self.stats["running"] = False

    def _draw(self, frame, rows: list[dict], fps: float,
              detector_ms: float, pipeline_ms: float):
        output = frame.copy(); height, width = output.shape[:2]
        cv2.line(output, (width // 2, 0), (width // 2, height), (0, 0, 255), 2)
        cv2.putText(output, "INTRUSION ZONE", (width // 2 + 10, 28),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        for row in rows:
            x1, y1, x2, y2 = map(int, row["bbox_xyxy"])
            color = (0, 220, 0) if row["class_name"] == "person" else (0, 210, 255)
            cv2.rectangle(output, (x1, y1), (x2, y2), color, 2)
            display_id = (self.adapter.physical_id(row["global_track_id"])
                          if row["class_name"] == "luggage" else None)
            cv2.putText(output, f"{row['class_name']} {display_id or row['global_track_id']}",
                        (x1, max(16, y1 - 5)), cv2.FONT_HERSHEY_SIMPLEX, 0.42, color, 1)
        state = self.adapter.status()
        lines = [f"FPS {fps:.1f} | detector {detector_ms:.1f} ms | pipe {pipeline_ms:.1f} ms",
                 f"Persons {sum(r['class_name']=='person' and r['eligible'] for r in rows)}",
                 f"Crowd {'ACTIVE' if state['crowd_active'] else 'NORMAL'}",
                 f"Intrusion {state['intrusion_track_ids'] or 'NONE'}",
                 f"Abandoned {state['abandoned_candidate_ids'] or 'NONE'}"]
        for index, text in enumerate(lines):
            cv2.putText(output, text, (10, 25 + index * 22), cv2.FONT_HERSHEY_SIMPLEX,
                        0.52, (255, 255, 255), 2)
        return output

    def snapshot(self) -> dict:
        with self.lock:
            return dict(self.stats)

    def clear_events(self) -> None:
        self.adapter.clear_log()
