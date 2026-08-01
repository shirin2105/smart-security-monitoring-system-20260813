from enum import Enum


class EventType(str, Enum):
    ZONE_INTRUSION = "ZONE_INTRUSION"
    CROWD_THRESHOLD = "CROWD_THRESHOLD"
    ABANDONED_OBJECT = "ABANDONED_OBJECT"
    SUSPECTED_FALL = "SUSPECTED_FALL"
    COVERAGE_DEGRADED = "COVERAGE_DEGRADED"


class SourceEngine(str, Enum):
    CV = "CV"
    VLM = "VLM"


class RedactionStatus(str, Enum):
    PENDING = "PENDING"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"


class CameraStatus(str, Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    OFFLINE = "OFFLINE"


class IntrusionState(str, Enum):
    OUTSIDE = "OUTSIDE"
    ENTERING = "ENTERING"
    INSIDE_PENDING = "INSIDE_PENDING"
    INTRUSION_ACTIVE = "INTRUSION_ACTIVE"
    EXITED = "EXITED"
