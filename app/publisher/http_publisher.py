import time
import uuid
import httpx
from app.common.schemas import EventCandidate
from app.publisher.base import EventPublisher


class HttpEventPublisher(EventPublisher):
    def __init__(
        self,
        endpoint_url: str = "http://127.0.0.1:8000/internal/api/v1/event-candidates",
        bearer_token: str = "",
        timeout_seconds: float = 5.0,
        max_retries: int = 3,
    ):
        self.endpoint_url = endpoint_url
        self.bearer_token = bearer_token
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries

    def publish(self, candidate: EventCandidate) -> bool:
        request_id = str(uuid.uuid4())
        if not self.bearer_token.strip():
            print(
                f"[HttpPublisher] Refused unauthenticated publish for candidateId={candidate.candidateId} "
                f"(request_id={request_id})"
            )
            return False
        headers = {
            "Content-Type": "application/json",
            "Idempotency-Key": candidate.candidateId,
            "X-Request-ID": request_id,
        }
        headers["Authorization"] = f"Bearer {self.bearer_token}"

        # Dump candidate JSON (excluding raw image matrices)
        payload = candidate.model_dump(mode="json")

        # Bounded retry loop with exponential backoff
        for attempt in range(1, self.max_retries + 1):
            try:
                with httpx.Client(timeout=self.timeout_seconds) as client:
                    response = client.post(self.endpoint_url, json=payload, headers=headers)

                if 200 <= response.status_code < 300:
                    print(
                        f"[HttpPublisher] Published candidateId={candidate.candidateId} "
                        f"(request_id={request_id}, status={response.status_code})"
                    )
                    return True
                elif response.status_code not in (408, 429) and response.status_code < 500:
                    print(
                        f"[HttpPublisher] Permanent failure for candidateId={candidate.candidateId} "
                        f"(request_id={request_id}, status={response.status_code})"
                    )
                    return False
                else:
                    print(
                        f"[HttpPublisher] Attempt {attempt}/{self.max_retries} failed for request_id={request_id}: "
                        f"HTTP {response.status_code}"
                    )
            except httpx.TransportError as e:
                print(
                    f"[HttpPublisher] Attempt {attempt}/{self.max_retries} error for request_id={request_id}: "
                    f"{type(e).__name__}"
                )

            if attempt < self.max_retries:
                time.sleep(0.2 * (2 ** (attempt - 1)))  # Backoff: 0.2s, 0.4s

        return False
