from collections.abc import Sequence
from typing import Any

from app.cv.contracts.cv_event import CVEvent
from app.publisher.base import CVEventPublisher


class CompositePublisher(CVEventPublisher):
    def __init__(self, publishers: Sequence[Any]):
        self.publishers = tuple(publishers)

    def publish(self, event: CVEvent) -> bool:
        # Gửi qua tất cả publishers
        return all(p.publish(event) for p in self.publishers if hasattr(p, "publish"))

    def publish_telemetry(self, telemetry: dict) -> bool:
        # Gửi telemetry tới publisher có hỗ trợ (ví dụ HttpEventPublisher)
        success = True
        for p in self.publishers:
            if hasattr(p, "publish_telemetry"):
                if not p.publish_telemetry(telemetry):
                    success = False
        return success
