# PHASE 7C v1 — ABANDONED OBJECT REASONING

## 0. Quyết định

Phase7B.1 đã giảm duplicate mạnh bằng generic luggage + cross-class NMS. Phase7C KHÔNG chạy lại detector.

Input chuẩn:
`tracks_v4.jsonl`

Phase7C chạy offline trước để iteration nhanh. Không cần GPU.

---

## 1. Mục tiêu Phase7C

Biến track-level output thành event-level reasoning:

```text
tracks_v4.jsonl
    ↓
rolling quality gate
    ↓
physical luggage stitching
    ↓
stationary detection
    ↓
owner association
    ↓
owner-away dwell
    ↓
ABANDONED_OBJECT_CANDIDATE
```

Đây là candidate cho backend/HITL, chưa tự xác nhận sự cố.

---

## 2. Rolling Quality Gate

Lỗi v4: một track chỉ cần vài high-confidence hit trong toàn lịch sử là có thể thành ELIGIBLE.

Phase7C thay bằng rolling + global quality.

### Person baseline
- rolling window = 2s
- high-confidence = 0.40
- rolling high-confidence ratio >= 0.30
- median confidence >= 0.40
- rolling-good ratio toàn track >= 0.50
- global high-confidence ratio >= 0.30

Mục tiêu: loại false-static person confidence thấp kéo dài.

### Luggage baseline
- min duration = 1.5s
- high-confidence = 0.35
- median confidence >= 0.35
- rolling high-confidence ratio >= 0.50
- rolling-good ratio >= 0.50
- global high-confidence ratio >= 0.50

Không dùng low-confidence tracker support trực tiếp làm semantic event evidence.

---

## 3. Physical luggage stitching

ByteTrack có thể đổi ID đúng lúc người đặt túi xuống.

Stitch chỉ áp dụng cho luggage tracks đã PASS quality.

A → B nếu:
- gap <= 0.80s
- center distance <= 80px
- normalized distance <= 1.20 bbox diagonal

Kết quả:
```text
track 2000004
      +
track 2000005
      ↓
physical_id = LUG_0001
```

Output phải giữ `source_track_ids` để audit.

---

## 4. Stationary detection

Không dùng pixel displacement tuyệt đối.

Rolling window 2s:
- robust center spread / bbox diagonal <= 0.15
- net displacement / bbox diagonal <= 0.20

Phải liên tục stationary >= 3s mới confirm.

State:
```text
MOVING
STATIONARY_PENDING
STATIONARY
```

Hold 3s giúp bỏ các pause ngắn khi người đang cầm túi.

---

## 5. Owner association

Chỉ dùng person tracks PASS rolling quality.

Association dùng lịch sử trước lúc luggage bắt đầu stationary dài.

Khoảng cách:
`distance(luggage_center, person_bbox) / person_bbox_diagonal`

Một person được chấm:
- inside_ratio: 65%
- near_ratio: 25%
- temporal overlap: 10%

Owner phải:
- overlap >=0.7s
- association score >=0.60

Không dùng "nearest person ở một frame".

---

## 6. Owner-away

Sau khi đã có owner:

```text
owner last near luggage
      ↓
owner không còn near
      ↓
5s dwell
```

Bag đồng thời phải vẫn nằm trong cùng stationary run.

Candidate time:
```text
max(
  stationary_confirmed_time,
  owner_last_near_time + 5s
)
```

Nếu bag mất/move trước thời điểm đó → không tạo event.

---

## 7. Optional ROI

Production camera nên có valid floor ROI.

Kaggle runner hỗ trợ:

```python
os.environ["ROI_POLYGON_JSON"] = \
'[[0,220],[640,220],[640,480],[0,480]]'
```

ROI chỉ kiểm tra bottom-center của luggage tại stationary candidate.

Không bật ROI mặc định vì polygon phải do từng camera cấu hình.

---

## 8. Kaggle runner

Phase7C không cần detector/checkpoint/GPU.

Inputs:
- Phase7B.1 `tracks_v4.jsonl`
- source video nếu muốn annotated output

Run:

```python
import os

os.environ["TRACKS_V4_PATH"] = \
"/kaggle/input/phase7b1-output/tracks_v4.jsonl"

os.environ["VIDEO_PATH"] = \
"/kaggle/input/datasets/shirin21st/phase7b-aboda-tracking-video/aboda-video1.avi"

# Optional ROI:
# os.environ["ROI_POLYGON_JSON"] = '[[0,220],[640,220],[640,480],[0,480]]'

!python /kaggle/input/phase7c-code/phase7c_kaggle_v1.py
```

CPU is enough. GPU accelerator can be OFF.

---

## 9. Outputs

```text
/kaggle/working/phase7c_v1/
  phase7c_summary.json
  quality_report.json
  physical_luggage.json
  owner_associations.json
  phase7c_events.json
  phase7c_timeline.jsonl
  annotated_phase7c.mp4
```

Expected event contract:

```json
{
  "event_id": "AO_0001",
  "physical_id": "LUG_0001",
  "source_track_ids": [2000004, 2000005],
  "owner_person_track_id": 1000005,
  "stationary_start_s": 0,
  "stationary_confirmed_s": 0,
  "owner_last_near_s": 0,
  "candidate_time_s": 0,
  "owner_away_s": 0,
  "association_score": 0,
  "bbox_xyxy": [],
  "center_xy": [],
  "status": "ABANDONED_OBJECT_CANDIDATE"
}
```

---

## 10. Gate Phase7C

Trên ABODA clip hiện tại, mục tiêu không phải benchmark tổng quát mà là kiểm tra logic:

1. false person confidence thấp bị quality gate loại;
2. low-quality luggage tracks bị loại;
3. bag trước/sau placement được stitch thành một physical object;
4. owner đúng được associate từ lịch sử;
5. short pause không tạo stationary event;
6. bag đặt xuống lâu mới được stationary;
7. owner rời đủ dwell mới tạo candidate;
8. không sinh nhiều event cho cùng physical luggage.

Sau clip này phải test thêm negative clips:
- owner đứng cạnh bag;
- owner rời rồi quay lại trước dwell;
- passer-by đi gần bag;
- bag có sẵn từ đầu;
- bag được nhấc đi;
- nhiều người quanh bag.

---

## 11. Không chờ Kaggle

Sau khi file Kaggle được tạo/chạy, agent KHÔNG chờ kết quả.

Tiếp tục ngay:
- event payload schema cho backend;
- unit tests negative cases;
- config YAML/JSON cho per-camera ROI/dwell;
- evaluation script tính event precision/recall, false alarms/hour, time-to-alert;
- README local replay.

Chỉ threshold tuning theo nhiều video mới phụ thuộc kết quả Kaggle.

---

## 12. Không làm trong Phase7C

- Không retrain DEIMv2.
- Không S4.
- Không EdgeCrafter.
- Không VLM.
- Không Re-ID.
- Không cross-camera.
- Không tự escalate/confirm event.
