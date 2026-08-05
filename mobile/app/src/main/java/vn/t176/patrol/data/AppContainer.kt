package vn.t176.patrol.data

import android.content.Context
import kotlinx.serialization.builtins.ListSerializer
import vn.t176.patrol.data.fake.FakeEventStore
import vn.t176.patrol.data.fake.FixtureLoader
import vn.t176.patrol.data.local.SessionStore
import vn.t176.patrol.data.repository.ActionRepository
import vn.t176.patrol.data.repository.AuditRepository
import vn.t176.patrol.data.repository.EventRepository
import vn.t176.patrol.data.repository.FakeActionRepository
import vn.t176.patrol.data.repository.FakeAuditRepository
import vn.t176.patrol.data.repository.FakeEventRepository
import vn.t176.patrol.domain.model.AuditEntry
import vn.t176.patrol.domain.model.SecurityEvent

/**
 * Nơi ráp các phụ thuộc lại với nhau — DI thủ công, đủ dùng cho quy mô app này
 * và không kéo thêm thư viện.
 *
 * Cả ba repository giả cùng nhìn một [FakeEventStore], nên hành động ở màn chi
 * tiết phản ánh ngay sang danh sách và nhật ký — giống backend thật.
 *
 * Phase 2 sẽ chọn repository theo `BuildConfig.FLAVOR`: flavor `mock` giữ
 * nguyên fixture, flavor `real` trỏ vào Retrofit.
 */
class AppContainer(context: Context) {

    private val appContext = context.applicationContext
    private val fixtures = FixtureLoader(appContext)

    private val store = FakeEventStore(
        initialEvents = fixtures.json.decodeFromString(
            ListSerializer(SecurityEvent.serializer()),
            fixtures.read("events.json"),
        ),
        initialAudit = fixtures.json.decodeFromString(
            ListSerializer(AuditEntry.serializer()),
            fixtures.read("audit.json"),
        ),
    )

    val sessionStore: SessionStore = SessionStore(appContext)
    val eventRepository: EventRepository = FakeEventRepository(store)
    val auditRepository: AuditRepository = FakeAuditRepository(store)
    val actionRepository: ActionRepository = FakeActionRepository(store)
}
