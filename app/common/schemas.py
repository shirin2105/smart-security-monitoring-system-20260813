from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.common.enums import EventType, RedactionStatus, SourceEngine


class DetectionResult(BaseModel):
    class_id: int
    class_name: str
    bbox: list[float]  # [x1, y1, x2, y2]
    confidence: float


class TrackResult(BaseModel):
    track_id: int
    class_name: str
    bbox: list[float]  # [x1, y1, x2, y2]
    confidence: float
    first_seen_at: str
    last_seen_at: str


class FrameData(BaseModel):
    camera_id: str
    frame_id: int
    captured_at: str
    source_type: str
    source_fps: float
    inference_fps: float
    image: Any | None = Field(default=None, exclude=True)  # Raw frame matrix in memory


class StaticRegionObservation(BaseModel):
    model_config = ConfigDict(frozen=True)
    region_id: str
    bbox: list[float]
    first_seen_at: str
    last_seen_at: str
    persistence_seconds: float
    confidence: float

class VLMValidationResult(BaseModel):
    model_config = ConfigDict(frozen=True)
    verdict: Literal["accepted", "rejected", "unavailable"]
    confidence: float = 0.0
    reason: str | None = None

class ObservationData(BaseModel):
    personCount: int = 0
    dwellSeconds: float | None = None
    insideZone: bool = False
    stationarySeconds: float | None = None
    ownerAbsentSeconds: float | None = None


class ArtifactData(BaseModel):
    available: bool = False
    contentType: str = "image/jpeg"
    redactionStatus: RedactionStatus = RedactionStatus.PENDING
    uri: str | None = None


class EventCandidate(BaseModel):
    candidateId: str
    sourceEngine: SourceEngine = SourceEngine.CV
    cameraId: str
    zoneId: str | None = None
    sourceType: str = "SIMULATED"

    eventType: EventType
    eventDetected: bool = True

    detectedAt: str
    firstSeenAt: str
    lastSeenAt: str

    confidence: float
    trackCount: int = 1
    trackIds: list[int] = Field(default_factory=list)

    observations: ObservationData
    modelVersion: str = "yolo-v11n"
    ruleVersion: str = "intrusion-rule-v1"
    policyVersion: int = 1

    artifact: ArtifactData = Field(default_factory=ArtifactData)
