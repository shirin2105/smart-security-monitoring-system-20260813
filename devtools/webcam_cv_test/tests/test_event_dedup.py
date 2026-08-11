import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from webcam_event_adapter import RealtimeEventAdapter


class EventDedupTests(unittest.TestCase):
    def test_same_abandoned_candidate_is_logged_once(self):
        with tempfile.TemporaryDirectory() as temporary:
            log=Path(temporary)/"events.jsonl"
            config={"camera_id":"C", "intrusion":{"enabled":False}, "crowd":{"enabled":False},
                    "abandoned":{"enabled":True,"stationary_hold_s":3,"owner_away_hold_s":5}}
            adapter=RealtimeEventAdapter(config,log,Path(__file__).resolve().parents[3])
            event={"event_id":"AO_0001","candidate_time_s":8.0}
            fake=SimpleNamespace(
                StationaryConfig=lambda **kw: kw, OwnerConfig=lambda **kw: kw,
                Phase7CConfig=lambda **kw: kw,
                infer_phase7c=lambda rows,cfg:{"events":[event],"physical_luggage":[]})
            adapter.phase7c=fake
            row={"class_name":"luggage","eligible":True,"global_track_id":2,
                 "bbox_xyxy":[0,0,10,10],"frame_index":0,"timestamp_s":0,
                 "center_xy":[5,5],"confidence":.9}
            self.assertEqual(len(adapter.update([row],8,100)),1)
            self.assertEqual(adapter.update([row],9,100),[])
            self.assertEqual(len(log.read_text().splitlines()),1)
            self.assertEqual(json.loads(log.read_text())["event_type"],"ABANDONED_OBJECT_CANDIDATE")


if __name__ == "__main__": unittest.main()
