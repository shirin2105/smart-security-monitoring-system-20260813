from pathlib import Path
import threading

from app.cv.contracts.cv_event import CVEvent
from app.cv.contracts.jsonl_io import append_event_jsonl
from app.publisher.base import CVEventPublisher


class JsonlPublisher(CVEventPublisher):
    """Append schema-valid CVEvent v1 records to one local JSONL file."""

    _locks_guard = threading.Lock()
    _locks: dict[Path, threading.Lock] = {}

    def __init__(self, output_path: str | Path = "artifacts/events/cv-events.jsonl"):
        self.output_path = Path(output_path).resolve()
        with self._locks_guard:
            self._lock = self._locks.setdefault(self.output_path, threading.Lock())

    def publish(self, event: CVEvent) -> bool:
        try:
            with self._lock:
                append_event_jsonl(self.output_path, event)
        except OSError:
            return False
        return True
