# Custom COCO dataset validation

**Status:** PASS

## train

- Images: 6471
- Annotations: 343204
- Empty images: 0 (0.00%)
- Occluded objects: 175901
- Objects per class: {'1': 79337, '2': 27059, '3': 10480, '4': 144866, '5': 24956, '6': 12875, '7': 4812, '8': 3246, '9': 5926, '10': 29647}
- Width px: {'gt_32': 136776, '8_to_16': 82346, '16_to_32': 93829, 'lt_8': 30253}
- Height px: {'gt_32': 139422, '16_to_32': 120859, '8_to_16': 71284, 'lt_8': 11639}
- Area px²: {'gt_32': 336960, '16_to_32': 4839, '8_to_16': 1336, 'lt_8': 69}
- COCO size: {'medium': 116696, 'small': 207524, 'large': 18984}
- Validation errors: 0

## val

- Images: 401
- Annotations: 27304
- Empty images: 0 (0.00%)
- Occluded objects: 15217
- Objects per class: {'1': 6392, '2': 3104, '3': 994, '4': 10643, '5': 1316, '6': 582, '7': 607, '8': 299, '9': 189, '10': 3178}
- Width px: {'8_to_16': 8198, '16_to_32': 6990, 'gt_32': 8571, 'lt_8': 3545}
- Height px: {'8_to_16': 6096, '16_to_32': 11247, 'gt_32': 8986, 'lt_8': 975}
- Area px²: {'gt_32': 26801, '16_to_32': 415, '8_to_16': 85, 'lt_8': 3}
- COCO size: {'small': 18839, 'medium': 7691, 'large': 774}
- Validation errors: 0

## test

- Images: 147
- Annotations: 11455
- Empty images: 0 (0.00%)
- Occluded objects: 6732
- Objects per class: {'1': 2452, '2': 2021, '3': 293, '4': 3421, '5': 659, '6': 168, '7': 438, '8': 233, '9': 62, '10': 1708}
- Width px: {'gt_32': 3575, '16_to_32': 3510, '8_to_16': 3266, 'lt_8': 1104}
- Height px: {'gt_32': 4273, '16_to_32': 4950, '8_to_16': 1892, 'lt_8': 340}
- Area px²: {'gt_32': 11225, '16_to_32': 183, '8_to_16': 45, 'lt_8': 2}
- COCO size: {'medium': 3425, 'small': 7736, 'large': 294}
- Validation errors: 0

## Split leakage

```json
{
  "video_ids": {
    "train_val": [],
    "train_test": [],
    "val_test": []
  },
  "camera_id": {
    "train_val": [],
    "train_test": [],
    "val_test": []
  },
  "camera": {
    "train_val": [],
    "train_test": [],
    "val_test": []
  },
  "scene_id": {
    "train_val": [],
    "train_test": [],
    "val_test": []
  },
  "scene": {
    "train_val": [],
    "train_test": [],
    "val_test": []
  }
}
```

## Category consistency

```json
{}
```
