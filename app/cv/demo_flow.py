"""LEGACY backend compatibility demo; not part of the production CV boundary."""
from __future__ import annotations

import asyncio
import hashlib
import json
import multiprocessing as mp
import os
import threading
import time
import uuid
from pathlib import Path
from queue import Empty
from typing import Callable

import cv2
import httpx
import websockets
import yaml

from app.config import settings
from app.cv.tracker import ByteTrackMultiObjectTracker
from app.cv.worker import CVWorker


class DemoFailure(RuntimeError):
    pass


def load_config(path: Path) -> dict:
    with path.open(encoding="utf-8") as stream:
        return yaml.safe_load(stream)


def _namespace(run_id: str, candidate_id: str) -> str:
    prefix = f"demo-{run_id}-"
    return prefix + candidate_id[:255 - len(prefix)]


def _receipt(value) -> dict | None:
    if value is None:
        return None
    return {"candidate_id": value.candidate_id, "status": value.status, "incident": value.incident}


def _worker_process(config: dict, run_id: str, output, stop_event) -> None:
    """Windows-spawn-safe target; constructs all CV/model objects in the child."""
    try:
        tracker = ByteTrackMultiObjectTracker(
            camera_id=config["camera_id"],
            frame_rate=float(config.get("inference_fps", 5.0)),
            **config.get("tracker", {}),
        )
        worker = CVWorker(
            camera_id=config["camera_id"], source_uri=config["sample_path"],
            tracker=tracker,
            candidate_id_namespace=lambda value: _namespace(run_id, value))
        candidates = worker.run(int(config["max_frames"]), stop_event, time.monotonic() + float(config["timeout_seconds"]))
        accepted = _receipt(worker.publisher.last_receipt)
        matching = next((item for item in candidates if accepted and item.event_id == accepted["candidate_id"]), None)
        duplicate = None
        if matching is not None and worker.publisher.publish(matching):
            duplicate = _receipt(worker.publisher.last_receipt)
        output.put({"accepted": accepted, "duplicate": duplicate})
    except BaseException as exc:
        output.put({"error": type(exc).__name__})


async def _process_execution(config: dict, run_id: str) -> dict:
    context = mp.get_context("spawn")
    output, stop_event = context.Queue(maxsize=1), context.Event()
    process = context.Process(target=_worker_process, args=(config, run_id, output, stop_event), daemon=False)
    timeout, grace = float(config["timeout_seconds"]), min(2.0, float(config["timeout_seconds"]))
    try:
        process.start()
        await asyncio.to_thread(process.join, timeout)
        timed_out = process.is_alive()
        if process.is_alive():
            stop_event.set()
            await asyncio.to_thread(process.join, grace)
        if process.is_alive():
            process.terminate()
            await asyncio.to_thread(process.join)
            raise DemoFailure("CV timeout: child terminated and joined")
        if timed_out:
            raise DemoFailure("CV timeout: child stopped and joined")
        try:
            result = output.get_nowait()
        except Empty as exc:
            raise DemoFailure("CV process: child returned no result") from exc
        if not isinstance(result, dict) or result.get("error"):
            raise DemoFailure("CV process: child execution failed")
        return result
    except DemoFailure:
        raise
    except Exception as exc:
        raise DemoFailure("CV process: start or IPC failure") from exc
    finally:
        if process.is_alive():
            process.terminate()
            process.join()
        process.close()
        output.close()
        output.join_thread()


async def _local_execution(config: dict, run_id: str, factory: Callable[..., object]) -> dict:
    """Fast test seam; production never uses this thread-based executor."""
    worker = factory(
        camera_id=config["camera_id"], source_uri=config["sample_path"],
        candidate_id_namespace=lambda value: _namespace(run_id, value))
    timeout, stop_event = float(config["timeout_seconds"]), threading.Event()
    future = asyncio.create_task(asyncio.to_thread(
        worker.run, int(config["max_frames"]), stop_event, time.monotonic() + timeout))
    try:
        candidates = await asyncio.wait_for(asyncio.shield(future), timeout=timeout)
    except TimeoutError as exc:
        stop_event.set()
        try:
            await asyncio.wait_for(asyncio.shield(future), timeout=min(2.0, timeout))
        except TimeoutError:
            raise DemoFailure("CV test executor: worker did not stop") from exc
        raise DemoFailure("CV timeout: worker stopped before post-timeout publish") from exc
    accepted = _receipt(getattr(worker.publisher, "last_receipt", None))
    matching = next((item for item in candidates if accepted and getattr(item, "event_id", getattr(item, "candidateId", None)) == accepted["candidate_id"]), None)
    duplicate = None
    if matching is not None and worker.publisher.publish(matching):
        duplicate = _receipt(worker.publisher.last_receipt)
    return {"accepted": accepted, "duplicate": duplicate}


def _json_response(url: str, timeout: float, stage: str) -> object:
    try:
        response = httpx.get(url, timeout=timeout)
        response.raise_for_status()
        return response.json()
    except (httpx.HTTPError, ValueError, TypeError) as exc:
        raise DemoFailure(f"{stage}: backend response unavailable or invalid") from exc


