"""Run Phase 6 training and evaluation sequentially in one Kaggle session."""

import runpy
from pathlib import Path


INPUT = Path("/kaggle/input")


def run_script(name: str) -> None:
    matches = list(INPUT.rglob(name))
    if len(matches) != 1:
        raise FileNotFoundError(
            f"Expected exactly one {name} in Kaggle Input; found {len(matches)}: "
            + ", ".join(map(str, matches[:20]))
        )
    path = matches[0]
    print(f"\n[PHASE6 LAUNCHER] running {path.name}", flush=True)
    runpy.run_path(str(path), run_name="__main__")


run_script("phase6_01_train_ecdet_visdrone.py")
run_script("phase6_02_eval_ecdet_vs_deim.py")
