from abc import ABC, abstractmethod
from typing import List, Optional
from app.common.schemas import EventCandidate, FrameData
from app.cv.track_store import TrackState


class BaseEventEngine(ABC):
    @abstractmethod
    def evaluate(self, tracks: List[TrackState], frame_data: FrameData) -> List[EventCandidate]:
        """Evaluate active tracks and generate EventCandidates if rules trigger."""
        pass
