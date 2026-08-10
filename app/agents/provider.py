from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field


ProviderSeverity = Literal["INFO", "WARNING", "HIGH", "CRITICAL"]


class ProviderDraft(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    recommended_severity: ProviderSeverity = Field(alias="recommendedSeverity")
    rationale: str = Field(min_length=1)


class ProviderResult(BaseModel):
    draft: ProviderDraft | None
    latency_ms: float
    model_name: str
    error: str | None = None


class AssessmentProvider(Protocol):
    async def assess(self, *, prompt: str, system_prompt: str) -> ProviderResult:
        raise NotImplementedError