def _rows(value: object, stage: str) -> list[dict]:
    if not isinstance(value, list) or any(not isinstance(row, dict) or "id" not in row for row in value):
        raise DemoFailure(f"{stage}: invalid incident schema")
    return value


def _check_file(path: Path, stage: str) -> None:
    if not path.is_file() or path.stat().st_size == 0:
        raise DemoFailure(f"{stage}: missing or empty file: {path}")


def preflight(config: dict, real_mode: bool = True) -> None:
    if not os.getenv("EVENT_INGEST_TOKEN", "").strip():
        raise DemoFailure("preflight: EVENT_INGEST_TOKEN is blank")
    validation = config.get("validation", {})
    if validation != {"region_validator": "disabled", "external_llm": False}:
        raise DemoFailure("preflight validation: external VLM/LLM must be disabled")
    if float(config.get("duplicate_observation_seconds", 0)) < 2:
        raise DemoFailure("preflight duplicate: observation window must be at least 2 seconds")
    sample = Path(config["sample_path"])
    _check_file(sample, "preflight sample")
    capture = cv2.VideoCapture(str(sample)); readable, _ = capture.read(); capture.release()
    if not readable:
        raise DemoFailure(f"preflight sample: video is unreadable: {sample}")
    timeout = float(config["timeout_seconds"])
    for name, url in (("backend", config["backend_url"] + "/health"), ("frontend", config["frontend_url"])):
        try:
            response = httpx.get(url, timeout=timeout); response.raise_for_status()
            if name == "backend" and response.json().get("status") != "ok":
                raise ValueError
        except (httpx.HTTPError, ValueError, TypeError, AttributeError) as exc:
            raise DemoFailure(f"preflight {name}: health check failed") from exc
    if real_mode:
        model = settings.detector_config
        for key, checksum in (("checkpoint_path", "checkpoint_sha256"), ("backbone_path", "backbone_sha256")):
            path = Path(model[key]); _check_file(path, "preflight DEIMv2")
            if hashlib.sha256(path.read_bytes()).hexdigest().lower() != model[checksum].lower():
                raise DemoFailure(f"preflight DEIMv2: checksum mismatch: {path}")
        if not Path(model["source_path"]).is_dir():
            raise DemoFailure(f"preflight DEIMv2: missing source directory: {model['source_path']}")


async def run_demo(config: dict, worker_factory: Callable[..., object] | None = None,
                   executor: Callable[[dict, str], object] | None = None) -> dict:
    timeout, backend = float(config["timeout_seconds"]), config["backend_url"]
    baseline = {row["id"] for row in _rows(_json_response(backend + "/api/v1/alerts", timeout, "baseline REST"), "baseline REST")}
    run_id = uuid.uuid4().hex
    execute = executor or (_process_execution if worker_factory is None else
                           lambda cfg, rid: _local_execution(cfg, rid, worker_factory))
    try:
        async with websockets.connect(config["websocket_url"], open_timeout=timeout) as socket:
            result = await execute(config, run_id)
            accepted, duplicate = result.get("accepted"), result.get("duplicate")
            if not isinstance(accepted, dict) or accepted.get("status") != "ACCEPTED":
                raise DemoFailure("publish: no accepted backend receipt")
            incident = accepted.get("incident")
            if not isinstance(incident, dict) or not isinstance(incident.get("id"), int):
                raise DemoFailure("publish: accepted receipt has invalid incident schema")
            if not isinstance(duplicate, dict) or duplicate.get("status") != "DUPLICATE_IGNORED":
                raise DemoFailure("verify duplicate: missing duplicate receipt")
            incident_id, loop = incident["id"], asyncio.get_running_loop()
            envelope = await _matching_alert(socket, incident_id, loop.time() + timeout, True)
            rows = _rows(_json_response(backend + "/api/v1/alerts", timeout, "verify REST"), "verify REST")
            persisted = next((row for row in rows if row["id"] == incident_id), None)
            if not persisted or incident_id in baseline or persisted.get("source") != "CV" or persisted.get("camera_id") != 1:
                raise DemoFailure("verify REST: matching CV incident for camera 1 not persisted")
            duplicate_alert = await _matching_alert(
                socket, incident_id, loop.time() + float(config["duplicate_observation_seconds"]), False)
            if duplicate_alert:
                raise DemoFailure("verify duplicate: backend rebroadcast duplicate")
            return {"candidate_id": accepted["candidate_id"], "incident": persisted, "websocket": envelope}
    except DemoFailure:
        raise
    except Exception as exc:
        raise DemoFailure("WebSocket stage: connection or frame failure") from exc


async def _matching_alert(socket, incident_id: int, deadline: float, required: bool):
    loop = asyncio.get_running_loop()
    while (remaining := deadline - loop.time()) > 0:
        try:
            raw = await asyncio.wait_for(socket.recv(), timeout=remaining)
        except TimeoutError:
            break
        try:
            value = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            continue
        if (isinstance(value, dict) and value.get("type") == "NEW_ALERT" and
                isinstance(value.get("incident"), dict) and value["incident"].get("id") == incident_id):
            return value
    if required:
        raise DemoFailure("verify WebSocket: matching NEW_ALERT timed out")
    return None
