import cv2
import numpy as np
from typing import Tuple, List, Optional
from app.common.enums import RedactionStatus


class PrivacyRedaction:
    """
    Performs privacy redaction (blurring person/face bounding boxes).
    Enforces strict Privacy Failure Gate: if redaction fails, image is rejected.
    """

    def redact_image(
        self, image: np.ndarray, bboxes: Optional[List[List[float]]] = None
    ) -> Tuple[Optional[np.ndarray], RedactionStatus]:
        if image is None or not isinstance(image, np.ndarray) or image.size == 0:
            return None, RedactionStatus.FAILED

        try:
            redacted = image.copy()
            h, w = redacted.shape[:2]

            if bboxes:
                for box in bboxes:
                    x1, y1, x2, y2 = [int(v) for v in box]
                    # Clamp to image boundaries
                    x1, y1 = max(0, x1), max(0, y1)
                    x2, y2 = min(w, x2), min(h, y2)

                    if x2 > x1 and y2 > y1:
                        # Blur detected person / face region
                        roi = redacted[y1:y2, x1:x2]
                        # Apply heavy Gaussian blur
                        kernel_w = max(3, (x2 - x1) // 3 | 1)
                        kernel_h = max(3, (y2 - y1) // 3 | 1)
                        blurred_roi = cv2.GaussianBlur(roi, (kernel_w, kernel_h), 0)
                        redacted[y1:y2, x1:x2] = blurred_roi
            else:
                # Full frame subtle blur if no specific bbox provided
                redacted = cv2.GaussianBlur(redacted, (15, 15), 0)

            return redacted, RedactionStatus.COMPLETE

        except Exception as e:
            # Privacy Failure Gate: Log error without exposing raw image
            print(f"[PrivacyRedaction] Redaction failed: {type(e).__name__}")
            return None, RedactionStatus.FAILED
