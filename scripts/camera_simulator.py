import os
import sys
import time
import cv2
import requests
import yaml
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_URL = os.getenv("EVENT_INGEST_URL", "http://127.0.0.1:8000/api/v1/stream/clock")
TOKEN = os.getenv("EVENT_INGEST_TOKEN", "dev-secret-token-2026")

def main():
    print("=" * 60, flush=True)
    print("Simulated Camera Engine (Frontend Sync Proxy)", flush=True)
    print("=" * 60, flush=True)

    cameras_file = ROOT_DIR / "configs" / "cameras.yaml"
    with open(cameras_file, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    
    cameras = config.get("cameras", [])
    
    # Load all simulated cameras to guarantee frontend always has a clock if AI is off.
    cam_info = []
    for c in cameras:
        if c.get("source_type") != "SIMULATED":
            continue
        cam_id = c["camera_id"]
        uri = c.get("source_uri")
        path = ROOT_DIR / uri
        if path.exists():
            cap = cv2.VideoCapture(str(path))
            fps = cap.get(cv2.CAP_PROP_FPS)
            frames = cap.get(cv2.CAP_PROP_FRAME_COUNT)
            cap.release()
            duration = frames / fps if fps > 0 else 0
            if duration > 0:
                cam_info.append({
                    "camera_id": cam_id, 
                    "duration": float(duration), 
                    "epoch": time.time()
                })
                print(f"Loaded {cam_id}: {duration:.2f}s")
    
    print("\n[Engine Ready] - Sending Stream Clocks to Backend...")
    while True:
        now = time.time()
        for info in cam_info:
            # Shift the epoch forward exactly by 'duration' if a loop completed
            if now - info["epoch"] >= info["duration"]:
                loops = int((now - info["epoch"]) / info["duration"])
                info["epoch"] += loops * info["duration"]
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {TOKEN}",
            }
            body = {
                "cameraId": info["camera_id"],
                "epoch": float(info["epoch"]),
                "duration": float(info["duration"])
            }
            try:
                requests.post(BACKEND_URL, json=body, headers=headers, timeout=2)
            except Exception:
                pass
        
        # Send heartbeat sync every 10 seconds (Frontend refreshes every 20s)
        time.sleep(10)

if __name__ == "__main__":
    main()
