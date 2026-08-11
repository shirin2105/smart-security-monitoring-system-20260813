from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.evaluation.phase7c_candidate_metrics import evaluate_phase7c_candidates


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate Phase 7C candidate events")
    parser.add_argument("--events", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    events = json.loads(args.events.read_text(encoding="utf-8"))
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    if not isinstance(events, list):
        raise ValueError("events JSON must be a list")
    report = evaluate_phase7c_candidates(events, manifest)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(report["overall"], indent=2))


if __name__ == "__main__":
    main()
