"""Create local contact sheets for content review of tests/clips."""

from pathlib import Path

import cv2
import numpy as np


SOURCE = Path("tests/clips")
OUTPUT = Path("artifacts/placement-transition/test-clip-review")


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for path in sorted(SOURCE.iterdir()):
        if path.suffix.lower() not in {".mp4", ".avi", ".webm"}:
            continue
        capture = cv2.VideoCapture(str(path))
        count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
        frames = []
        for index in [round(i * max(count - 1, 0) / 11) for i in range(12)]:
            capture.set(cv2.CAP_PROP_POS_FRAMES, index)
            ok, frame = capture.read()
            if ok:
                frames.append(cv2.resize(frame, (320, 180)))
        capture.release()
        if not frames:
            continue
        frames.extend([np.zeros_like(frames[0])] * (12 - len(frames)))
        sheet = np.vstack([np.hstack(frames[index:index + 4]) for index in range(0, 12, 4)])
        cv2.imwrite(str(OUTPUT / f"{path.stem}.jpg"), sheet)


if __name__ == "__main__":
    main()
