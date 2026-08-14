import os
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import cv2
import numpy as np

OUTPUT_DIR = "examples"
os.makedirs(OUTPUT_DIR, exist_ok=True)


def create_abandoned_object_video(filename: str = "abandoned_object_demo.mp4"):
    filepath = os.path.join(OUTPUT_DIR, filename)
    width, height = 1280, 720
    fps = 25
    duration_sec = 6
    total_frames = fps * duration_sec

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(filepath, fourcc, fps, (width, height))

    # Fixed backpack position after drop
    bag_x, bag_y = 640, 450
    bag_bbox = [bag_x - 30, bag_y - 25, bag_x + 30, bag_y + 25]

    for frame_idx in range(total_frames):
        # Dark sleek background
        frame = np.ones((height, width, 3), dtype=np.uint8) * 30

        # Draw grid
        for x in range(0, width, 80):
            cv2.line(frame, (x, 0), (x, height), (45, 45, 45), 1)
        for y in range(0, height, 80):
            cv2.line(frame, (0, y), (width, y), (45, 45, 45), 1)

        # Timeline:
        # 0-30: Person carrying backpack, walking from (200, 450) to (640, 450)
        # 30-150: Backpack dropped at (640, 450), stationary
        # 30-150: Person walks away from (640, 450) to (1150, 450)
        
        if frame_idx < 30:
            progress = frame_idx / 30.0
            person_x = int(200 + progress * 440)
            person_y = 450
            person_present = True
            bag_present = True
            bag_current_bbox = [person_x + 10 - 25, person_y - 30 - 20, person_x + 10 + 25, person_y - 30 + 20]
        else:
            progress = min(1.0, (frame_idx - 30) / 40.0)
            person_x = int(640 + progress * 510)
            person_y = 450
            person_present = (person_x < 1100)
            bag_present = True
            bag_current_bbox = bag_bbox

        # Draw Header Bar
        cv2.rectangle(frame, (0, 0), (width, 50), (15, 15, 15), -1)
        cv2.putText(frame, f"CAM_01 | CCTV Live Stream | Frame: {frame_idx}/{total_frames}", (20, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        # Draw Person BBox
        if person_present:
            p_bbox = [person_x - 30, person_y - 120, person_x + 30, person_y + 20]
            cv2.rectangle(frame, (p_bbox[0], p_bbox[1]), (p_bbox[2], p_bbox[3]), (0, 255, 0), 2)
            cv2.putText(frame, "Person Track #1", (p_bbox[0], p_bbox[1] - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 2)

        # Abandoned logic trigger timeline (after frame 75: stationary 15s & owner absent 10s simulated)
        is_abandoned = (frame_idx >= 75)

        # Draw Backpack BBox
        if bag_present:
            b_color = (0, 0, 255) if is_abandoned else (255, 255, 0)
            cv2.rectangle(frame, (bag_current_bbox[0], bag_current_bbox[1]), (bag_current_bbox[2], bag_current_bbox[3]), b_color, 2)
            label = "Backpack #10 (ABANDONED)" if is_abandoned else "Backpack Track #10"
            cv2.putText(frame, label, (bag_current_bbox[0] - 20, bag_current_bbox[1] - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.55, b_color, 2)

        # Draw Banner when ABANDONED_OBJECT triggered
        if is_abandoned:
            stat_sec = round(15.0 + (frame_idx - 75) * 0.1, 1)
            absent_sec = round(10.0 + (frame_idx - 75) * 0.1, 1)
            cv2.rectangle(frame, (20, 60), (620, 135), (0, 0, 180), -1)
            cv2.rectangle(frame, (20, 60), (620, 135), (0, 0, 255), 2)
            cv2.putText(frame, "WARNING ALERT: ABANDONED_OBJECT", (35, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            cv2.putText(frame, f"Class: backpack | Stationary: {stat_sec}s | Owner Absent: {absent_sec}s", (35, 118), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (220, 220, 220), 1)

        writer.write(frame)

    writer.release()
    print(f"[VideoGenerator] Created Phase 4 demo video: {filepath}")


if __name__ == "__main__":
    create_abandoned_object_video()
