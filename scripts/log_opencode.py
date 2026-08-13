#!/usr/bin/env python3
"""
OpenCode log scanner — extracts user prompts from the local OpenCode SQLite DB
and writes them to .ai-log/session.jsonl.

Source of truth:
    ~/.local/share/opencode/opencode.db (read-only, WAL-safe via URI mode)

A user prompt is a row in `part` with `type="text"` joined to a `message` with
`role="user"`, in a `session` whose `directory` matches the current repo.

Env overrides:
  OPENCODE_DB           path to opencode.db (default: ~/.local/share/.../opencode.db)
  AI_LOG_DIR            where session.jsonl is written (default: .ai-log)

Usage:
  python scripts/log_opencode.py --auto            # default: last 24h
  python scripts/log_opencode.py --hours 72
  python scripts/log_opencode.py --all             # every session, no cutoff
  python scripts/log_opencode.py --session <id>    # one session
  python scripts/log_opencode.py --dry-run         # preview only
"""
import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from opencode_db import open_db, iter_user_prompts

VN_TZ = timezone(timedelta(hours=7))


def git(cmd: str) -> str:
    try:
        return subprocess.check_output(
            cmd.split(), shell=False, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except Exception:
        return ""


def get_logged_ids(log_file: Path) -> set[str]:
    ids: set[str] = set()
    if not log_file.exists():
        return ids
    with open(log_file, encoding="utf-8-sig") as f:
        for line in f:
            try:
                ids.add(json.loads(line).get("entry_id", ""))
            except json.JSONDecodeError:
                continue
    return {i for i in ids if i}


def build_entry(prompt: dict, repo: str, branch: str, commit: str,
                student: str) -> dict:
    ts = datetime.fromtimestamp(prompt["ts_ms"] / 1000, tz=VN_TZ).isoformat()
    return {
        "ts": ts,
        "tool": "opencode",
        "event": "UserPrompt",
        "entry_id": f"opencode-{prompt['part_id']}",
        "session_id": prompt["session_id"],
        "model": prompt["model"],
        "repo": repo,
        "branch": branch,
        "commit": commit,
        "student": student,
        "prompt": prompt["text"],
        "response_summary": "",
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract OpenCode user prompts into .ai-log/session.jsonl."
    )
    parser.add_argument("--auto", action="store_true",
                        help="Default mode: scan recent prompts (last --hours).")
    parser.add_argument("--hours", type=int, default=24,
                        help="Window in hours (default: 24).")
    parser.add_argument("--all", action="store_true",
                        help="Ignore the time window.")
    parser.add_argument("--session", help="Limit to a single session id.")
    parser.add_argument("--no-repo-filter", action="store_true",
                        help="Don't filter sessions by current repo.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview only, don't write.")
    args = parser.parse_args()

    log_dir = Path(os.environ.get("AI_LOG_DIR", ".ai-log"))
    log_file = log_dir / "session.jsonl"
    log_dir.mkdir(exist_ok=True)
    logged = get_logged_ids(log_file)

    repo_root = "" if args.no_repo_filter else str(Path.cwd())
    repo = git("git remote get-url origin").split("/")[-1].replace(".git", "")
    if not repo and not args.no_repo_filter:
        repo = Path.cwd().name
    branch = git("git rev-parse --abbrev-ref HEAD")
    commit = git("git rev-parse --short HEAD")
    student = git("git config user.email") or os.environ.get(
        "USERNAME", os.environ.get("USER", "unknown"))

    cutoff_ms = None if args.all else int(
        (datetime.now(tz=VN_TZ) - timedelta(hours=args.hours)).timestamp() * 1000
    )

    try:
        conn = open_db()
    except FileNotFoundError as e:
        print(f"[opencode-log] {e} — skipping.", file=sys.stderr)
        sys.exit(0)

    try:
        new_entries: list[dict] = []
        for p in iter_user_prompts(conn, repo_root, cutoff_ms, args.session):
            entry = build_entry(p, repo, branch, commit, student)
            if entry["entry_id"] in logged:
                continue
            new_entries.append(entry)
            logged.add(entry["entry_id"])
    finally:
        conn.close()

    if not new_entries:
        scope = "all" if args.all else f"{args.hours}h"
        print(f"[opencode-log] No new prompts (window={scope}).", file=sys.stderr)
        sys.exit(0)

    if args.dry_run:
        print(f"\n[opencode-log] DRY RUN — would log {len(new_entries)} entries:\n")
        for e in new_entries:
            preview = e["prompt"].replace("\n", " ")[:120]
            print(f"  [{e['ts'][:19]}] {preview}")
        sys.exit(0)

    with open(log_file, "a", encoding="utf-8") as f:
        for e in new_entries:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")

    print(f"[opencode-log] Logged {len(new_entries)} prompt(s) from OpenCode.",
          file=sys.stderr)


if __name__ == "__main__":
    main()
