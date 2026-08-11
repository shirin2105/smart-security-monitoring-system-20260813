import os
import glob

dataset_dir = "datasets/cctv_abandoned_combined"
lbl_files = glob.glob(os.path.join(dataset_dir, "labels/**/*.txt"), recursive=True)

print(f"=== Fixing {len(lbl_files)} label files to use contiguous class indices 0, 1, 2, 3 ===")

CLASS_MAP = {
    "0": "0",
    "24": "1",
    "26": "2",
    "28": "3"
}

fixed_count = 0

for lbl_path in lbl_files:
    if not os.path.exists(lbl_path):
        continue
    with open(lbl_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
        
    new_lines = []
    for line in lines:
        parts = line.strip().split()
        if parts and parts[0] in CLASS_MAP:
            parts[0] = CLASS_MAP[parts[0]]
            new_lines.append(" ".join(parts))
            
    with open(lbl_path, "w", encoding="utf-8") as f:
        f.write("\n".join(new_lines))
    fixed_count += 1

print(f"Fixed {fixed_count} label files successfully!")

# Write clean dataset.yaml
abs_root = os.path.abspath(dataset_dir).replace("\\", "/")
yaml_content = f"""path: {abs_root}
train: images/train
val: images/val

names:
  0: person
  1: backpack
  2: handbag
  3: suitcase
"""

yaml_file = os.path.join(dataset_dir, "dataset.yaml")
with open(yaml_file, "w", encoding="utf-8") as f:
    f.write(yaml_content)

print(f"Updated {yaml_file} with class names 0: person, 1: backpack, 2: handbag, 3: suitcase.")
