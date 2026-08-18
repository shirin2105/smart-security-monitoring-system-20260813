from types import SimpleNamespace

import pytest

from app.cv.demo_flow import DemoFailure, _process_execution, _worker_process
from app.publisher.http_publisher import PublishReceipt


CONFIG = {"camera_id": "cam_01", "sample_path": "sample.mp4", "max_frames": 2, "timeout_seconds": 0.01}


class Output:
    def __init__(self):
        self.value = None

    def put(self, value):
        self.value = value


def test_worker_process_returns_serializable_success_and_duplicate_receipts(monkeypatch):
    class Publisher:
        last_receipt = PublishReceipt("demo-run-original", "ACCEPTED", {"id": 7})

        def publish(self, candidate):
            self.last_receipt = PublishReceipt(candidate.candidateId, "DUPLICATE_IGNORED", {"id": 7})
            return True

    class Worker:
        def __init__(self, **kwargs):
            self.publisher = Publisher()

        def run(self, *args):
            return [SimpleNamespace(candidateId="demo-run-original", event_id="demo-run-original")]

    output = Output()
    monkeypatch.setattr("app.cv.demo_flow.CVWorker", Worker)
    _worker_process(CONFIG, "run", output, SimpleNamespace(is_set=lambda: False))

    assert output.value["accepted"]["status"] == "ACCEPTED"
    assert output.value["duplicate"]["status"] == "DUPLICATE_IGNORED"


def test_worker_process_sanitizes_child_exception(monkeypatch):
    class BrokenWorker:
        def __init__(self, **kwargs):
            raise RuntimeError("secret-token-and-body")

    output = Output()
    monkeypatch.setattr("app.cv.demo_flow.CVWorker", BrokenWorker)
    _worker_process(CONFIG, "run", output, SimpleNamespace(is_set=lambda: False))

    assert output.value == {"error": "RuntimeError"}
    assert "secret" not in str(output.value)


@pytest.mark.asyncio
async def test_process_timeout_terminates_and_joins_before_failure(monkeypatch):
    order = []

    class Event:
        def set(self): order.append("stop")

    class Queue:
        def close(self): order.append("queue-close")
        def join_thread(self): order.append("queue-join")

    class Process:
        alive = True
        def start(self): order.append("start")
        def join(self, timeout=None): order.append("join-final" if timeout is None else "join-bounded")
        def is_alive(self): return self.alive
        def terminate(self): self.alive = False; order.append("terminate")
        def close(self): order.append("process-close")

    process = Process()
    context = SimpleNamespace(
        Queue=lambda maxsize: Queue(), Event=Event,
        Process=lambda **kwargs: process,
    )
    monkeypatch.setattr("app.cv.demo_flow.mp.get_context", lambda mode: context)

    with pytest.raises(DemoFailure, match="child terminated and joined"):
        await _process_execution(CONFIG, "run")

    assert order.index("terminate") < order.index("join-final") < order.index("process-close")
    assert order[-2:] == ["queue-close", "queue-join"]
