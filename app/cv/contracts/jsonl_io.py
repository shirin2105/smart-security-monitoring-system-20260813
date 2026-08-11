from __future__ import annotations

from pathlib import Path

from .cv_event import CVEvent
from .validation import validate_event


def append_event_jsonl(path: str | Path, event: CVEvent) -> None:
    validate_event(event)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as output:
        output.write(event.to_json() + "\n")


def read_events_jsonl(path: str | Path) -> list[CVEvent]:
    events = []
    with Path(path).open(encoding="utf-8") as source:
        for line_number, line in enumerate(source, start=1):
            if not line.strip():
                continue
            try:
                events.append(CVEvent.from_json(line))
            except (TypeError, ValueError) as error:
                raise ValueError(f"Invalid CVEvent JSONL at line {line_number}: {error}") from error
    return events
