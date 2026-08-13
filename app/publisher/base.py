from abc import ABC, abstractmethod
from app.common.schemas import EventCandidate


class EventPublisher(ABC):
    @abstractmethod
    def publish(self, candidate: EventCandidate) -> bool:
        """Publish an EventCandidate object. Returns True if successful."""
        pass

    def publish_telemetry(self, telemetry: dict) -> bool:
        """Publish real-time frame telemetry (bounding boxes). Returns True if successful."""
        return True

