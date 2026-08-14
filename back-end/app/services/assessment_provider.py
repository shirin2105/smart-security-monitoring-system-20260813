import json
import os
import urllib.error
import urllib.request


class TransientProviderError(RuntimeError):
    pass


class PermanentProviderError(RuntimeError):
    pass


def assess(snapshot: dict) -> dict:
    key = os.getenv("ASSESSMENT_LLM_API_KEY", "")
    if not key:
        raise PermanentProviderError("missing API key")
    base = os.getenv("ASSESSMENT_LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    body = json.dumps({"model": os.getenv("ASSESSMENT_LLM_MODEL", "gpt-4.1-mini"),
        "response_format": {"type": "json_object"}, "messages": [
        {"role": "system", "content": "Assess security metadata. Return JSON: outcome, summary, rationale."},
        {"role": "user", "content": json.dumps(snapshot, separators=(",", ":"))}]}).encode()
    request = urllib.request.Request(f"{base}/chat/completions", body,
        {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=float(os.getenv("ASSESSMENT_LLM_TIMEOUT_SECONDS", "15"))) as response:
            raw = response.read(int(os.getenv("ASSESSMENT_MAX_RESPONSE_BYTES", "65536")) + 1)
        if len(raw) > int(os.getenv("ASSESSMENT_MAX_RESPONSE_BYTES", "65536")):
            raise PermanentProviderError("provider response too large")
        result = json.loads(raw)
        output = json.loads(result["choices"][0]["message"]["content"])
        if not isinstance(output, dict):
            raise PermanentProviderError("provider output must be an object")
        return output
    except urllib.error.HTTPError as exc:
        if exc.code in {408, 429} or 500 <= exc.code < 600:
            raise TransientProviderError(f"provider HTTP {exc.code}") from exc
        raise PermanentProviderError(f"provider HTTP {exc.code}") from exc
    except (TimeoutError, urllib.error.URLError) as exc:
        raise TransientProviderError(str(exc)) from exc
    except (KeyError, TypeError, json.JSONDecodeError) as exc:
        raise PermanentProviderError("invalid provider response") from exc
