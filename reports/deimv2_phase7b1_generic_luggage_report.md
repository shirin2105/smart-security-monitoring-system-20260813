# DEIMv2 Phase 7B.1 generic-luggage tracking

## Outcome

Kaggle kernel `shirin21st/deimv2-phase-7b-1-generic-luggage` completed successfully. The downloaded log reaches the final summary without a traceback, and all required runtime artifacts are present.

This is a tracking/candidate-generation result. It does not emit or validate an abandoned-object alarm, and no MOT ground truth is available for IDF1, HOTA, or MOTA claims.

## Runtime

| Measure | Result |
|---|---:|
| Input frames | 2,189 |
| Video duration | 73.040 s |
| Wall time | 108.907 s |
| Pipeline FPS | 20.100 |
| Inference mode | full640 |
| Average tiles/frame | 1.0 |
| JSONL observations | 5,019 |
| Invalid JSONL rows | 0 |

## Tracking result

| Class | Tracks | Mean duration | Median duration | Max duration | Mean confidence |
|---|---:|---:|---:|---:|---:|
| person | 11 | 11.144 s | 5.472 s | 44.344 s | 0.7922 |
| luggage | 6 | 7.852 s | 3.804 s | 25.626 s | 0.3734 |
| total | 17 | — | — | — | — |

The JSONL contains only `person` and merged `luggage` tracks. Status counts are 540 `TRACK_ONLY` and 4,479 `ELIGIBLE` observations.

## Generic-luggage merge

The detector produced 35,762 raw luggage-class boxes: 13,365 backpack, 14,607 handbag, and 7,790 suitcase. Cross-class merge/NMS retained 14,132 luggage detections and removed 21,630 duplicates, a 60.48% reduction.

## Important limitation

The startup warmup produced zero background anchors. The run is complete and the output contract is valid, but this clip does not provide evidence that static-background suppression is effective. Thresholds must remain untuned until the annotated candidate video is reviewed.

## Downloaded artifacts

- `annotated_all_tracks.mp4`
- `annotated_candidate_view.mp4`
- `tracks_v4.jsonl`
- `summary_v4.json`
- `background_anchors.json`
- complete Kaggle execution log

Large videos, JSONL, and raw logs remain under the ignored `artifacts/phase7b1-results/` directory. The compact summary and completion record are retained under `reports/phase7b1/`.

## Unresolved questions

- Does visual review confirm that the six luggage tracks retain true luggage while suppressing duplicate class boxes?
- Does the scene contain no stable startup background luggage, or are the provisional anchor rules too strict?
