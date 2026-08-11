import unittest

from app.evaluation.phase8_evaluator import evaluate_events
from app.evaluation.phase8_schema import GroundTruthEvent, PredictedEvent


class Phase8EvaluatorTests(unittest.TestCase):
    def test_perfect_match_reports_delay(self):
        gt = [GroundTruthEvent("c1", "cam1", "g1", "ABANDONED_OBJECT", 10, 15, 30)]
        pred = [PredictedEvent("c1", "cam1", "p1", "ABANDONED_OBJECT", 16)]
        result = evaluate_events(gt, pred, 1.0)
        self.assertEqual(result["overall"]["tp"], 1)
        self.assertEqual(result["overall"]["mean_detection_delay_s"], 1.0)
        self.assertEqual(result["unattributed_error_count"], 0)

    def test_fp_fn_receive_unknown_attribution(self):
        gt = [GroundTruthEvent("c1", "cam1", "g1", "ZONE_INTRUSION", 10, 11, 20)]
        pred = [PredictedEvent("c1", "cam1", "p1", "ZONE_INTRUSION", 40)]
        result = evaluate_events(gt, pred, 0.5)
        self.assertEqual((result["overall"]["tp"], result["overall"]["fp"],
                          result["overall"]["fn"]), (0, 1, 1))
        self.assertEqual(result["overall"]["false_alarms_per_hour"], 2.0)
        self.assertEqual(result["unattributed_error_count"], 2)
        self.assertTrue(all(row["error_category"] == "UNKNOWN" for row in result["errors"]))

    def test_zone_mismatch_does_not_match(self):
        gt = [GroundTruthEvent("c1", "cam1", "g1", "ZONE_INTRUSION", 1, 2, 4, "A")]
        pred = [PredictedEvent("c1", "cam1", "p1", "ZONE_INTRUSION", 2,
                               evidence={"zone_id": "B"})]
        result = evaluate_events(gt, pred, 1.0)
        self.assertEqual(result["overall"]["tp"], 0)

    def test_reviewed_attribution_is_complete(self):
        gt = [GroundTruthEvent("c1", "cam1", "g1", "CROWD_THRESHOLD", 1, 2, 3)]
        result = evaluate_events(gt, [], 1.0, attributions={
            ("c1", "CROWD_THRESHOLD", "FN", "g1"): {"error_category": "DETECTOR_MISS",
                            "root_cause_notes": "person missed", "component_to_change": "detector"}
        })
        self.assertTrue(result["attribution_complete"])
        self.assertEqual(result["errors"][0]["error_category"], "DETECTOR_MISS")

    def test_prediction_before_trigger_is_not_true_positive(self):
        gt = [GroundTruthEvent("c1", "cam1", "g1", "ZONE_INTRUSION", 0, 50, 100)]
        pred = [PredictedEvent("c1", "cam1", "p1", "ZONE_INTRUSION", 1)]
        result = evaluate_events(gt, pred, 1.0)
        self.assertEqual((result["overall"]["tp"], result["overall"]["fp"],
                          result["overall"]["fn"]), (0, 1, 1))

    def test_abandoned_false_prediction_is_not_called_false_alarm(self):
        pred = [PredictedEvent("c1", "cam1", "p1", "ABANDONED_OBJECT", 10,
                               evidence={"candidate_only": True})]
        result = evaluate_events([], pred, 0.5)
        row = result["by_event_type"]["ABANDONED_OBJECT"]
        self.assertIsNone(row["false_alarms_per_hour"])
        self.assertEqual(row["false_candidates_per_hour"], 2.0)
        self.assertEqual(result["overall"]["false_alarms_per_hour"], 0.0)

    def test_duplicate_prediction_identity_is_rejected(self):
        prediction = PredictedEvent("c1", "cam1", "same", "ZONE_INTRUSION", 10)
        with self.assertRaisesRegex(ValueError, "duplicate prediction"):
            evaluate_events([], [prediction, prediction], 1.0)


if __name__ == "__main__":
    unittest.main()
