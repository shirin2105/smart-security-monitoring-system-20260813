import os
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import cv2
import numpy as np

OUTPUT_DIR = "examples"
os.makedirs(OUTPUT_DIR, exist_ok=True)


def create_intrusion_video(filename: str = "intrusion_positive_demo.mp4"):
    filepath = os.path.join(OUTPUT_DIR, filename)
    width, height = 1280, 720
    fps = 25
    duration_sec = 6
    total_frames = fps * duration_sec

    # Defined restricted zone polygon
    polygon_pts = np.array([[300, 200], [980, 200], [1100, 650], [200, 650]], np.int32)

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(filepath, fourcc, fps, (width, height))

    for frame_idx in range(total_frames):
        # Dark sleek background frame
        frame = np.ones((height, width, 3), dtype=np.uint8) * 30

        # Draw grid
        for x in range(0, width, 80):
            cv2.line(frame, (x, 0), (x, height), (45, 45, 45), 1)
        for y in range(0, height, 80):
            cv2.line(frame, (0, y), (width, y), (45, 45, 45), 1)

        # Move person from x=150 to x=600, y=150 to y=450
        progress = min(1.0, frame_idx / (total_frames * 0.7))
        person_x = int(150 + progress * 450)
        person_y = int(150 + progress * 300)

        bbox = [person_x - 30, person_y - 120, person_x + 30, person_y + 20]
        foot_x, foot_y = (person_x, person_y + 20)

        # Check if foot is inside polygon
        inside = cv2.pointPolygonTest(polygon_pts, (float(foot_x), float(foot_y)), False) >= 0

        # Polygon color (Red if intrusion active, else Amber)
        poly_color = (0, 0, 255) if (inside and frame_idx > 75) else (0, 165, 255)
        cv2.polylines(frame, [polygon_pts], isClosed=True, color=poly_color, thickness=3)
        cv2.putText(frame, "RESTRICTED ZONE (cam_01)", (310, 190), cv2.FONT_HERSHEY_SIMPLEX, 0.8, poly_color, 2)

        # Draw Person BBox
        cv2.rectangle(frame, (bbox[0], bbox[1]), (bbox[2], bbox[3]), (0, 255, 0), 2)
        cv2.circle(frame, (int(foot_x), int(foot_y)), 6, (0, 255, 255), -1)
        cv2.putText(frame, f"Person Track #17 (0.94)", (bbox[0], bbox[1] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        # Draw Header Bar
        cv2.rectangle(frame, (0, 0), (width, 50), (15, 15, 15), -1)
        cv2.putText(frame, f"CAM_01 | CCTV Live Stream | Frame: {frame_idx}/{total_frames}", (20, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        # Event Banner when Intrusion Triggered (after frame 75)
        if inside and frame_idx >= 75:
            dwell_sec = round((frame_idx - 50) / 25.0, 1)
            cv2.rectangle(frame, (20, 60), (550, 130), (0, 0, 180), -1)
            cv2.rectangle(frame, (20, 60), (550, 130), (0, 0, 255), 2)
            cv2.putText(frame, "CRITICAL ALERT: ZONE_INTRUSION", (35, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            cv2.putText(frame, f"Track #17 | Dwell: {dwell_sec}s >= 2.0s threshold", (35, 115), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (220, 220, 220), 1)

        writer.write(frame)

    writer.release()
    print(f"[VideoGenerator] Created intrusion demo video: {filepath}")


def create_crowd_video(filename: str = "crowd_positive_demo.mp4"):
    filepath = os.path.join(OUTPUT_DIR, filename)
    width, height = 1280, 720
    fps = 25
    duration_sec = 6
    total_frames = fps * duration_sec

    # ROI Polygon for Lobby Area
    polygon_pts = np.array([[100, 120], [1180, 120], [1180, 680], [100, 680]], np.int32)

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(filepath, fourcc, fps, (width, height))

    # 10 Simulated person positions inside lobby
    np.random.seed(42)
    base_positions = [
        (250 + i * 90, 300 + (i % 3) * 100) for i in range(10)
    ]

    for frame_idx in range(total_frames):
        frame = np.ones((height, width, 3), dtype=np.uint8) * 30

        # Draw grid
        for x in range(0, width, 80):
            cv2.line(frame, (x, 0), (x, height), (45, 45, 45), 1)
        for y in range(0, height, 80):
            cv2.line(frame, (0, y), (width, y), (45, 45, 45), 1)

        # Number of active people increases from 3 to 10
        active_count = min(10, 3 + frame_idx // 12)

        # Draw ROI Polygon
        is_crowd_active = (active_count >= 8 and frame_idx >= 50)
        poly_color = (0, 0, 255) if is_crowd_active else (255, 191, 0)
        cv2.polylines(frame, [polygon_pts], isClosed=True, color=poly_color, thickness=3)
        cv2.putText(frame, f"LOBBY ROI (cam_02) | Count: {active_count}/8 threshold", (120, 110), cv2.FONT_HERSHEY_SIMPLEX, 0.7, poly_color, 2)

        # Draw BBoxes for active people
        for i in range(active_count):
            px, py = base_positions[i]
            # Small subtle movement jitter
            jitter_x = int(np.sin(frame_idx * 0.1 + i) * 5)
            jitter_y = int(np.cos(frame_idx * 0.1 + i) * 5)
            px += jitter_x
            py += jitter_y

            bbox = [px - 25, py - 90, px + 25, py + 10]
            cv2.rectangle(frame, (bbox[0], bbox[1]), (bbox[2], bbox[3]), (0, 255, 0), 2)
            cv2.putText(frame, f"#{i+1}", (bbox[0], bbox[1] - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

        # Header
        cv2.rectangle(frame, (0, 0), (width, 50), (15, 15, 15), -1)
        cv2.putText(frame, f"CAM_02 | CCTV Live Stream | Frame: {frame_idx}/{total_frames}", (20, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        # Event Banner when Crowd Triggered
        if is_crowd_active:
            hold_sec = round((frame_idx - 50) / 25.0, 1)
            cv2.rectangle(frame, (20, 60), (580, 130), (0, 0, 180), -1)
            cv2.rectangle(frame, (20, 60), (580, 130), (0, 0, 255), 2)
            cv2.putText(frame, "WARNING ALERT: CROWD_THRESHOLD", (35, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            cv2.putText(frame, f"Distinct People: {active_count} >= 8 | Hold: {hold_sec}s", (35, 115), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (220, 220, 220), 1)

        writer.write(frame)

    writer.release()
    print(f"[VideoGenerator] Created crowd demo video: {filepath}")


if __name__ == "__main__":
    create_intrusion_video()
    create_crowd_video()
