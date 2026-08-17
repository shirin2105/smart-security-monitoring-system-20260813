# Camera 3 Live Webcam Feed & RTSP Swap Guide

## 1. Tổng quan (Overview)

Tài liệu này hướng dẫn cách vận hành luồng live webcam cho Camera #3 (`Camera Hàng Rào Tây`) trên giao diện web giám sát, tuân thủ nguyên tắc **Single Device Owner** (chỉ một tiến trình mở camera phần cứng), và cách chuyển đổi (swap) sang camera RTSP thật trong môi trường production.

---

## 2. Khởi chạy Webcam MJPEG Stream Server

### Lệnh chạy mặc định
Khởi chạy stream server độc lập trên cổng `8081` trỏ vào webcam mặc định (`index 0`):

```powershell
# Chạy với Python venv của dự án
.venv\Scripts\python.exe -m app.webcam_stream_server --index 0 --port 8081 --camera-id 3
```

### Các tham số tùy chọn (CLI Arguments)
- `--index`: Index của camera phần cứng trên máy tính (mặc định: `0`), hoặc RTSP URL / HTTP video feed.
- `--port`: Cổng lắng nghe HTTP (mặc định: `8081`).
- `--host`: Host bind (mặc định: `0.0.0.0`).
- `--camera-id`: ID camera hiển thị trong URL endpoint (mặc định: `3`).
- `--fps`: Giới hạn tốc độ khung hình truyền tải (mặc định: `15.0` FPS) nhằm tiết kiệm tài nguyên CPU/GPU laptop.
- `--quality`: Chất lượng nén JPEG từ `1` đến `100` (mặc định: `80`).

---

## 3. Quyền truy cập thiết bị (OS Camera Permissions)

* **Windows**: Vào *Settings* > *Privacy & security* > *Camera*. Đảm bảo *Camera access* và *Let desktop apps access your camera* đang được bật (`On`).
* **macOS / Linux**: Cấp quyền camera cho Terminal/iTerm khi có hộp thoại popup yêu cầu cấp quyền.

---

## 4. Kiểm tra & Nghiệm thu (Verification Checklist)

| Mục kiểm tra | Cách thực hiện | Kết quả mong đợi |
|---|---|---|
| **1. Health Check Endpoint** | `curl http://localhost:8081/healthz` | HTTP 200 `{"status": "ok", "device_open": true, "camera_id": "3"}` |
| **2. MJPEG Stream Trực Tiếp** | Mở trình duyệt tại `http://localhost:8081/cameras/3/stream` | Hiển thị hình ảnh chuyển động thời gian thực từ webcam |
| **3. Web Grid Tile** | Mở frontend web dashboard | Tile Camera #3 hiển thị video trực tiếp từ webcam |
| **4. Source Badge** | Kiểm tra nhãn trên tile Camera #3 | Hiển thị badge `CV thật` (LIVE), không phải `Nguồn giả lập` |
| **5. Cơ chế Fallback / Offline** | Tắt tiến trình `app.webcam_stream_server` (`Ctrl + C`) | Tile Camera #3 chuyển sang trạng thái OFFLINE / Không có tín hiệu (không bị đơ frame cũ) |
| **6. Đảm bảo Single Owner** | Kiểm tra process | Chỉ có duy nhất 1 tiến trình `webcam_stream_server` chiếm dụng device |

---

## 5. Chuyển đổi sang Camera RTSP Thật (Real RTSP Swap)

Khi triển khai hệ thống tới hạ tầng có camera RTSP phần cứng và GPU host:

1. **Cấu hình biến môi trường**:
   ```bash
   export CAMERA_3_URL="rtsp://admin:password@192.168.1.100:554/stream1"
   ```
2. **Kích hoạt trong `configs/cameras.yaml`**:
   ```yaml
   - camera_id: cam_03
     name: Camera Hàng Rào Tây
     source_type: RTSP
     source_uri: ${CAMERA_3_URL}
     enabled: true
   ```
3. **Cập nhật URL xem trực tiếp trên Web**:
   * Cấu hình lại `stream_url` của Camera #3 trong cơ sở dữ liệu / cấu hình backend trỏ về endpoint MJPEG gateway hoặc luồng HLS của camera RTSP.
