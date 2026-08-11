import unittest

from app.cv.contracts import validate_event
from tests.contracts.helpers import intrusion


class IntrusionEventTests(unittest.TestCase):
    def test_valid_intrusion(self):
        event = intrusion()
        validate_event(event)
        self.assertEqual(event.event_type, "ZONE_INTRUSION")
        self.assertEqual(event.objects["persons"][0]["track_id"], 1000012)

    def test_lifecycle_keeps_stable_event_id(self):
        ids = {intrusion(state).event_id for state in ("START", "UPDATE", "END")}
        self.assertEqual(ids, {"CAM01_IN_000001"})


if __name__ == "__main__":
    unittest.main()
