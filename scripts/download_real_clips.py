import os
import sys
import urllib.request
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

CLIPS_DIR = Path("tests/clips")
CLIPS_DIR.mkdir(parents=True, exist_ok=True)

REAL_VIDEO_URLS = {
    "vtest.avi": "https://raw.githubusercontent.com/opencv/opencv/master/samples/data/vtest.avi",
    "walking_people.mp4": "https://raw.githubusercontent.com/DeGirum/PySDKExamples/main/images/WalkingPeople2.mp4",
    "people_detection.mp4": "https://raw.githubusercontent.com/intel-iot-devkit/sample-videos/master/people-detection.mp4",
}


def download_real_videos():
    downloaded_files = {}
    for name, url in REAL_VIDEO_URLS.items():
        dest_path = CLIPS_DIR / name
        print(f"[Download] Fetching real CCTV video: {name} from {url}...")
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            )
            with urllib.request.urlopen(req, timeout=30) as response, open(dest_path, "wb") as out_file:
                out_file.write(response.read())
            print(f"[Download] Successfully downloaded {name} ({dest_path.stat().st_size} bytes)")
            downloaded_files[name] = dest_path
        except Exception as e:
            print(f"[Download] Failed to download {name}: {e}")

    return downloaded_files


if __name__ == "__main__":
    download_real_videos()
