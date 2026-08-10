from __future__ import annotations

import argparse
import atexit
import json
import sys
import time
from pathlib import Path

from flask import Flask, Response, jsonify, send_from_directory

TOOL_ROOT = Path(__file__).resolve().parent
REPO_ROOT = TOOL_ROOT.parents[1]
if str(TOOL_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOL_ROOT))

from webcam_runner import WebcamRunner


def create_app(camera_override: int | None = None) -> Flask:
    config = json.loads((TOOL_ROOT / "config.json").read_text(encoding="utf-8"))
    runner = WebcamRunner(config, TOOL_ROOT, REPO_ROOT)
    app = Flask(__name__)
    app.config["WEBCAM_RUNNER"] = runner

    @app.get("/")
    def index():
        return send_from_directory(TOOL_ROOT / "web", "index.html")

    @app.get("/video_feed")
    def video_feed():
        def stream():
            while True:
                with runner.lock:
                    frame = runner.latest_jpeg
                if frame:
                    yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
                time.sleep(0.03)
        return Response(stream(), mimetype="multipart/x-mixed-replace; boundary=frame")

    @app.get("/status")
    def status():
        return jsonify(runner.snapshot())

    @app.post("/start")
    def start():
        runner.start(camera_override)
        return jsonify({"ok": True})

    @app.post("/stop")
    def stop():
        runner.stop()
        return jsonify({"ok": True})

    @app.post("/events/clear")
    def clear_events():
        runner.clear_events()
        return jsonify({"ok": True})

    atexit.register(runner.stop)
    return app


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 8.5 local webcam CV test")
    parser.add_argument("--camera", type=int)
    args = parser.parse_args()
    app = create_app(args.camera)
    runner = app.config["WEBCAM_RUNNER"]
    runner.start(args.camera)
    web = runner.config["web"]
    try:
        app.run(host=web["host"], port=int(web["port"]), threaded=True, use_reloader=False)
    finally:
        runner.stop()


if __name__ == "__main__":
    main()
