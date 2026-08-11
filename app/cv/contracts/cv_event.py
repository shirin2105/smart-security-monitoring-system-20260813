from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class CVEvent:
    schema_version: str
    event_id: str
    event_type: str
    event_state: str
    camera_id: str
    event_time: str
    event_time_s: float
    cv_confidence: float
    objects: dict[str, Any]
    evidence: dict[str, Any]
    spatial: dict[str, Any]
    media: dict[str, Any]
    diagnostics: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return deepcopy(asdict(self))

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, separators=(",", ":"))

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "CVEvent":
        from .validation import validate_event

        validate_event(payload)
        return cls(**deepcopy(payload))

    @classmethod
    def from_json(cls, payload: str) -> "CVEvent":
        decoded = json.loads(payload)
        if not isinstance(decoded, dict):
            raise ValueError("CVEvent JSON must decode to an object")
        return cls.from_dict(decoded)
