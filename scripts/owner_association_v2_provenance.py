"""Create a hash-bound retrospective index for owner-association v2 runs."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "artifacts" / "owner-association-v2"
RUN_FILES = (
    "run-before.json",
    "run-after.json",
    "run-picked-up.json",
    "run-negatives.json",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    core = ROOT / "kaggle_pipeline" / "phase7c_kernel" / "phase7c_core.py"
    checkpoint = ROOT / "third_party" / "deimv2" / "ckpts" / "vitt_distill.pt"
    attempted_patch = ARTIFACTS / "attempted-fix.patch"
    git_head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=False
    ).stdout.strip()
    records = []
    for name in RUN_FILES:
        run_path = ARTIFACTS / name
        manifest = json.loads(run_path.read_text(encoding="utf-8"))
        prediction = ROOT / manifest["predictions_path"]
        records.append({
            "run_manifest": str(run_path.relative_to(ROOT)),
            "run_manifest_sha256": sha256(run_path),
            "prediction": str(prediction.relative_to(ROOT)),
            "prediction_sha256": sha256(prediction),
            "prediction_hash_matches_manifest": (
                sha256(prediction) == manifest["predictions_sha256"]
            ),
        })
    payload = {
        "capture_mode": "retrospective_after_scoring_rollback",
        "limitation": (
            "Run artifacts are hash-bound here, but attempted-fix source identity was not captured "
            "at execution time. attempted-fix.patch records the exact rejected scoring delta."
        ),
        "git_head_at_index_creation": git_head,
        "current_rolled_back_core_sha256": sha256(core),
        "attempted_fix_patch_sha256": sha256(attempted_patch),
        "checkpoint_sha256": sha256(checkpoint),
        "runs": records,
    }
    output = ARTIFACTS / "provenance.json"
    output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
