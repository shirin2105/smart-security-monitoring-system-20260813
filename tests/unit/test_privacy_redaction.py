import numpy as np
import pytest
from app.cv.redaction import PrivacyRedaction
from app.cv.evidence import EvidenceCapture
from app.common.schemas import FrameData
from app.common.enums import RedactionStatus
from app.common.time_utils import utc_now_iso


def test_privacy_redaction_success():
    redactor = PrivacyRedaction()
    image = np.ones((100, 100, 3), dtype=np.uint8) * 255
    bboxes = [[10, 10, 50, 50]]

    redacted, status = redactor.redact_image(image, bboxes=bboxes)
    assert status == RedactionStatus.COMPLETE
    assert redacted is not None
    assert redacted.shape == image.shape


def test_privacy_redaction_failure_gate():
    capture = EvidenceCapture(artifact_dir="artifacts/test_evidence")
    
    # Frame with None image -> trigger RedactionStatus.FAILED
    frame = FrameData(
        camera_id="cam_01",
        frame_id=1,
        captured_at=utc_now_iso(),
        source_type="SIMULATED",
        source_fps=5.0,
        inference_fps=5.0,
        image=None,
    )

    artifact = capture.capture_evidence(frame, candidate_id="test-fail-gate")
    
    # Section 17 Gate: available=False, redactionStatus=FAILED, uri=None
    assert artifact.available is False
    assert artifact.redactionStatus == RedactionStatus.FAILED
    assert artifact.uri is None
