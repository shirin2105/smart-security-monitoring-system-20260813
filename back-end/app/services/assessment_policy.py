ALLOWED_OUTCOMES = {"MONITOR", "INVESTIGATE", "URGENT_REVIEW"}


def validate_assessment(value: dict) -> dict:
    if not isinstance(value, dict):
        raise ValueError("assessment must be an object")
    outcome, summary, rationale = value.get("outcome"), value.get("summary"), value.get("rationale")
    if outcome not in ALLOWED_OUTCOMES:
        raise ValueError("invalid outcome")
    if not isinstance(summary, str) or not summary.strip() or len(summary) > 500:
        raise ValueError("invalid summary")
    if not isinstance(rationale, str) or not rationale.strip() or len(rationale) > 1000:
        raise ValueError("invalid rationale")
    return {"outcome": outcome, "summary": summary.strip(), "rationale": rationale.strip()}


def fallback_assessment(reason: str) -> dict:
    return {"outcome": "INVESTIGATE", "summary": "Automated assessment unavailable; manual review required.",
            "rationale": f"Deterministic fallback: {reason}"}
