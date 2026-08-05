package vn.t176.patrol.ui.common

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import vn.t176.patrol.domain.model.EventState
import vn.t176.patrol.domain.model.Severity
import vn.t176.patrol.ui.theme.SeverityCritical
import vn.t176.patrol.ui.theme.SeverityHigh
import vn.t176.patrol.ui.theme.SeverityInfo
import vn.t176.patrol.ui.theme.SeverityWarning
import vn.t176.patrol.ui.theme.StateOk

@Composable
private fun Pill(text: String, color: Color, modifier: Modifier = Modifier) {
    Text(
        text = text,
        color = color,
        fontSize = 11.sp,
        fontWeight = FontWeight.SemiBold,
        modifier = modifier
            .background(color.copy(alpha = 0.15f), RoundedCornerShape(6.dp))
            .border(1.dp, color.copy(alpha = 0.45f), RoundedCornerShape(6.dp))
            .padding(horizontal = 8.dp, vertical = 3.dp),
    )
}

@Composable
fun SeverityBadge(severity: Severity, modifier: Modifier = Modifier) {
    Pill(text = severity.label, color = severity.color(), modifier = modifier)
}

@Composable
fun StateBadge(state: EventState, modifier: Modifier = Modifier) {
    val color = when (state) {
        EventState.OPEN -> SeverityInfo
        EventState.ACKNOWLEDGED -> StateOk
        EventState.PENDING_REVIEW -> SeverityWarning
        EventState.CONFIRMED -> SeverityCritical
        EventState.RESOLVED, EventState.DISMISSED -> MaterialTheme.colorScheme.onSurfaceVariant
        EventState.EXPIRED -> SeverityHigh
    }
    Pill(text = state.label, color = color, modifier = modifier)
}

@Composable
fun NeutralBadge(text: String, modifier: Modifier = Modifier) {
    Pill(text = text, color = MaterialTheme.colorScheme.onSurfaceVariant, modifier = modifier)
}

internal fun Severity.color(): Color = when (this) {
    Severity.INFO -> SeverityInfo
    Severity.WARNING -> SeverityWarning
    Severity.HIGH -> SeverityHigh
    Severity.CRITICAL -> SeverityCritical
}
