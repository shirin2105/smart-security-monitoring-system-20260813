"""Render the ABODA demo window with real DEIMv2 + ByteTrack overlays."""
from __future__ import annotations

import argparse
import sys
from fractions import Fraction
from pathlib import Path

import av
import cv2

REPO_ROOT = Path(__file__).resolve().parents[1]
WEBCAM_TOOL = REPO_ROOT / "devtools" / "webcam_cv_test"
sys.path.insert(0, str(WEBCAM_TOOL))

from model_runtime import SharedCvRuntime  # noqa: E402


def draw_tracks(frame, rows: list[dict]) -> None:
    for row in rows:
        x1, y1, x2, y2 = map(int, row["bbox_xyxy"])
        is_person = row["class_name"] == "person"
        color = (52, 211, 153) if is_person else (0, 191, 255)
        label = f'{row["class_name"]} #{row["global_track_id"]} {row["confidence"]:.2f}'
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        (text_width, text_height), _ = cv2.getTextSize(
            label, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1
        )
        label_top = max(0, y1 - text_height - 8)
        cv2.rectangle(frame, (x1, label_top), (x1 + text_width + 6, y1), color, -1)
        cv2.putText(
            frame,
            label,
            (x1 + 3, y1 - 4),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            (15, 23, 42),
            1,
            cv2.LINE_AA,
        )


def render(source: Path, output: Path, start_s: float, duration_s: float) -> None:
    capture = cv2.VideoCapture(str(source))
    if not capture.isOpened():
        raise RuntimeError(f"Cannot open source video: {source}")
    fps = float(capture.get(cv2.CAP_PROP_FPS))
    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
    start_frame = round(start_s * fps)
    frame_count = round(duration_s * fps)
    capture.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

    runtime = SharedCvRuntime(REPO_ROOT, fps)
    output.parent.mkdir(parents=True, exist_ok=True)
    container = av.open(str(output), "w", options={"movflags": "faststart"})
    stream = container.add_stream("libx264", rate=Fraction(str(fps)))
    stream.width = width
    stream.height = height
    stream.pix_fmt = "yuv420p"
    stream.options = {"crf": "22", "preset": "medium"}

    try:
        for frame_index in range(frame_count):
            ok, frame = capture.read()
            if not ok:
                break
            rows, _, _ = runtime.process(frame, frame_index, frame_index / fps)
            draw_tracks(frame, rows)
            video_frame = av.VideoFrame.from_ndarray(frame, format="bgr24")
            for packet in stream.encode(video_frame):
                container.mux(packet)
            if frame_index % 60 == 0:
                print(f"rendered {frame_index + 1}/{frame_count}", flush=True)
        for packet in stream.encode():
            container.mux(packet)
    finally:
        container.close()
        capture.release()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path("datasets/aboda-video1.avi"))
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("front-end/public/videos/camera-1-aboda-tracking.h264.mp4"),
    )
    parser.add_argument("--start-s", type=float, default=40.0)
    parser.add_argument("--duration-s", type=float, default=16.0)
    args = parser.parse_args()
    render(args.source, args.output, args.start_s, args.duration_s)


if __name__ == "__main__":
    main()
