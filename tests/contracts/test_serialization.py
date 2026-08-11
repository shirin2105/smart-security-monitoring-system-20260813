import json
import tempfile
import unittest
from pathlib import Path

from app.cv.contracts import CVEvent, append_event_jsonl, read_events_jsonl, validate_event
from tests.contracts.helpers import abandoned, crowd, intrusion


class SerializationTests(unittest.TestCase):
    def test_json_roundtrip(self):
        original = abandoned()
        restored = CVEvent.from_json(original.to_json())
        self.assertEqual(restored, original)
        self.assertEqual(json.loads(restored.to_json()), original.to_dict())

    def test_jsonl_roundtrip(self):
        events = [intrusion(), crowd(), abandoned()]
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "events.jsonl"
            for event in events:
                append_event_jsonl(path, event)
            restored = read_events_jsonl(path)
        self.assertEqual(restored, events)

    def test_all_bundled_examples_validate(self):
        root = Path(__file__).resolve().parents[2]
        for path in (root / "examples/cv_event_examples").glob("*.json"):
            with self.subTest(path=path.name):
                validate_event(json.loads(path.read_text(encoding="utf-8")))


if __name__ == "__main__":
    unittest.main()
