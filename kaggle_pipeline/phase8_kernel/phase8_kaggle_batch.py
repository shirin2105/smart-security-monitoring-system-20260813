from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path


INPUT = Path("/kaggle/input")
OUTPUT = Path(os.environ.get("PHASE8_OUT_ROOT", "/kaggle/working/phase8_predictions"))


def materialize_code_bundle(input_root: Path = INPUT, work_root: Path | None = None) -> Path:
    matches = sorted(input_root.rglob("phase8_code_bundle.zip"))
    expanded = sorted(input_root.rglob("tools/phase8/phase8_batch_runner.py"))
    if len(expanded) == 1 and not matches:
        root = expanded[0].parents[2]
        if not (root / "phase8_tracker_wrapper.py").is_file():
            raise RuntimeError(f"Expanded Phase 8 bundle is incomplete: {root}")
        return root
    if len(matches) == 1 and not expanded:
        destination = work_root or Path("/kaggle/working/phase8_code")
        if destination.exists():
            shutil.rmtree(destination)
        shutil.unpack_archive(str(matches[0]), str(destination))
        return destination
    preview = "\n".join(str(path) for path in [*matches, *expanded][:20])
    raise RuntimeError(
        f"Expected exactly one zipped or expanded Phase 8 code bundle; "
        f"found zip={len(matches)} expanded={len(expanded)}\n{preview}"
    )


def unique_file(name: str, code_root: Path) -> Path:
    roots = [code_root, INPUT]
    matches = sorted({path.resolve() for root in roots for path in root.rglob(name)})
    if len(matches) != 1:
        preview = "\n".join(str(path) for path in matches[:20])
        raise RuntimeError(f"Expected exactly one {name}; found {len(matches)}\n{preview}")
    return matches[0]


def build_inference_template(inference: Path, tracker_template: str) -> str:
    nested_tracker = tracker_template.replace("{", "{{").replace("}", "}}")
    return (
        f"{sys.executable} {inference} --video {{video_path}} --clip-id {{clip_id}} "
        "--camera-id {camera_id} --camera-config {camera_config_path} "
        "--out {pred_path} --work-dir {clip_out_dir} "
        f"--tracker-cmd-template {nested_tracker!r}"
    )


def main() -> None:
    subprocess.run([sys.executable, "-m", "pip", "install", "-q",
                    "pydantic>=2.10", "shapely>=2.0"], check=True)
    code_root = materialize_code_bundle()
    manifest = Path(os.environ["PHASE8_MANIFEST"]) if os.environ.get("PHASE8_MANIFEST") else unique_file("manifest.json", code_root)
    runner = Path(os.environ["PHASE8_BATCH_RUNNER"]) if os.environ.get("PHASE8_BATCH_RUNNER") else unique_file("phase8_batch_runner.py", code_root)
    inference = Path(os.environ["PHASE8_INFERENCE_VIDEO"]) if os.environ.get("PHASE8_INFERENCE_VIDEO") else unique_file("inference_video.py", code_root)
    tracker_wrapper = unique_file("phase8_tracker_wrapper.py", code_root)
    tracker_template = os.environ.get("PHASE8_TRACKER_CMD") or (
        f"{sys.executable} {tracker_wrapper} --video {{video}} --tracks {{tracks}} "
        "--work-dir {work_dir} --inference-profile {inference_profile}"
    )
    inference_template = build_inference_template(inference, tracker_template)
    command = [sys.executable, str(runner), "--manifest", str(manifest),
               "--out-root", str(OUTPUT), "--infer-cmd-template", inference_template]
    print("$", " ".join(command), flush=True)
    subprocess.run(command, check=True)
    print("PHASE8 BATCH COMPLETE", flush=True)


if __name__ == "__main__":
    main()
