import time
import uuid
from typing import Optional
import httpx
from app.common.schemas import EventCandidate
from app.publisher.base import EventPublisher


class HttpEventPublisher(EventPublisher):
    def __init__(
        self,
        endpoint_url: str = "http://127.0.0.1:8000/internal/api/v1/event-candidates",
        timeout_seconds: float = 5.0,
        max_retries: int = 3,
    ):
        self.endpoint_url = endpoint_url
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries

    def publish(self, candidate: EventCandidate) -> bool:
        request_id = str(uuid.uuid4())
        headers = {
            "Content-Type": "application/json",
            "Idempotency-Key": candidate.candidateId,
            "X-Request-ID": request_id,
        }

        # Dump candidate JSON (excluding raw image matrices)
        payload = candidate.model_dump(mode="json")

        # Bounded retry loop with exponential backoff
        for attempt in range(1, self.max_retries + 1):
            try:
                with httpx.Client(timeout=self.timeout_seconds) as client:
                    response = client.post(self.endpoint_url, json=payload, headers=headers)

                if response.status_code in (200, 201):
                    print(
                        f"[HttpPublisher] Published candidateId={candidate.candidateId} "
                        f"(request_id={request_id}, status={response.status_code})"
                    )
                    return True
                else:
                    print(
                        f"[HttpPublisher] Attempt {attempt}/{self.max_retries} failed for request_id={request_id}: "
                        f"HTTP {response.status_code}"
                    )
            except Exception as e:
                print(
                    f"[HttpPublisher] Attempt {attempt}/{self.max_retries} error for request_id={request_id}: "
                    f"{type(e).__name__}"
                )

            if attempt < self.max_retries:
                time.sleep(0.2 * (2 ** (attempt - 1)))  # Backoff: 0.2s, 0.4s

        return False
