# App Android T176 — kênh cảnh báo

Kotlin + Jetpack Compose. Phụ trách: Nguyễn Ngọc Hiệp.
Bám theo `tai_lieu_p176/PLAN_mobile_app_t176.md`.

App là **kênh phụ**. Web là kênh chính: 6 camera, xem live, xử lý sự cố.
App tồn tại để người không ngồi trước màn hình biết khi có việc quan trọng.

---

## Chạy nhanh

```bash
cd mobile

# Tạo local.properties trỏ tới Android SDK của máy bạn
echo "sdk.dir=C:/Users/<TÊN>/AppData/Local/Android/Sdk" > local.properties

./gradlew :app:testMockDebugUnitTest    # 11 unit test cho ActionPolicy
./gradlew :app:assembleMockDebug        # APK chạy bằng fixture, không cần backend
adb install -r app/build/outputs/apk/mock/debug/app-mock-debug.apk
```

APK: `vn.t176.patrol.mock`, minSdk 26, targetSdk 35.

### Hai flavor

| Flavor | Nguồn dữ liệu | Dùng khi |
| --- | --- | --- |
| `mock` | fixture trong `assets/fixtures/` | Phát triển song song khi API chưa xong; **dự phòng lúc demo** nếu backend chết |
| `real` | API thật (Phase 2, chưa nối) | Chạy với backend của Hưng |

---

## Đã xong

**Cả hai role.**

| Màn | Nội dung |
| --- | --- |
| Đăng nhập | Chọn vai trò (giả, Phase 2 thay bằng API thật) |
| Cảnh báo | Danh sách, mặc định lọc HIGH/CRITICAL, có nút xem tất cả |
| Chi tiết | Camera, giờ, mức độ, trạng thái, mô tả, ô bằng chứng, hành động theo role |
| Nhật ký | Chỉ Quản lý thấy, phân trang theo cursor |

Đủ trạng thái rỗng / đang tải / lỗi ở cả bốn màn.

**Quản lý an ninh** — nhận cảnh báo, xem chi tiết, tra nhật ký. Không có nút
hành động nào; mọi quyết định đóng sự cố nằm trên web.

**Bảo vệ vật lý** — ba nút theo §3, chạy thật trên kho dữ liệu giả:

| Nút | Hiện khi | Kết quả |
| --- | --- | --- |
| Tôi đang xử lý | `OPEN` hoặc `PENDING_REVIEW`, mọi mức độ | → `ACKNOWLEDGED` |
| Đã xử lý xong | INFO/WARNING đã tiếp nhận | → `RESOLVED`, bắt buộc lý do |
| Báo cáo kết quả | HIGH/CRITICAL đã tiếp nhận | Ghi nhật ký, **không đổi state**, bắt buộc lý do |

Ba ràng buộc ghi của §3 đều đã thực thi:

- **`Idempotency-Key`** giữ theo từng hành động cho tới khi gửi thành công, nên
  thử lại sau lỗi mạng không tạo bản ghi đôi.
- **`expectedVersion`** — gửi phiên bản cũ thì bị từ chối như HTTP 409, app hiện
  "sự cố đã được người khác xử lý" rồi tự tải lại trạng thái mới.
- **Lý do bắt buộc** với "Đã xử lý xong" và "Báo cáo kết quả", tối thiểu 10 ký tự.

Trong lúc gửi, **toàn bộ** nút bị khóa chứ không riêng nút vừa bấm. Danh sách và
nhật ký tự tải lại mỗi khi quay về foreground, nên thao tác vừa làm hiện ngay.

**Hạ tầng thông báo (phần không cần Firebase)**

- Hai notification channel `SECURITY_ALERT` và `DISPATCH`, tạo lúc khởi động
- Xin quyền `POST_NOTIFICATIONS` cho Android 13+, xin sau khi đăng nhập
- `NotificationBuilder` dựng và gỡ được thông báo, deep link `app://event/{id}`

---

## `ActionPolicy` — file quan trọng nhất

`domain/ActionPolicy.kt` là nơi duy nhất quyết định nút nào hiện với ai. Màn
hình không được tự suy luận thêm.

