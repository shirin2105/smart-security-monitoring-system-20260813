import sys
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from app.config import settings
from app.cv.detector import DEIMv2Detector
from app.cv.multi_camera_runner import MultiCameraRunner

def main():
    print("=" * 60)
    print("AI CV Runner (Real DEIMv2 Inference)")
    print(f"Cameras: {[c.get('camera_id') for c in settings.cameras if c.get('enabled', True)]}")
    print("=" * 60)

    print("Loading DEIMv2 model and weights...")
    model_cfg = settings.detector_config
    shared_detector = DEIMv2Detector(**model_cfg)
    print("DEIMv2 model ready!")

    loop_count = 0
    while True:
        loop_count += 1
        print(f"\n[AI-LOOP #{loop_count}] Processing frames...")
        runner = MultiCameraRunner(detector=shared_detector)
        try:
            results = runner.run(max_frames=100)
            for cam_id, res in results.items():
                status = res.get("status")
                events = res.get("events", [])
                print(f"  Camera [{cam_id}]: status={status}, events={len(events)}")
        except Exception as e:
            print(f"  Error in CV loop: {e}")

        time.sleep(1)

if __name__ == "__main__":
    main()
