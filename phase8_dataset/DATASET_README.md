# Phase 8 CAVIAR CV validation set

This directory is a frozen 20-video E2E validation set. It is **not training data**.
The original MPEG files and XML annotations were downloaded from the University
of Edinburgh [CAVIAR Test Case Scenarios](https://groups.inf.ed.ac.uk/vision/DATASETS/CAVIAR/CAVIARDATA1/).
CAVIAR documents these sequences as 384×288, 25 FPS surveillance video with
manual XML ground truth. The source is licensed CC BY-SA 3.0; derived annotations
in this directory retain the same attribution/share-alike requirement.

## Selection

- Abandoned/object: `LeftBag`, `LeftBag_AtChair`, `LeftBag_BehindChair`,
  `LeftBox`, `LeftBag_PickedUp`.
- Crowd/group: `Meet_Crowd`, `Meet_WalkTogether1`, `Meet_WalkTogether2`,
  `Meet_WalkSplit`, `Meet_Split_3rdGuy`.
- Intrusion/ROI: `Walk1`, `Walk2`, `Walk3`, `WalkByShop1cor`,
  `WalkByShop1front`.
- Negative/mixed: `Browse1`–`Browse4`, `Rest_InChair`.

`WalkByShop1cor` and `WalkByShop1front` are linked from CAVIARDATA1 and hosted
under CAVIARDATA2. All filenames are unchanged. No video was transcoded.

## Annotation policy

The project event schema is not native to CAVIAR, so it is derived reproducibly:

- `ZONE_INTRUSION`: an annotated person's foot point remains in that clip's
  configured intrusion ROI for 1 second.
- `CROWD_THRESHOLD`: at least two annotated people remain in the configured
  crowd ROI for 1 second.
- `ABANDONED_OBJECT`: XML role `leaving object`; trigger follows the first
  annotated frame by the frozen 5-second candidate dwell. `LeftBag_BehindChair`
  has no bag object in its XML because the bag is occluded; its event is explicitly
  marked as manually video-reviewed in `ground_truth_events.jsonl`.

Target clips use the central ROI. Non-target and mixed-negative camera rules use
an intentionally empty upper-right control ROI. This fixes positive/negative
coverage before model output is examined and prevents post-result threshold tuning.

The abandoned output remains candidate-level validation. It must not be reported
as a confirmed alarm or a production false-alarm rate.

## Rebuild and validate

```powershell
third_party/deimv2/.python311/python.exe tools/phase8/prepare_caviar_dataset.py
third_party/deimv2/.python311/python.exe tools/phase8/validate_config.py --manifest phase8_dataset/manifest.json
```

`source_xml/` preserves the downloaded XML evidence. `dataset_inventory.csv`
contains decoded duration/FPS/resolution for every original video.

## Benchmark

Use `tools/phase8/phase8_batch_runner.py` to produce one prediction JSONL and
runtime record per clip, then require complete 20/20 coverage before running
`tools/phase8/evaluate_events.py`. Review and attribute every FP/FN before making
an E2E performance claim.
