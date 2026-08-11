# DEIMv2 Phase 7A — Person and luggage

Kaggle run: `shirin21st/deimv2-phase-7a-person-luggage`, status `COMPLETE`.
Training used two Tesla T4 GPUs, DEIMv2-S commit
`0fff8d4dcdc272e6cf2d84be31399db471357941`, and the Phase-4 VisDrone
checkpoint as tuning initialization.

## PHASE 7A DATASET READY

- Taxonomy: `person`, `backpack`, `handbag`, `suitcase`.
- Train: 17,673 images, 197,399 objects.
- Train sources: 5,684 VisDrone images and 11,989 COCO luggage-context images.
- Train classes: person 170,133; backpack 8,720; handbag 12,354; suitcase 6,192.
- Val: 1,021 images, 17,924 objects.
- Val sources: 531 VisDrone images and 490 COCO luggage-context images.
- Val classes: person 16,710; backpack 371; handbag 540; suitcase 303.

## Smoke and training

`[SMOKE PASS] 4-class DEIMv2 pipeline works`

- Full training: 20 epochs, global batch 16, AMP and EMA enabled.
- Metric-best epoch: 17.
- Training evaluator at best epoch: AP 0.3392, AP-small 0.2534, AR-small 0.4561.
- Checkpoint: `/kaggle/working/outputs/phase7a_deimv2_s_person_luggage/best.pth`.
- Local checkpoint: `artifacts/phase7a-results/outputs/phase7a_deimv2_s_person_luggage/best.pth`.
- SHA-256: `56063D9767463AD4DB270BA34CB82F86469D56FCB323E44B22C018898CB29BF3`.
- `best.pth` and `best_stg1.pth` are byte-identical.

## PHASE 7A FINAL EVALUATION

| Dataset/mode | AP | AP-small | AR-small | FPS | Tiles/image |
|---|---:|---:|---:|---:|---:|
| combined_val/full640 | 0.3364 | 0.2401 | 0.4483 | 23.96 | 1.00 |
| combined_val/tile768_overlap20 | 0.3444 | 0.2504 | 0.4351 | 14.60 | 1.58 |
| visdrone_person_val/full640 | 0.2304 | 0.1963 | 0.2979 | 22.11 | 1.00 |
| visdrone_person_val/tile768_overlap20 | 0.2870 | 0.2555 | 0.3546 | 10.71 | 2.12 |
| coco_luggage_val/full640 | 0.4095 | 0.2837 | 0.4987 | 25.06 | 1.00 |
| coco_luggage_val/tile768_overlap20 | 0.4066 | 0.2813 | 0.4679 | 25.53 | 1.00 |

## [PER CLASS] visdrone_person_val / tile768_overlap20

```text
person     AP=0.2870 AP50=0.6343 AR100=0.3788
backpack   AP=-1.0000 AP50=-1.0000 AR100=-1.0000
handbag    AP=-1.0000 AP50=-1.0000 AR100=-1.0000
suitcase   AP=-1.0000 AP50=-1.0000 AR100=-1.0000
```

The three luggage classes are absent from this VisDrone-person subset; COCOeval
therefore reports `-1.0`, not a failed detector score.

## [PER CLASS] coco_luggage_val / tile768_overlap20

```text
person     AP=0.5695 AP50=0.8539 AR100=0.6607
backpack   AP=0.2542 AP50=0.4575 AR100=0.5431
handbag    AP=0.2705 AP50=0.4602 AR100=0.5270
suitcase   AP=0.5323 AP50=0.7727 AR100=0.6749
```

## Warnings

No traceback or fatal warning occurred. Non-fatal runtime warnings concerned
`TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD`, deprecated AMP `GradScaler` and NCCL env
names, tensor-to-scalar conversion, and notebook conversion escape sequences.
Distributed startup also warned that the barrier device was unspecified and
that ProcessGroupNCCL inferred rank-to-GPU mapping, which can hang if mappings
are heterogeneous. This run used two identical T4 GPUs and completed normally;
the warning did not invalidate its saved metrics or checkpoints.

Machine-readable evidence:

- [dataset audit](phase7a/dataset_audit.json)
- [evaluation summary](phase7a/phase7a_eval_summary.json)

## Unresolved questions

- Phase 7B/ByteTrack remains intentionally unstarted pending review of these results.
