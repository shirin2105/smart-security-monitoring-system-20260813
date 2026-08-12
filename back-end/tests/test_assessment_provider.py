import io
import json
import urllib.error

import pytest

from app.services import assessment_provider as provider


def test_http_errors_are_classified(monkeypatch):
    monkeypatch.setenv("ASSESSMENT_LLM_API_KEY", "test")
    for code, error_type in ((408, provider.TransientProviderError), (429, provider.TransientProviderError),
                             (503, provider.TransientProviderError), (400, provider.PermanentProviderError)):
        def fail(*_args, status=code, **_kwargs):
            raise urllib.error.HTTPError("https://provider.invalid", status, "failure", {}, io.BytesIO())
        monkeypatch.setattr(provider.urllib.request, "urlopen", fail)
        with pytest.raises(error_type):
            provider.assess({"eventType": "ZONE_INTRUSION"})


def test_provider_rejects_large_and_non_object_output(monkeypatch):
    monkeypatch.setenv("ASSESSMENT_LLM_API_KEY", "test")
    monkeypatch.setenv("ASSESSMENT_MAX_RESPONSE_BYTES", "20")
    class Response:
        def __enter__(self): return self
        def __exit__(self, *_): return None
        def read(self, _limit): return b"x" * 21
    monkeypatch.setattr(provider.urllib.request, "urlopen", lambda *_a, **_k: Response())
    with pytest.raises(provider.PermanentProviderError):
        provider.assess({})

    payload = json.dumps({"choices": [{"message": {"content": "[]"}}]}).encode()
    monkeypatch.setenv("ASSESSMENT_MAX_RESPONSE_BYTES", "1024")
    Response.read = lambda self, _limit: payload
    with pytest.raises(provider.PermanentProviderError):
        provider.assess({})
