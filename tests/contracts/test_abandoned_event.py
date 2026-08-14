import unittest

from app.cv.contracts import CVEventValidationError, validate_event
from tests.contracts.helpers import abandoned


class AbandonedEventTests(unittest.TestCase):
    def test_valid_abandoned(self):
        event = abandoned()
        validate_event(event)
        self.assertEqual(event.objects["luggage"]["physical_id"], "LUG_0001")

    def test_missing_owner_is_rejected(self):
        payload = abandoned().to_dict()
        payload["objects"]["owner"] = {}
        with self.assertRaisesRegex(CVEventValidationError, "person_track_id"):
            validate_event(payload)

    def test_missing_owner_away_evidence_is_rejected(self):
        payload = abandoned().to_dict()
        payload["evidence"].pop("owner_away_duration_s")
        with self.assertRaisesRegex(CVEventValidationError, "owner_away_duration_s"):
            validate_event(payload)


if __name__ == "__main__":
    unittest.main()
