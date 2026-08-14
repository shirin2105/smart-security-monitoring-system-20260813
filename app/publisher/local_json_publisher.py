import json
import os

from app.common.schemas import EventCandidate
from app.publisher.base import EventPublisher


class LocalJsonEventPublisher(EventPublisher):
    def __init__(self, output_dir: str = "artifacts/events"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def publish(self, candidate: EventCandidate) -> bool:
        file_path = os.path.join(self.output_dir, f"candidate_{candidate.candidateId}.json")
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(candidate.model_dump(mode="json"), f, indent=2, ensure_ascii=False)
            print(f"[EventPublisher] Emitted EventCandidate to {file_path}")
            return True
        except Exception as e:
            print(f"[EventPublisher] Failed to emit candidate JSON: {e}")
            return False
