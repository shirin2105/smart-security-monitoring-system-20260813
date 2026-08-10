#!/usr/bin/env python3
"""Gửi thông báo FCM data-only tới app T176 — dùng để test và demo.

Đây cũng là **bản tham chiếu cho backend**: phần `build_*_message` và
`send_message` dưới đây chính là thứ Hưng cần đưa vào FastAPI ở mục 6.4 của
PLAN_mobile_app_t176.md.

Hai điều bắt buộc, sai là hỏng:

1. **Không được có khối `notification`.** Nếu có, Android tự dựng thông báo khi
   app ở nền và `onMessageReceived` của app KHÔNG chạy — mất luôn deep link,
   mất phần tự gỡ thông báo, và mất cả tiêu đề tiếng Việt do app tự dựng.

2. **`android.priority` phải là `high`.** Mức thường bị Android trì hoãn khi máy
   đang tiết kiệm pin, cảnh báo an ninh mà tới trễ thì vô nghĩa.

Cách dùng:

    export FCM_SERVICE_ACCOUNT="E:/Download/t176-patrol-....json"
    export FCM_TOKEN="<token in ra tu Logcat>"

    python mobile/tools/send_fcm.py alert
    python mobile/tools/send_fcm.py alert --severity HIGH --camera "Cổng B2"
    python mobile/tools/send_fcm.py resolved --event-id evt_01H8ZK
    python mobile/tools/send_fcm.py dispatch --message "Ra kiểm tra cổng B2"
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone

import requests
from google.auth.transport.requests import Request
from google.oauth2 import service_account

# Console Windows mặc định là cp1252, không in được tiếng Việt và sẽ ném
# UnicodeEncodeError giữa chừng. Ép UTF-8 để chạy được trên máy của cả nhóm.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FCM_SCOPE = "https://www.googleapis.com/auth/firebase.messaging"
FCM_ENDPOINT = "https://fcm.googleapis.com/v1/projects/{project_id}/messages:send"

# Sự cố có sẵn trong fixture của app, để deep link mở ra là thấy dữ liệu thật.
DEFAULT_EVENT_ID = "evt_01H8ZK"


def load_credentials(path: str):
    """Đọc service account key và lấy access token OAuth2."""
    if not os.path.isfile(path):
        sys.exit(f"Không tìm thấy service account key: {path}")

    creds = service_account.Credentials.from_service_account_file(path, scopes=[FCM_SCOPE])
    creds.refresh(Request())

    with open(path, encoding="utf-8") as handle:
        project_id = json.load(handle)["project_id"]

    return creds, project_id


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def build_event_alert(
    token: str,
    event_id: str,
    event_type: str,
    severity: str,
    camera_name: str,
    action: str,
) -> dict:
    """Cảnh báo tự động từ CV — plan mục 6.2, loại 1.

    Payload chỉ mang MÃ và tên camera, không mang ảnh và không mang PII: thông
    báo hiện cả trên màn hình khóa (bất biến mục 4.1). App tự dịch mã sang chữ
    tiếng Việt để hiển thị.
    """
    return {
        "message": {
            "token": token,
            "data": {
                "type": "EVENT_ALERT",
                "eventId": event_id,
                "eventType": event_type,
                "severity": severity,
                "cameraName": camera_name,
                "detectedAt": now_iso(),
                "action": action,
            },
            "android": {
                "priority": "high",
                # Gộp theo sự cố: nhiều cập nhật của cùng một sự cố không xếp chồng.
                "collapse_key": event_id,
            },
        }
    }


def build_dispatch(token: str, dispatch_id: str, event_id: str, from_user: str, message: str) -> dict:
    """Điều phối thủ công từ người trực web — plan mục 6.2, loại 2.

    Đây là đường DUY NHẤT để sự cố mức INFO/WARNING tới được người đi tuần, vì
    push tự động chỉ gửi HIGH/CRITICAL.
    """
    return {
        "message": {
            "token": token,
            "data": {
                "type": "DISPATCH",
                "dispatchId": dispatch_id,
                "eventId": event_id,
                "fromUser": from_user,
                "message": message,
                "sentAt": now_iso(),
            },
            "android": {"priority": "high"},
        }
    }


def send_message(creds, project_id: str, payload: dict) -> None:
    response = requests.post(
        FCM_ENDPOINT.format(project_id=project_id),
        headers={
            "Authorization": f"Bearer {creds.token}",
            "Content-Type": "application/json; UTF-8",
        },
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        timeout=15,
    )

    if response.status_code == 200:
        print("Đã gửi:", response.json().get("name", ""))
        return

    # Token chết là chuyện bình thường (gỡ app, xoá dữ liệu). Backend phải xoá
    # token khỏi DB khi gặp hai mã này thay vì gửi mãi.
    if response.status_code == 404 or "UNREGISTERED" in response.text:
        sys.exit("Token không còn hiệu lực — mở lại app để lấy token mới.")

    sys.exit(f"FCM trả lỗi {response.status_code}:\n{response.text}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Gửi thông báo FCM data-only tới app T176")
    parser.add_argument(
        "kind",
        choices=["alert", "resolved", "dispatch"],
        help="alert: cảnh báo mới · resolved: gỡ thông báo · dispatch: tin điều phối",
    )
    parser.add_argument("--token", default=os.getenv("FCM_TOKEN"), help="FCM token của máy")
    parser.add_argument(
        "--service-account",
        default=os.getenv("FCM_SERVICE_ACCOUNT"),
        help="Đường dẫn service account key JSON",
    )
    parser.add_argument("--event-id", default=DEFAULT_EVENT_ID)
    parser.add_argument("--event-type", default="ZONE_INTRUSION")
    parser.add_argument("--severity", default="CRITICAL", choices=["INFO", "WARNING", "HIGH", "CRITICAL"])
    parser.add_argument("--camera", default="Camera Hàng Rào Tây")
    parser.add_argument("--from-user", default="Bảo vệ trực ca 2")
    parser.add_argument("--message", default="Ra kiểm tra khu vực cổng B2 ngay")

    args = parser.parse_args()

    if not args.service_account:
        sys.exit("Thiếu --service-account hoặc biến môi trường FCM_SERVICE_ACCOUNT")
    if not args.token:
        sys.exit("Thiếu --token hoặc biến môi trường FCM_TOKEN")

    creds, project_id = load_credentials(args.service_account)

    if args.kind == "dispatch":
        payload = build_dispatch(
            token=args.token,
            dispatch_id=f"dsp_{int(datetime.now().timestamp())}",
            event_id=args.event_id,
            from_user=args.from_user,
            message=args.message,
        )
    else:
        payload = build_event_alert(
            token=args.token,
            event_id=args.event_id,
            event_type=args.event_type,
            severity=args.severity,
            camera_name=args.camera,
            action="RESOLVED" if args.kind == "resolved" else "NEW",
        )

    print("Payload gửi đi:")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    send_message(creds, project_id, payload)


if __name__ == "__main__":
    main()
