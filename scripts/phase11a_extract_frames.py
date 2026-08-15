"""Extract frames from CAVIAR clips at requested times for visual review.

Usage: python scripts/phase11a_extract_frames.py <clip> <t1> [<t2> ...]
Writes frames to .qa-tmp/phase11a/frames/<clip>_t<t>s.jpg
"""

from __future__ import annotations

import sys
from pathlib import Path

import cv2


def extract(clip: str, times: list[float], out_dir: Path) -> list[Path]:
    path = Path("phase8_dataset/videos") / f"{clip}.mpg"
    cap = cv2.VideoCapture(str(path))
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for t in times:
        frame_idx = int(round(t * fps))
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ok, frame = cap.read()
        if not ok:
            continue
        out = out_dir / f"{clip}_t{t:.1f}s.jpg"
        cv2.imwrite(str(out), frame)
        written.append(out)
    cap.release()
    return written


def main() -> int:
    clip = sys.argv[1]
    times = [float(t) for t in sys.argv[2:]]
    out_dir = Path(".qa-tmp/phase11a/frames")
    written = extract(clip, times, out_dir)
    for path in written:
        print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
