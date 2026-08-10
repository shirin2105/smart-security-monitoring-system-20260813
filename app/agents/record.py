"""Assessment record: typed, legacy-compatible JSON record per candidate.

``AssessmentRecord`` owns the persistence format and its reload/evaluation
projection (C3). The on-disk shape stays byte-compatible with the legacy
record (``candidateId``/``eventType``/``assessment``/``telemetry``, camelCase
telemetry keys) so existing consumers can keep reading what the runner
writes. ``outputValid`` reflects whether the provider returned a
schema-valid result; a persist failure is reported as its own outcome and
never rewrites ``fallback_used``.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Iterator
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.agents.assessment import AgentAssessment, AssessmentOutcome
from app.common.schemas import EventCandidate

logger = logging.getLogger(__name__)
ENRICHMENT_PREFIX = "enrichment_"
ENRICHMENT_SUFFIX = ".json"


class RecordTelemetry(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    latency_ms: float = Field(alias="latencyMs")
    model_name: str = Field(alias="model")
    fallback_used: bool = Field(alias="fallbackUsed")
    provider_output_valid: bool = Field(alias="outputValid")
    provider_error: str | None = Field(default=None, alias="error")
    persist_error: str | None = Field(default=None, alias="persistError")


class AssessmentRecord(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    candidate_id: str = Field(alias="candidateId")
    event_type: str = Field(alias="eventType")
    assessment: AgentAssessment
    telemetry: RecordTelemetry

    @classmethod
    def from_outcome(
        cls, *, candidate: EventCandidate, outcome: AssessmentOutcome
    ) -> "AssessmentRecord":
        return cls(
            candidateId=candidate.candidateId,
            eventType=candidate.eventType.value,
            assessment=outcome.assessment,
            telemetry=RecordTelemetry(
                latencyMs=outcome.telemetry.latency_ms,
                model=outcome.telemetry.model_name,
                fallbackUsed=outcome.telemetry.fallback_used,
                outputValid=outcome.telemetry.provider_output_valid,
                error=outcome.telemetry.provider_error,
                persistError=None,
            ),
        )


class AssessmentRecordStore:
    """Persist and reload AssessmentRecord values on the local filesystem."""

    def __init__(self, output_dir: str | Path) -> None:
        self.output_dir = Path(output_dir)

    def save(self, record: AssessmentRecord) -> str | None:
        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            target = self.output_dir / (
                f"{ENRICHMENT_PREFIX}{record.candidate_id}{ENRICHMENT_SUFFIX}"
            )
            target.write_text(
                json.dumps(
                    record.model_dump(mode="json", by_alias=True),
                    indent=2,
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            return None
        except OSError as exc:
            return f"enrichment_persist_failed:{type(exc).__name__}"

    def load(self, candidate_id: str) -> AssessmentRecord | None:
        target = self.output_dir / (
            f"{ENRICHMENT_PREFIX}{candidate_id}{ENRICHMENT_SUFFIX}"
        )
        if not target.exists():
            return None
        return self._read(target)

    def iter_records(self) -> Iterator[AssessmentRecord]:
        if not self.output_dir.exists():
            return
        for path in sorted(
            self.output_dir.glob(f"{ENRICHMENT_PREFIX}*{ENRICHMENT_SUFFIX}")
        ):
            record = self._read(path)
            if record is not None:
                yield record

    def _read(self, path: Path) -> AssessmentRecord | None:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            return AssessmentRecord.model_validate(payload)
        except (OSError, json.JSONDecodeError, ValidationError) as exc:
            logger.warning(
                "assessment_record_invalid",
                extra={"record_path": str(path), "exception_class": type(exc).__name__},
            )
            return None
