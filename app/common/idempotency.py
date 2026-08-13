import os
import json
from typing import Set


class IdempotencyStore:
    """Stores processed candidate IDs to ensure idempotency across requests."""

    def __init__(self, storage_file: str = "artifacts/idempotency_store.json"):
        self.storage_file = storage_file
        self.processed_ids: Set[str] = set()
        self._load()

    def _load(self) -> None:
        if os.path.exists(self.storage_file):
            try:
                with open(self.storage_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.processed_ids = set(data.get("processed_ids", []))
            except Exception:
                self.processed_ids = set()

    def _save(self) -> None:
        os.makedirs(os.path.dirname(self.storage_file), exist_ok=True)
        try:
            with open(self.storage_file, "w", encoding="utf-8") as f:
                json.dump({"processed_ids": list(self.processed_ids)}, f, indent=2)
        except Exception:
            pass

    def is_processed(self, candidate_id: str) -> bool:
        return candidate_id in self.processed_ids

    def mark_processed(self, candidate_id: str) -> bool:
        if candidate_id in self.processed_ids:
            return False  # Already processed
        self.processed_ids.add(candidate_id)
        self._save()
        return True
