package vn.t176.patrol.data.fake

import android.content.Context
import kotlinx.serialization.json.Json

/**
 * Đọc fixture JSON trong assets.
 *
 * Fixture bám đúng schema ở mục 6 của plan, nên khi nối API thật chỉ cần đổi
 * repository — model và màn hình giữ nguyên. Đây cũng là phương án dự phòng khi
 * demo: backend chết vẫn chiếu được app.
 */
class FixtureLoader(private val context: Context) {

    /**
     * `ignoreUnknownKeys` để backend bổ sung field mới không làm app crash —
     * app là kênh phụ, không được đổ vỡ vì thay đổi ngoài tầm kiểm soát.
     */
    val json: Json = Json { ignoreUnknownKeys = true }

    fun read(fileName: String): String =
        context.assets.open("fixtures/$fileName").bufferedReader().use { it.readText() }
}
