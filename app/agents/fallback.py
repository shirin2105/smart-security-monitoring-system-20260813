"""Deterministic fallback enrichment when the LLM is unavailable (FR-AI-06).

The fallback is template-based: it never infers identity, intent, or
criminality, and it never recommends a severity above the event type's
hard cap (PRD §8.2: ABANDONED_OBJECT is at most HIGH).
"""

from __future__ import annotations

from app.common.schemas import EnrichmentOutput

_EVENT_LABELS: dict[str, str] = {
    "ZONE_INTRUSION": "xâm nhập vùng cấm",
    "CROWD_THRESHOLD": "tụ tập đông người",
    "ABANDONED_OBJECT": "vật thể bỏ quên",
    "SUSPECTED_FALL": "nghi ngờ té ngã",
    "COVERAGE_DEGRADED": "suy giảm giám sát",
}

# Allow-list of checklist items (FR-AI-04: the agent proposes from an
# allow-list; it never performs or triggers any external action).
_ALLOWED_CHECKLIST: dict[str, list[str]] = {
    "ZONE_INTRUSION": [
        "Kiểm tra khu vực vùng cấm trên camera",
        "Xác minh nhân sự có phép vào khu vực",
        "Cập nhật trạng thái xử lý trên hệ thống",
    ],
    "CROWD_THRESHOLD": [
        "Theo dõi số lượng người trong khu vực",
        "Xác minh tình huống tại hiện trường",
        "Cập nhật trạng thái xử lý trên hệ thống",
    ],
    "ABANDONED_OBJECT": [
        "Xác minh vật thể bỏ quên trên camera",
        "Kiểm tra người sở hữu vật thể trong phạm vi",
        "Cập nhật trạng thái xử lý trên hệ thống",
    ],
    "SUSPECTED_FALL": [
        "Xác minh tình huống trên camera",
        "Cập nhật trạng thái xử lý trên hệ thống",
    ],
    "COVERAGE_DEGRADED": [
        "Kiểm tra trạng thái camera/nguồn video",
        "Cập nhật trạng thái xử lý trên hệ thống",
    ],
}


def _label(event_type: str) -> str:
    return _EVENT_LABELS.get(event_type, event_type)


def build_fallback_output(event: dict) -> EnrichmentOutput:
    """Create a deterministic advisory output from controlled event metadata."""
    event_type = str(event.get("eventType", ""))
    camera_id = str(event.get("cameraId", "unknown"))
    label = _label(event_type)

    if event_type == "ZONE_INTRUSION":
        severity = "HIGH"
        zone = str(event.get("zoneId", "unknown"))
        summary = (
            f"Phát hiện khả năng {label} tại khu vực {zone} "
            f"(camera {camera_id}). Cần người trực xác minh."
        )
    elif event_type == "CROWD_THRESHOLD":
        severity = "WARNING"
        count = int(event.get("trackCount", 0))
        summary = (
            f"Phát hiện {label} với khoảng {count} người "
            f"tại camera {camera_id}. Cần người trực kiểm tra."
        )
    elif event_type == "ABANDONED_OBJECT":
        severity = "HIGH"
        summary = (
            f"Phát hiện {label} tại camera {camera_id}. "
            f"Đây là candidate, cần người trực xác minh."
        )
    elif event_type == "SUSPECTED_FALL":
        severity = "WARNING"
        summary = f"Phát hiện {label} tại camera {camera_id}. Cần xác minh."
    else:
        severity = "INFO"
        summary = f"Ghi nhận sự kiện {label} tại camera {camera_id}."

    return EnrichmentOutput(
        recommendedSeverity=severity,
        rationale="Fallback rule-based theo loại sự kiện; LLM không khả dụng.",
        summary=summary,
        actionChecklist=_ALLOWED_CHECKLIST.get(event_type, _ALLOWED_CHECKLIST["COVERAGE_DEGRADED"]),
    )
