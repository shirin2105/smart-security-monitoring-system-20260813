"""PersistedIntake: canonical identity, dedupe, durable write, handoff.

Concentrates the persisted-candidate intake rules that used to live in the
API route (architecture review candidate 5): which ID is canonical, when a
write is a duplicate, where the candidate is durably stored, and what the
assessment handoff trigger is. Local JSON files are the MVP storage
stand-in; swapping to a database later must not change this interface.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.common.idempotency import IdempotencyStore
from app.common.schemas import EventCandidate

STORAGE_SUBDIR = "backend_events"


@dataclass
class IntakeOutcome:
    status: str
    candidate_id: str
    stored_uri: str | None = None
    error: str | None = None

    def as_response(self) -> dict[str, Any]:
        if self.status == "DUPLICATE_IGNORED":
            return {
                "status": self.status,
                "candidateId": self.candidate_id,
                "message": "Candidate already processed and persisted.",
            }
        if self.status == "ERROR":
            return {
                "status": self.status,
                "candidateId": self.candidate_id,
                "error": self.error,
            }
        return {
            "status": self.status,
            "candidateId": self.candidate_id,
            "stored_uri": self.stored_uri,
        }


class PersistedIntake:
    """Durable EventCandidate intake with idempotent writes."""

    def __init__(
        self,
        storage_dir: str = "artifacts/backend_events",
        idempotency_file: str | None = None,
    ):
        self.storage_dir = Path(storage_dir)
        if idempotency_file is None:
            idempotency_file = str(self.storage_dir / "idempotency.json")
        self.store = IdempotencyStore(storage_file=idempotency_file)

    def canonical_candidate(
        self,
        candidate: EventCandidate,
        header_id: str | None = None,
    ) -> EventCandidate:
        """Return a copy of the candidate carrying the canonical identity.

        ``header_id`` (Idempotency-Key) wins over the body ``candidateId``.
        Callers pass this copy to downstream seams (assessment handoff) so
        one identity drives persistence, dedupe, and enrichment.
        """
        canonical = header_id or candidate.candidateId
        if canonical == candidate.candidateId:
            return candidate
        return candidate.model_copy(update={"candidateId": canonical})

    def accept(
        self,
        candidate: EventCandidate,
        header_id: str | None = None,
    ) -> IntakeOutcome:
        """Persist a candidate exactly once.

        ``header_id`` (Idempotency-Key) wins over the body ``candidateId``;
        the canonical identity is the one used for both the file name and
        the dedupe store, so a single rule drives both.
        """
        candidate_id = header_id or candidate.candidateId

        if self.store.is_processed(candidate_id):
            return IntakeOutcome(
                status="DUPLICATE_IGNORED",
                candidate_id=candidate_id,
            )

        try:
            self.storage_dir.mkdir(parents=True, exist_ok=True)
            file_path = self.storage_dir / f"candidate_{candidate_id}.json"
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(candidate.model_dump(mode="json"), f, indent=2, ensure_ascii=False)
            self.store.mark_processed(candidate_id)
            return IntakeOutcome(
                status="ACCEPTED",
                candidate_id=candidate_id,
                stored_uri=f"/backend/events/candidate_{candidate_id}.json",
            )
        except OSError as exc:
            return IntakeOutcome(
                status="ERROR",
                candidate_id=candidate_id,
                error=f"persist_failed:{type(exc).__name__}",
            )
