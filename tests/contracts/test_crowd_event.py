import unittest

from app.cv.contracts import CVEventValidationError, validate_event
from tests.contracts.helpers import crowd


class CrowdEventTests(unittest.TestCase):
    def test_valid_crowd(self):
        event = crowd()
        validate_event(event)
        self.assertEqual(event.objects["person_count"], 2)

    def test_count_must_match_track_ids(self):
        payload = crowd().to_dict()
        payload["objects"]["person_count"] = 3
        with self.assertRaisesRegex(CVEventValidationError, "must equal"):
            validate_event(payload)

    def test_missing_threshold_is_rejected(self):
        payload = crowd().to_dict()
        payload["evidence"].pop("threshold")
        with self.assertRaisesRegex(CVEventValidationError, "threshold"):
            validate_event(payload)

    def test_duplicate_track_ids_are_rejected(self):
        payload = crowd().to_dict()
        payload["objects"]["person_track_ids"] = [1001, 1001]
        with self.assertRaisesRegex(CVEventValidationError, "unique"):
            validate_event(payload)


if __name__ == "__main__":
    unittest.main()
