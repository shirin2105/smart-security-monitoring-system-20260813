from abc import ABC, abstractmethod
from app.common.schemas import EventCandidate
from app.cv.contracts.cv_event import CVEvent


class EventPublisher(ABC):
    @abstractmethod
    def publish(self, event: EventCandidate) -> bool:
        """Publish a legacy backend EventCandidate."""
        pass


class CVEventPublisher(ABC):
    @abstractmethod
    def publish(self, event: CVEvent) -> bool:
        """Publish one schema-valid CVEvent v1 record."""
        pass
