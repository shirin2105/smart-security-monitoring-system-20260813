import unittest

from app.cv.contracts import CVEventValidationError, validate_event
from tests.contracts.helpers import intrusion


class ValidationTests(unittest.TestCase):
    def assert_invalid(self, field, value):
        payload = intrusion().to_dict()
        payload[field] = value
        with self.assertRaises(CVEventValidationError):
            validate_event(payload)

    def test_invalid_taxonomy_lifecycle_confidence_and_time(self):
        for field, value in (
            ("event_type", "intrusion"),
            ("event_state", "ACTIVE"),
            ("cv_confidence", 1.1),
            ("event_time", "not-a-time"),
            ("event_time_s", -0.01),
        ):
            with self.subTest(field=field):
                self.assert_invalid(field, value)

    def test_timezone_is_required(self):
        self.assert_invalid("event_time", "2026-08-10T16:30:25")

    def test_unexpected_field_is_rejected(self):
        payload = intrusion().to_dict()
        payload["severity"] = "HIGH"
        with self.assertRaisesRegex(CVEventValidationError, "unexpected"):
            validate_event(payload)

    def test_missing_intrusion_evidence_is_rejected(self):
        payload = intrusion().to_dict()
        payload["evidence"].pop("zone_id")
        with self.assertRaisesRegex(CVEventValidationError, "zone_id"):
            validate_event(payload)

    def test_negative_and_duplicate_track_ids_are_rejected(self):
        payload = intrusion().to_dict()
        payload["objects"]["persons"][0]["track_id"] = -1
        with self.assertRaisesRegex(CVEventValidationError, "must be >= 0"):
            validate_event(payload)


if __name__ == "__main__":
    unittest.main()
