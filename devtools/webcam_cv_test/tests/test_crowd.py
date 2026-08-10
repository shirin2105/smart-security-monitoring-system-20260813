import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from test_intrusion import person
from webcam_event_adapter import RealtimeEventAdapter


class CrowdTests(unittest.TestCase):
    def test_hold_dedup_and_recovery(self):
        with tempfile.TemporaryDirectory() as temporary:
            config={"camera_id":"C", "intrusion":{"enabled":False},
                    "crowd":{"enabled":True,"threshold":2,"hold_s":2,"recovery_s":1},
                    "abandoned":{"enabled":False}}
            adapter=RealtimeEventAdapter(config,Path(temporary)/"events.jsonl",
                                         Path(__file__).resolve().parents[3])
            two=[person(1,10,20),person(2,30,40)]
            self.assertEqual(adapter.update(two,0,100),[])
            self.assertEqual(adapter.update(two,2.1,100)[0]["state"],"ACTIVE")
            self.assertEqual(adapter.update(two,2.2,100),[])
            self.assertEqual(adapter.update(two[:1],2.5,100),[])
            self.assertEqual(adapter.update(two[:1],3.6,100)[0]["state"],"CLEARED")


if __name__ == "__main__": unittest.main()
