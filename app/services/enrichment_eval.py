"""AI evaluation tooling: aggregate enrichment telemetry into metrics.

Implements the SPEC §15 evaluation protocol for the agent layer: schema-valid
rate, fallback rate, severity distribution, and latency percentiles over the
persisted enrichment records.
"""

from __future__ import annotations

import json
import statistics
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ENRICHMENT_PREFIX = "enrichment_"
ENRICHMENT_SUFFIX = ".json"


@dataclass
class EvaluationRecord:
    """One enrichment result, loaded from a persisted record file.

    Fields use snake_case internally; camelCase JSON keys are mapped on load
    so the file contract stays unchanged.
    """

    candidate_id: str
    event_type: str
    fallback_used: bool
    output_valid: bool
    latency_ms: float
    model: str
    severity: str | None = None


@dataclass
class EvaluationReporter:
    enrichment_dir: str = "artifacts/backend_events"

    def load_records(self) -> list[EvaluationRecord]:
        records: list[EvaluationRecord] = []
        directory = Path(self.enrichment_dir)
        if not directory.exists():
            return records
        for path in sorted(directory.glob(f"{ENRICHMENT_PREFIX}*{ENRICHMENT_SUFFIX}")):
            record = self._parse_file(path)
            if record is not None:
                records.append(record)
        return records

    def _parse_file(self, path: Path) -> EvaluationRecord | None:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        telemetry = payload.get("telemetry", {})
        enrichment = payload.get("enrichment", {})
        return EvaluationRecord(
            candidate_id=str(payload.get("candidateId", path.stem)),
            event_type=str(payload.get("eventType", "")),
            fallback_used=bool(telemetry.get("fallbackUsed", False)),
            output_valid=bool(telemetry.get("outputValid", False)),
            latency_ms=float(telemetry.get("latencyMs", 0.0)),
            model=str(telemetry.get("model", "")),
            severity=enrichment.get("recommendedSeverity"),
        )

    def report(self) -> dict[str, Any]:
        return summarize_records(self.load_records())


def summarize_records(records: list[EvaluationRecord]) -> dict[str, Any]:
    """Aggregate records into machine-readable summary dicts (SPEC §15)."""
    total = len(records)
    if total == 0:
        return {
            "total": 0,
            "schema_valid_rate": None,
            "fallback_rate": None,
            "schema_invalid_but_no_fallback": 0,
            "severity_counts": {},
            "latency_ms": {"p50": None, "p95": None, "mean": None},
            "models": {},
        }

    schema_valid = sum(1 for r in records if r.output_valid)
    fallback_used = sum(1 for r in records if r.fallback_used)
    invalid_no_fallback = sum(1 for r in records if not r.output_valid and not r.fallback_used)

    severity_counts: dict[str, int] = {}
    for r in records:
        if r.severity is not None:
            severity_counts[r.severity] = severity_counts.get(r.severity, 0) + 1

    model_counts: dict[str, int] = {}
    for r in records:
        if r.model:
            model_counts[r.model] = model_counts.get(r.model, 0) + 1

    latencies = [r.latency_ms for r in records if r.latency_ms >= 0]
    latency_summary = _percentiles(latencies)

    return {
        "total": total,
        "schema_valid_rate": schema_valid / total,
        "fallback_rate": fallback_used / total,
        "schema_invalid_but_no_fallback": invalid_no_fallback,
        "severity_counts": severity_counts,
        "latency_ms": latency_summary,
        "models": model_counts,
    }


def _percentiles(latencies: list[float]) -> dict[str, float | None]:
    if not latencies:
        return {"p50": None, "p95": None, "mean": None}
    ordered = sorted(latencies)
    p50 = _quantile(ordered, 0.50)
    p95 = _quantile(ordered, 0.95)
    return {
        "p50": round(p50, 2),
        "p95": round(p95, 2),
        "mean": round(statistics.mean(latencies), 2),
    }


def _quantile(ordered: list[float], q: float) -> float:
    """Linear-interpolation percentile, matching statistics.quantiles."""
    if not ordered:
        return 0.0
    if len(ordered) == 1:
        return ordered[0]
    position = q * (len(ordered) - 1)
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    frac = position - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * frac
