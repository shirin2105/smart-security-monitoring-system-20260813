from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.evaluation.phase8_config import load_json, validate_manifest


def _resolve(value: str, base: Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (base / path).resolve()


def run(args: argparse.Namespace) -> list[dict]:
    manifest_path = args.manifest.resolve()
    clips = validate_manifest(load_json(manifest_path), not args.allow_small_manifest)
    output_root = args.out_root.resolve(); output_root.mkdir(parents=True, exist_ok=True)
    status = []
    for clip in clips:
        clip_dir = output_root / str(clip["clip_id"]); clip_dir.mkdir(parents=True, exist_ok=True)
        pred_path = clip_dir / "pred_events.jsonl"
        fields = {
            "clip_id": str(clip["clip_id"]),
            "video_path": str(_resolve(clip["video_path"], manifest_path.parent)),
            "camera_id": str(clip["camera_id"]),
            "camera_config_path": str(_resolve(clip["camera_config_path"], manifest_path.parent)),
            "pred_path": str(pred_path), "clip_out_dir": str(clip_dir),
        }
        command = shlex.split(args.infer_cmd_template.format(**fields))
        print(f"\n[PHASE8] {fields['clip_id']}\n$ {shlex.join(command)}", flush=True)
        try:
            subprocess.run(command, check=True)
            summary_path = clip_dir / "phase8_runtime_summary.json"
            if not summary_path.is_file():
                raise RuntimeError(f"missing runtime summary: {summary_path}")
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            duration_s = float(summary.get("processed_duration_s", 0))
            if duration_s <= 0:
                raise RuntimeError(f"invalid processed duration: {fields['clip_id']}")
            status.append({"clip_id": fields["clip_id"], "ok": True,
                           "pred_path": str(pred_path), "processed_duration_s": duration_s})
        except (subprocess.CalledProcessError, RuntimeError) as error:
            status.append({"clip_id": fields["clip_id"], "ok": False,
                           "returncode": getattr(error, "returncode", None), "error": str(error)})
            if not args.continue_on_error:
                raise
        (output_root / "batch_status.json").write_text(
            json.dumps(status, indent=2), encoding="utf-8")
    merged = output_root / "predictions_all.jsonl"
    with merged.open("w", encoding="utf-8") as destination:
        for row in status:
            if not row.get("ok"):
                continue
            text = Path(row["pred_path"]).read_text(encoding="utf-8")
            if text:
                destination.write(text.rstrip("\n") + "\n")
    failures = [row for row in status if not row.get("ok")]
    if failures:
        raise RuntimeError(f"Phase 8 batch failed for {len(failures)}/{len(status)} clips")
    print(f"[PHASE8] merged={merged}")
    return status


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Phase 8 inference over a validated manifest")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--out-root", type=Path, required=True)
    parser.add_argument("--infer-cmd-template", required=True)
    parser.add_argument("--continue-on-error", action="store_true")
    parser.add_argument("--allow-small-manifest", action="store_true",
                        help="Only for unit/smoke tests; production Phase 8 requires 20-30 clips")
    return parser.parse_args()


if __name__ == "__main__":
    run(parse_args())
