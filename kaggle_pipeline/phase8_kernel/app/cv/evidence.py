import os
import cv2
import numpy as np
from typing import List, Optional
from app.common.schemas import ArtifactData, FrameData
from app.common.enums import RedactionStatus
from app.cv.redaction import PrivacyRedaction


class EvidenceCapture:
    def __init__(self, artifact_dir: str = "artifacts/evidence"):
        self.artifact_dir = artifact_dir
        os.makedirs(self.artifact_dir, exist_ok=True)
        self.redactor = PrivacyRedaction()

    def capture_evidence(
        self,
        frame_data: FrameData,
        candidate_id: str,
        polygon_pts: Optional[List[List[float]]] = None,
        bboxes: Optional[List[List[float]]] = None,
    ) -> ArtifactData:
        if frame_data.image is None:
            return ArtifactData(available=False, redactionStatus=RedactionStatus.FAILED, uri=None)

        # Copy original frame to avoid modifying raw frame in memory
        annotated = frame_data.image.copy()

        # Draw polygon overlay
        if polygon_pts and len(polygon_pts) >= 3:
            pts = np.array(polygon_pts, np.int32).reshape((-1, 1, 2))
            cv2.polylines(annotated, [pts], isClosed=True, color=(0, 0, 255), thickness=2)

        # Draw bounding boxes
        if bboxes:
            for box in bboxes:
                x1, y1, x2, y2 = [int(v) for v in box]
                cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 255, 0), 2)

        # Apply Privacy Redaction Gate
        redacted_image, redaction_status = self.redactor.redact_image(annotated, bboxes=bboxes)

        # Section 17 Gate: If redaction failed, do NOT save image, do NOT serve image
        if redaction_status == RedactionStatus.FAILED or redacted_image is None:
            return ArtifactData(
                available=False,
                contentType="image/jpeg",
                redactionStatus=RedactionStatus.FAILED,
                uri=None,
            )

        image_filename = f"{candidate_id}.jpg"
        save_path = os.path.join(self.artifact_dir, image_filename)
        cv2.imwrite(save_path, redacted_image)

        return ArtifactData(
            available=True,
            contentType="image/jpeg",
            redactionStatus=RedactionStatus.COMPLETE,
            uri=f"/artifacts/evidence/{image_filename}",
        )
