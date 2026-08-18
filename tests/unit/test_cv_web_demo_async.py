import json
import time
from types import SimpleNamespace

import pytest
import httpx

from app.cv.demo_flow import DemoFailure, run_demo
from app.publisher.http_publisher import PublishReceipt


CONFIG = {
    "camera_id": "cam_01", "sample_path": "sample.mp4", "max_frames": 5,
    "timeout_seconds": 0.1, "duplicate_observation_seconds": 2,
    "backend_url": "http://backend", "websocket_url": "ws://backend/ws/alerts",
}
INCIDENT = {"id": 8, "camera_id": 1, "source": "CV"}


class Response:
    def __init__(self, body):
        self.body = body

    def json(self):
        return self.body

    def raise_for_status(self):
        return None


class Publisher:
    def __init__(self, receipt=True):
        self.last_receipt = PublishReceipt("candidate-8", "ACCEPTED", INCIDENT) if receipt else None

    def publish(self, candidate):
        self.last_receipt = PublishReceipt(candidate.candidateId, "DUPLICATE_IGNORED", INCIDENT)
        return True


class Worker:
    def __init__(self, order, receipt=True, candidates=True, namespace=lambda value: value):
        assert order == ["ws-enter"]
        order.append("worker-created")
        candidate_id = namespace("candidate-8")
        self.publisher = Publisher(False)
        if receipt:
            self.publisher.last_receipt = PublishReceipt(candidate_id, "ACCEPTED", INCIDENT)
        self.candidates = [SimpleNamespace(candidateId=candidate_id, event_id=candidate_id)] if candidates else []

    def run(self, max_frames, stop_event=None, deadline=None):
        return self.candidates


class Socket:
    def __init__(self, messages, order):
        self.messages = list(messages)
        self.order = order
        self.exited = False

    async def __aenter__(self):
        self.order.append("ws-enter")
        return self

    async def __aexit__(self, *args):
        self.exited = True

    async def recv(self):
        if not self.messages:
            raise TimeoutError
        value = self.messages.pop(0)
        if isinstance(value, Exception):
            raise value
        return json.dumps(value)


def install(monkeypatch, messages, rows=None, receipt=True, candidates=True):
    order = []
    socket = Socket(messages, order)
    responses = iter([[], rows if rows is not None else [INCIDENT]])
    monkeypatch.setattr("app.cv.demo_flow.httpx.get", lambda *args, **kwargs: Response(next(responses)))
    monkeypatch.setattr("app.cv.demo_flow.websockets.connect", lambda *args, **kwargs: socket)

    def factory(**kwargs):
        if "region_validator" in kwargs:
            assert kwargs["region_validator"].__class__.__name__ == "DisabledRegionValidator"
        return Worker(order, receipt, candidates, kwargs["candidate_id_namespace"])

    return socket, order, factory


@pytest.mark.asyncio
async def test_run_demo_connects_first_and_matches_receipt_websocket_and_rest(monkeypatch):
    socket, order, factory = install(monkeypatch, [{"type": "NEW_ALERT", "incident": INCIDENT}])

    result = await run_demo(CONFIG, factory)

    assert order == ["ws-enter", "worker-created"]
    assert result["incident"] == INCIDENT
    assert socket.exited


@pytest.mark.asyncio
async def test_run_demo_fails_when_worker_publishes_nothing_and_cleans_up(monkeypatch):
    socket, _, factory = install(monkeypatch, [], receipt=False, candidates=False)

    with pytest.raises(DemoFailure, match="no accepted backend receipt"):
        await run_demo(CONFIG, factory)

    assert socket.exited


@pytest.mark.asyncio
async def test_run_demo_rejects_mismatched_alert_then_timeout(monkeypatch):
    socket, _, factory = install(monkeypatch, [
        {"type": "NEW_ALERT", "incident": {**INCIDENT, "id": 99}}, TimeoutError()
    ])

    with pytest.raises(DemoFailure, match="matching NEW_ALERT timed out"):
        await run_demo(CONFIG, factory)

    assert socket.exited


@pytest.mark.asyncio
async def test_run_demo_rejects_rest_mismatch_and_cleans_up(monkeypatch):
    socket, _, factory = install(
        monkeypatch, [{"type": "NEW_ALERT", "incident": INCIDENT}], rows=[{**INCIDENT, "source": "SIMULATOR"}])

    with pytest.raises(DemoFailure, match="matching CV incident"):
        await run_demo(CONFIG, factory)

    assert socket.exited


@pytest.mark.asyncio
async def test_run_demo_detects_delayed_duplicate_rebroadcast(monkeypatch):
    alert = {"type": "NEW_ALERT", "incident": INCIDENT}
    socket, _, factory = install(monkeypatch, [alert, {"type": "HEARTBEAT"}, "not-json", alert])

    with pytest.raises(DemoFailure, match="rebroadcast duplicate"):
        await run_demo(CONFIG, factory)

    assert socket.exited


@pytest.mark.asyncio
async def test_each_run_uses_a_fresh_candidate_namespace(monkeypatch):
    candidate_ids = []
    for _ in range(2):
        socket, _, factory = install(monkeypatch, [{"type": "NEW_ALERT", "incident": INCIDENT}])
        candidate_ids.append((await run_demo(CONFIG, factory))["candidate_id"])
        assert socket.exited

    assert candidate_ids[0] != candidate_ids[1]
    assert all(value.startswith("demo-") for value in candidate_ids)


@pytest.mark.asyncio
@pytest.mark.parametrize("body", [{"not": "a list"}, [{"camera_id": 1}]])
async def test_run_demo_normalizes_malformed_baseline_schema(monkeypatch, body):
    monkeypatch.setattr("app.cv.demo_flow.httpx.get", lambda *args, **kwargs: Response(body))

    with pytest.raises(DemoFailure, match="baseline REST: invalid incident schema"):
        await run_demo(CONFIG, lambda **kwargs: None)


@pytest.mark.asyncio
async def test_run_demo_timeout_signals_stop_and_prevents_publish(monkeypatch):
    order = []
    socket = Socket([], order)
    monkeypatch.setattr("app.cv.demo_flow.httpx.get", lambda *args, **kwargs: Response([]))
    monkeypatch.setattr("app.cv.demo_flow.websockets.connect", lambda *args, **kwargs: socket)
    publisher = SimpleNamespace(last_receipt=None, publish_count=0)

    class BlockingWorker:
        def __init__(self, **kwargs):
            self.publisher = publisher

        def run(self, max_frames, stop_event, deadline):
            while not stop_event.is_set():
                time.sleep(0.001)
            return []

    config = {**CONFIG, "timeout_seconds": 0.02}
    with pytest.raises(DemoFailure, match="worker stopped before post-timeout publish"):
        await run_demo(config, BlockingWorker)

    assert publisher.publish_count == 0
    assert socket.exited


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["status", "json"])
async def test_run_demo_normalizes_backend_status_and_json_errors(monkeypatch, failure):
    class BrokenResponse(Response):
        def raise_for_status(self):
            if failure == "status":
                raise httpx.HTTPError("secret upstream detail")

        def json(self):
            if failure == "json":
                raise ValueError("secret malformed body")
            return []

    monkeypatch.setattr("app.cv.demo_flow.httpx.get", lambda *args, **kwargs: BrokenResponse([]))

    with pytest.raises(DemoFailure, match="baseline REST: backend response unavailable or invalid") as error:
        await run_demo(CONFIG, lambda **kwargs: None)

    assert "secret" not in str(error.value)
