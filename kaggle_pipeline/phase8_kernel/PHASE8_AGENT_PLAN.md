# PHASE 8 — CV E2E VALIDATION SUITE

## Scope
Chỉ Computer Vision. Không làm LLM/backend/dashboard/HITL.

Mục tiêu: chứng minh 3 event MVP chạy tốt trên nhiều clip, không chỉ 1 video:
- `ZONE_INTRUSION`
- `CROWD_THRESHOLD`
- `ABANDONED_OBJECT`

## Freeze baseline
Không research model trước Phase8:
- DEIMv2-S Phase7A `best.pth`
- runtime `person + luggage`
- ByteTrack
- abandoned: generic luggage + cross-class NMS + rolling quality + physical stitching + stationary + owner association + owner-away
- small/normal resolution: `full640`
- high-res CCTV: `tile768_overlap20` khi cần

Không S4, không EdgeCrafter, không retrain nếu chưa có error attribution.

## Validation set vòng đầu
20–30 clips, gồm positive + negative.

### Abandoned positive
- mang túi -> đặt -> rời
- đặt túi -> đứng cạnh -> rời
- nhiều người, owner rời
- occlusion ngắn
- bag nhỏ/xa
- high-angle

### Abandoned negative
- owner đứng cạnh
- rời ngắn rồi quay lại
- passer-by
- bag có sẵn từ đầu
- đặt rồi nhấc lại
- vật cố định giống bag
- crowd/occlusion

### Intrusion
- xuyên ROI
- đứng trong ROI
- sát biên
- nhiều người
- ngoài ROI

### Crowd
- dưới threshold
- đúng threshold
- vượt threshold
- ra/vào liên tục
- occlusion

## Manifest
Dùng `manifest.json`. Mỗi clip có:
`clip_id`, `video_path`, `camera_id`, `camera_config_path`, `scenario_tags`.

## Ground truth
Dùng `ground_truth_events.jsonl`.
Mỗi event:
- clip_id
- camera_id
- event_id
- event_type
- start_s
- trigger_time_s
- end_s
- optional zone_id/notes

`trigger_time_s` là thời điểm hợp lý để hệ thống được phép alert.

## Prediction schema
Mọi event engine phải output JSONL:
- clip_id
- camera_id
- event_id
- event_type
- event_time_s
- optional start_s/end_s/confidence/evidence

Không dùng format riêng cho từng event.

## Metrics chính
- TP / FP / FN
- Event Precision
- Event Recall
- Event F1
- False alarms/hour
- Detection delay / time-to-alert

Secondary:
- FPS
- latency
- VRAM
- detector AP/AR chỉ diagnostic

## Error attribution
Mọi FP/FN phải gán 1 nguyên nhân:
- DETECTOR_MISS
- DETECTOR_FALSE_POSITIVE
- TRACK_ID_SWITCH
- TRACK_FRAGMENTATION
- PHYSICAL_STITCH_ERROR
- STATIONARY_LOGIC_ERROR
- OWNER_ASSOCIATION_ERROR
- OWNER_AWAY_LOGIC_ERROR
- ROI_ERROR
- DUPLICATE_EVENT
- TIMING_ERROR
- UNKNOWN

Không sửa model chỉ vì metric thấp; phải biết lỗi nằm tầng nào.

## Thin validation adapter
Agent tạo `inference_video.py` mỏng:
Input:
- --video
- --camera-id
- --camera-config
- --out

Output:
- `pred_events.jsonl`

Bên trong dùng lại code Intrusion/Crowd/Abandoned hiện có.
Không rewrite DEIMv2/ByteTrack/Phase7C.

## Batch
Dùng `phase8_batch_runner.py` cho nhiều clip.
Kaggle launcher: `phase8_kaggle_batch.py`.

## Kaggle rule
Sau khi batch Kaggle bắt đầu, KHÔNG chờ kết quả.
Tiếp tục ngay:
- evaluator
- schema validator
- error attribution report
- result table
- negative tests
- README
- camera config validation

Chỉ tuning/error attribution mới cần output batch.

## Quy tắc quyết định sau validation
- false detector nhiều -> hard-negative fine-tune nhẹ
- miss small/far -> thử tiling/adaptive trước, S4 chỉ nếu vẫn là bottleneck
- track fragmentation -> sửa tracker/stitcher
- owner sai -> sửa temporal association
- alert sớm/muộn -> tune dwell/hold
- ROI sai -> sửa per-camera config

Không thay nhiều component cùng lúc.

## Gate PASS Phase8
Không đặt metric cứng trước khi có validation set đủ đa dạng.
PASS vòng đầu khi:
1. cả 3 event chạy batch end-to-end;
2. schema prediction thống nhất;
3. TP/FP/FN rõ;
4. false alarms/hour đo được;
5. detection delay đo được;
6. FP/FN có error attribution;
7. không còn bug logic hiển nhiên;
8. xác định được bottleneck tiếp theo.

Sau Phase8:
- ổn -> Phase9 Unified CV Event Engine
- chưa ổn -> Phase8B sửa đúng bottleneck rồi rerun cùng validation set
