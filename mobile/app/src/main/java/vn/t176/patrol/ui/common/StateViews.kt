package vn.t176.patrol.ui.common

import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CloudOff
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.VerifiedUser
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp

/**
 * Trạng thái rỗng / đang tải / lỗi dùng chung.
 *
 * Ba màn hình này là lúc người dùng dễ mất niềm tin nhất, nên mỗi cái đều phải
 * trả lời được ba câu: chuyện gì đang xảy ra, có nghiêm trọng không, và tôi
 * làm gì tiếp.
 */

/** Chiều cao tối thiểu của vùng chạm theo Material — dưới mức này ngón tay trượt. */
val MinTouchTarget = 48.dp

// ---------------------------------------------------------------------------
// Skeleton shimmer
// ---------------------------------------------------------------------------

/**
 * Nền nhấp nháy cho khối đang tải.
 *
 * Dùng skeleton thay vì vòng xoay vì nó cho biết trước **bố cục sắp hiện ra**,
 * nên mắt đã kịp định vị chỗ nào là mức độ, chỗ nào là tên camera trước khi dữ
 * liệu về. Vòng xoay chỉ nói "đợi đi" mà không nói đợi cái gì.
 */
@Composable
private fun Modifier.shimmer(): Modifier {
    val transition = rememberInfiniteTransition(label = "skeleton")
    val alpha by transition.animateFloat(
        initialValue = 0.35f,
        targetValue = 0.85f,
        animationSpec = infiniteRepeatable(
            animation = tween(durationMillis = 850),
            repeatMode = RepeatMode.Reverse,
        ),
        label = "skeleton-alpha",
    )
    return this.alpha(alpha)
}

/** Truyền `fraction` để giãn theo bề ngang, hoặc `widthDp` cho bề rộng cố định. */
@Composable
private fun SkeletonBlock(
    height: Int,
    fraction: Float? = null,
    widthDp: Int? = null,
    modifier: Modifier = Modifier,
) {
    val base = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.18f)
    val sized = when {
        widthDp != null -> modifier.width(widthDp.dp)
        fraction != null -> modifier.fillMaxWidth(fraction)
        else -> modifier.fillMaxWidth()
    }
    Box(
        modifier = sized
            .height(height.dp)
            .clip(RoundedCornerShape(6.dp))
            .background(base)
            .shimmer(),
    )
}

/**
 * Khung xương của một thẻ cảnh báo — bám đúng bố cục thật của `AlertRow`
 * để lúc dữ liệu về không bị giật layout.
 */
@Composable
fun AlertCardSkeleton(modifier: Modifier = Modifier) {
    Row(
        modifier = modifier
            .fillMaxWidth()
            .clip(MaterialTheme.shapes.medium)
            .background(MaterialTheme.colorScheme.surfaceVariant)
            .border(1.dp, MaterialTheme.colorScheme.outline, MaterialTheme.shapes.medium)
            .heightIn(min = 112.dp),
    ) {
        // Dải màu mức độ bên trái, giống thẻ thật.
        Box(
            modifier = Modifier
                .width(4.dp)
                .heightIn(min = 112.dp)
                .background(MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.18f))
                .shimmer(),
        )
        Column(
            modifier = Modifier.padding(14.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                SkeletonBlock(height = 20, widthDp = 84)
                SkeletonBlock(height = 20, widthDp = 96)
            }
            SkeletonBlock(height = 16, fraction = 0.55f)
            SkeletonBlock(height = 12, fraction = 0.9f)
            SkeletonBlock(height = 12, fraction = 0.7f)
        }
    }
}

/** Danh sách khung xương. */
@Composable
fun AlertListSkeleton(count: Int = 5, modifier: Modifier = Modifier) {
    Column(
        modifier = modifier
            .fillMaxSize()
            .padding(horizontal = 16.dp)
            // Trình đọc màn hình chỉ cần biết đang tải, không cần đọc từng ô rỗng.
            .semantics { contentDescription = "Đang tải danh sách cảnh báo" },
        verticalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        Box(Modifier.height(8.dp))
        repeat(count) { AlertCardSkeleton() }
    }
}

// ---------------------------------------------------------------------------
// Loading / Empty / Error
// ---------------------------------------------------------------------------

