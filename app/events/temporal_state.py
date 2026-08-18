from typing import Optional
from app.common.enums import IntrusionState
from app.common.time_utils import calculate_duration_seconds, utc_now_iso


class TrackIntrusionStateTracker:
    def __init__(self, track_id: int, dwell_threshold: float = 2.0):
        self.track_id = track_id
        self.dwell_threshold = dwell_threshold
        self.current_state: IntrusionState = IntrusionState.OUTSIDE
        self.entered_zone_at: Optional[str] = None
        self.last_condition_true_at: Optional[str] = None
        self.event_generated: bool = False

    def update_inside(self, timestamp: str) -> IntrusionState:
        """Called when person foot point is inside polygon."""
        if self.current_state == IntrusionState.OUTSIDE:
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

        return self.current_state

    def update_outside(self) -> IntrusionState:
        """Called when person foot point is outside polygon."""
        if self.current_state in (IntrusionState.ENTERING, IntrusionState.INSIDE_PENDING):
            # Dwell condition broken before threshold duration -> reset to OUTSIDE
            self.current_state = IntrusionState.OUTSIDE
            self.entered_zone_at = None
            self.last_condition_true_at = None
        elif self.current_state == IntrusionState.INTRUSION_ACTIVE:
            self.current_state = IntrusionState.EXITED

        return self.current_state
