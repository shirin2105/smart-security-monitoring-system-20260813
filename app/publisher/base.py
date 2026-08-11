from abc import ABC, abstractmethod
from app.common.schemas import EventCandidate


class EventPublisher(ABC):
    @abstractmethod
    def publish(self, candidate: EventCandidate) -> bool:
        """Publish an EventCandidate object. Returns True if successful."""
        pass
