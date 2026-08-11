---
title: Large-scale CV event dataset research
date: 2026-08-02
status: complete
---

# Large-scale CV Event Dataset Research

## Summary

No single public dataset directly supplies at least 100 independently labeled samples for all three current contracts: `ABANDONED_OBJECT`, polygon-based `ZONE_INTRUSION`, and temporal `CROWD_THRESHOLD`. Best practical combination is MEVA/ActEV or VIRAT for long-form surveillance and owner/entry behavior, plus WorldExpo'10 for crowd scenes. Build one local manifest with 100 samples per event rather than treating generic anomaly labels as ground truth.

## Findings

| Dataset | Scale | Useful for | Limitation |
|---|---:|---|---|
| MEVA / NIST ActEV | More than 250 hours ground video; public activity annotations; 37 activity types | `person_abandons_package`, `person_puts_down_object`, `person_enters_scene_through_structure`; long temporal context | Abandon-package positives are rare; arbitrary zone and crowd labels still need annotation |
| VIRAT | Natural surveillance video, tracks, 46 public activity types, more than 30 examples per original action class | Intrusion-like entry, person tracking, hard negatives | Does not directly define this project's polygon-zone or crowd-hold rules |
| WorldExpo'10 | 1,132 annotated video sequences from 108 surveillance cameras | Crowd count and cross-camera stress testing | Crowd-count annotations do not directly encode 10-second hold/release events |
| ShanghaiTech Campus | 437 videos, 130 abnormal events, 13 scenes | General false-positive/stress testing | Generic anomaly labels do not map to the three event contracts |
| UBnormal | 543 videos, 660 anomalies, 29 scenes | Synthetic anomaly stress testing | Synthetic; cannot count toward this repository's real-data benchmark totals |
| CAP | 1.45M clips, 512 fine-grained labels | Mining abandon/put-down action exemplars for VLM checks | Atomic activities are at most three seconds and mobile-camera domain; too short for the full 15s + owner-absence + post-roll flow |
| TOAST / PETS / ABODA | Strong event-specific abandoned-object examples | Qualitative regression and edge cases | Far below 100 clips; TOAST has 10 clips, PETS has seven scenarios |

## Recommendation

Create a 300-sample real-video benchmark:

- 100 abandoned-object samples from MEVA/ActEV long video: mine `person_abandons_package` and `person_puts_down_object`, then human-review owner departure; include positives, owner-return negatives, passerby negatives, and static-background-change negatives.
- 100 intrusion samples from MEVA/VIRAT: define project zone polygons per camera, then annotate entry/dwell and no-entry controls.
- 100 crowd samples from WorldExpo'10: select clips above and below the configured threshold and annotate whether the count persists for the configured hold interval.

Each manifest entry must include media hash, camera, processed range, event start/end, zone where applicable, provenance, and independent reviewer. Freeze predictions before scoring with `scripts/evaluate_real_video_events.py`.

## Practical order

1. Download a manageable MEVA/ActEV subset and its public annotations.
2. Download 100 WorldExpo sequences, not the entire corpus initially.
3. Add a conversion script from ActEV/KPF and WorldExpo annotations into `eval/manifests/`.
4. Human-review the resulting 300 clips because source labels do not exactly equal local policy.
5. Run the production worker once, freeze JSON predictions, then score precision, recall, false alerts/hour, and delay.

## Sources

- [NIST ActEV and supported MEVA data](https://actev.nist.gov/)
- [NIST ActEV SDL dataset access and activity list](https://actev.nist.gov/sdl)
- [MEVA WACV paper](https://openaccess.thecvf.com/content/WACV2021/papers/Corona_MEVA_A_Large-Scale_Multiview_Multimodal_Video_Dataset_for_Activity_Detection_WACV_2021_paper.pdf)
- [VIRAT official dataset](https://viratdata.org/index.html)
- [WorldExpo'10 official project page](https://www.ee.cuhk.edu.hk/~xgwang/expo.html)
- [UBnormal CVPR paper](https://openaccess.thecvf.com/content/CVPR2022/papers/Acsintoae_UBnormal_New_Benchmark_for_Supervised_Open-Set_Video_Anomaly_Detection_CVPR_2022_paper.pdf)
- [CAP official dataset](https://visym.github.io/cap/)
- [TOAST benchmark paper](https://www.sciencedirect.com/science/article/pii/S0957417425042733)

## Unresolved questions

- Exact count of publicly downloadable positive `person_abandons_package` instances must be measured after pulling the current MEVA/ActEV annotation release.
- Storage budget determines whether to download full MEVA or a curated subset first.
