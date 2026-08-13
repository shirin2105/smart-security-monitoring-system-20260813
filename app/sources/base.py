from abc import ABC, abstractmethod
from typing import Generator, Optional
from app.common.schemas import FrameData


class BaseVideoSource(ABC):
    @abstractmethod
    def read_frames(self) -> Generator[FrameData, None, None]:
        """Yield frames sequentially as FrameData objects."""
        pass

    @abstractmethod
    def release(self) -> None:
        """Release underlying video capture resource."""
        pass
