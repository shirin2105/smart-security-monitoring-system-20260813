from typing import Optional
from app.common.enums import IntrusionState
from app.common.time_utils import calculate_duration_seconds, utc_now_iso


class TrackIntrusionStateTracker:
    def __init__(self, track_id: int, dwell_threshold: float = 1.0, exit_grace_seconds: float = 0.5):
        self.track_id = track_id
        self.dwell_threshold = dwell_threshold
        self.exit_grace_seconds = exit_grace_seconds
        self.current_state: IntrusionState = IntrusionState.OUTSIDE
        self.entered_zone_at: Optional[str] = None
        self.last_condition_true_at: Optional[str] = None
        self.event_generated: bool = False

    def update_inside(self, timestamp: str) -> IntrusionState:
        """Called when person foot point is inside polygon."""
        if self.current_state in (IntrusionState.OUTSIDE, IntrusionState.EXITED):
            self.current_state = IntrusionState.ENTERING
            self.entered_zone_at = timestamp
            self.last_condition_true_at = timestamp
        elif self.current_state in (IntrusionState.ENTERING, IntrusionState.INSIDE_PENDING):
            self.last_condition_true_at = timestamp
            duration = calculate_duration_seconds(self.entered_zone_at, timestamp)
            if duration >= self.dwell_threshold:
                self.current_state = IntrusionState.INTRUSION_ACTIVE
            else:
                self.current_state = IntrusionState.INSIDE_PENDING
        elif self.current_state == IntrusionState.INTRUSION_ACTIVE:
            self.last_condition_true_at = timestamp

        return self.current_state

    def update_outside(self, timestamp: Optional[str] = None) -> IntrusionState:
        """Called when person foot point is outside polygon."""
        if timestamp and self.last_condition_true_at and self.exit_grace_seconds > 0:
            outside_duration = calculate_duration_seconds(self.last_condition_true_at, timestamp)
            if outside_duration < self.exit_grace_seconds:
                return self.current_state

        if self.current_state in (IntrusionState.ENTERING, IntrusionState.INSIDE_PENDING):
            # Dwell condition broken before threshold duration -> reset to OUTSIDE
            self.current_state = IntrusionState.OUTSIDE
            self.entered_zone_at = None
            self.last_condition_true_at = None
        elif self.current_state == IntrusionState.INTRUSION_ACTIVE:
            self.current_state = IntrusionState.EXITED

        return self.current_state