@Composable
fun LoadingState(label: String = "Đang tải…", modifier: Modifier = Modifier) {
    // Giữ chữ ký cũ cho các màn chưa cần skeleton (chi tiết sự cố, nhật ký).
    Column(
        modifier = modifier.fillMaxSize().padding(32.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center,
    ) {
        androidx.compose.material3.CircularProgressIndicator(
            strokeWidth = 2.dp,
            modifier = Modifier.size(28.dp),
        )
        Text(
            text = label,
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            modifier = Modifier.padding(top = 12.dp),
        )
    }
}

/**
 * Trạng thái rỗng.
 *
 * Với app an ninh, "không có gì" là **tin tốt** chứ không phải lỗi. Nên mặc
 * định nói rõ điều đó bằng màu xanh yên tâm thay vì để người trực phân vân
 * không biết app hỏng hay hiện trường thật sự yên.
 */
@Composable
fun EmptyState(
    title: String,
    hint: String? = null,
    icon: ImageVector = Icons.Default.VerifiedUser,
    modifier: Modifier = Modifier,
) {
    val accent = MaterialTheme.colorScheme.secondary

    Column(
        modifier = modifier.fillMaxSize().padding(32.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center,
    ) {
        Box(
            modifier = Modifier
                .size(72.dp)
                .clip(CircleShape)
                .background(accent.copy(alpha = 0.12f))
                .border(1.dp, accent.copy(alpha = 0.35f), CircleShape),
            contentAlignment = Alignment.Center,
        ) {
            Icon(
                imageVector = icon,
                contentDescription = null,
                tint = accent,
                modifier = Modifier.size(34.dp),
            )
        }
        Text(
            text = title,
            style = MaterialTheme.typography.titleSmall,
            textAlign = TextAlign.Center,
            modifier = Modifier.padding(top = 16.dp),
        )
        if (hint != null) {
            Text(
                text = hint,
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                textAlign = TextAlign.Center,
                modifier = Modifier.padding(top = 8.dp),
            )
        }
    }
}

/**
 * Trạng thái lỗi.
 *
 * Nói rõ **cái gì hỏng** và **dữ liệu có mất không**, rồi mới tới nút thử lại.
 * Người trực cần biết ngay là mình đang mù thông tin hay chỉ là màn hình cũ.
 */
@Composable
fun ErrorState(message: String, onRetry: () -> Unit, modifier: Modifier = Modifier) {
    val error = MaterialTheme.colorScheme.error

    Column(
        modifier = modifier.fillMaxSize().padding(32.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center,
    ) {
        Box(
            modifier = Modifier
                .size(72.dp)
                .clip(CircleShape)
                .background(MaterialTheme.colorScheme.errorContainer)
                .border(1.dp, error.copy(alpha = 0.5f), CircleShape),
            contentAlignment = Alignment.Center,
        ) {
            Icon(
                imageVector = Icons.Default.CloudOff,
                contentDescription = null,
                tint = error,
                modifier = Modifier.size(34.dp),
            )
        }

        Text(
            text = "Không lấy được dữ liệu",
            style = MaterialTheme.typography.titleSmall,
            textAlign = TextAlign.Center,
            modifier = Modifier.padding(top = 16.dp),
        )
        Text(
            text = message,
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            textAlign = TextAlign.Center,
            modifier = Modifier.padding(top = 8.dp),
        )
        Text(
            text = "Cảnh báo mới có thể chưa hiển thị. Kiểm tra kết nối mạng rồi thử lại.",
            style = MaterialTheme.typography.labelSmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            textAlign = TextAlign.Center,
            modifier = Modifier.padding(top = 6.dp),
        )

        Button(
            onClick = onRetry,
            contentPadding = PaddingValues(horizontal = 24.dp),
            colors = ButtonDefaults.buttonColors(
                containerColor = error,
                contentColor = MaterialTheme.colorScheme.onError,
            ),
            modifier = Modifier
                .padding(top = 20.dp)
                .heightIn(min = MinTouchTarget),
        ) {
            Icon(
                Icons.Default.Refresh,
                contentDescription = null,
                modifier = Modifier.size(18.dp),
            )
            Text(text = "Thử lại", modifier = Modifier.padding(start = 8.dp))
        }
    }
}