| Vai trò | INFO / WARNING | HIGH / CRITICAL |
| --- | --- | --- |
| Bảo vệ vật lý | Tôi đang xử lý → Đã xử lý xong | Tôi đang xử lý → Báo cáo kết quả |
| **Quản lý** | **không có nút nào** | **không có nút nào** |

Quản lý trong app chỉ nhận cảnh báo và tra nhật ký; mọi quyết định đóng sự cố
nằm trên web. "Báo cáo kết quả" **không đổi state** — Quản lý đóng trên web.

**24 unit test**, chạy bằng `./gradlew :app:testMockDebugUnitTest`:

- `ActionPolicyTest` (11) — phủ toàn bộ tổ hợp role × severity × state, trong đó
  có một test khẳng định enum `PatrolAction` không chứa bất kỳ hành động nào tên
  `CONFIRM`/`DISMISS`/`APPROVE`/`DECLINE` — bất biến mục 4.5 của plan.
- `FakeEventStoreTest` (13) — chuyển trạng thái, idempotency, xung đột phiên bản,
  lý do bắt buộc, và việc "Báo cáo kết quả" không được đổi state.

> Đây là lớp trình bày. Backend vẫn phải kiểm tra lại toàn bộ, vì ẩn nút không
> phải là biện pháp bảo mật.

---

## Chưa làm — và ai làm

### Phase 0 còn thiếu: Firebase (cần người thật, không tự động được)

1. Tạo Firebase project, thêm Android app với `applicationId` **`vn.t176.patrol`**
2. Tải `google-services.json` bỏ vào `mobile/app/` (đã gitignore)
3. Thêm plugin `com.google.gms.google-services` và `firebase-messaging` vào build
4. In FCM token ra Logcat, gửi thử từ Firebase Console

**Phải test trên thiết bị thật.** Nhiều emulator image thiếu Google Play
Services nên FCM không chạy.

### Phase 2 — nối API (chờ backend)

Retrofit + `AuthInterceptor`, đổi repository theo flavor, Coil tải evidence với
disk cache tắt, `Idempotency-Key` + `expectedVersion` khi POST action.

### Phase 3 — FCM end-to-end

`AppFirebaseMessagingService` phân nhánh theo `type`, deep link, gỡ thông báo
khi `action=RESOLVED`, đăng ký token sau login và `DELETE` khi logout.

### Việc phía backend — gửi Hưng (mục 6.4 của plan)

- Bảng `device_token` (userId, token, platform, createdAt, lastSeenAt)
- Service gửi FCM, lọc `severity IN (HIGH, CRITICAL)` **và** camera trong site scope
- Gửi `action=RESOLVED` khi event đổi trạng thái để app gỡ thông báo
- `EventAction` loại `FIELD_REPORT` — **nhiều khả năng chưa có trong schema**
- Endpoint và bảng cho `DISPATCH`
- FCM service account key để trong secrets

---

## Khác biệt so với plan, đã cân nhắc

**`SharedPreferences` thay cho DataStore.** Plan mục 5 ghi DataStore
Preferences, nhưng thư viện đó chưa có trong Gradle cache của máy build, trong
khi Phase 1 chỉ cần lưu một phiên giả. `SessionStore` giữ nguyên interface nên
Phase 2 đổi sang DataStore không phải sửa màn hình.

**Hành động chạy trên kho dữ liệu giả, chưa gọi API.** `FakeEventStore` mô phỏng
đúng luật ghi của server (kiểm version, bắt buộc lý do, nhớ Idempotency-Key, ghi
audit cùng lúc với state), nên các nhánh lỗi 409/400 kiểm chứng được ngay. Phase
2 chỉ cần thay `FakeActionRepository` bằng bản Retrofit — `ActionRepository` giữ
nguyên chữ ký nên ViewModel và màn hình không phải sửa.

---

## Bẫy Android cần nhớ

- **`POST_NOTIFICATIONS`** thiếu quyền thì mọi thứ chạy đúng mà không hiện gì,
  và không có lỗi nào để lần ra.
- **Channel importance chỉ ăn lúc tạo lần đầu.** Sửa rồi cài đè không đổi gì —
  muốn test lại phải gỡ app cài lại.
- **Notification id** dùng `eventId.hashCode()` để gỡ đúng cái, đừng dùng số tăng dần.
- **Battery optimization** trì hoãn FCM priority thường — backend phải đặt
  `priority: high`.
