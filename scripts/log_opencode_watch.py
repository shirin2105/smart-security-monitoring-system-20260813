#!/usr/bin/env python3
"""
OpenCode live watcher — polls the opencode.db WAL for new user prompts and
appends them to .ai-log/session.jsonl in real time. Analogous to the native
hooks Claude Code / Gemini / Codex / Cursor use: capture prompts as the user
types them, no git push required.

State:
  ~/.local/share/opencode/.scanner_watermark
      Last seen `part.time_created` (ms). Survives restarts so the watcher
      resumes from where it left off and never re-emits the same prompt.

Usage:
  python scripts/log_opencode_watch.py --once     # process pending, then exit
  python scripts/log_opencode_watch.py            # poll every --interval seconds
  python scripts/log_opencode_watch.py --interval 2

Stop with Ctrl-C. Each tick: open DB RO, fetch new user prompts > watermark,
append to log, advance watermark. Idempotent against the log file (uses the
same opencode-{part_id} entry_id format as log_opencode.py).
"""
import argparse
import json
import os
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from opencode_db import DEFAULT_DB
from opencode_watch import (
    fetch_new_user_prompts,
    load_watermark,
    save_watermark,
)

VN_TZ = timezone(timedelta(hours=7))
_running = True


def git(cmd: str) -> str:
    try:
        return subprocess.check_output(
            cmd.split(), shell=False, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except Exception:
        return ""


def _stop(_signum, _frame):
    global _running
    _running = False


def emit(prompts: list[dict], repo: str, branch: str, commit: str,
         student: str) -> int:
    """Append new entries to .ai-log/session.jsonl. Returns count written."""
    if not prompts:
        return 0
    log_dir = Path(os.environ.get("AI_LOG_DIR", ".ai-log"))
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / "session.jsonl"
    with open(log_file, "a", encoding="utf-8") as f:
        for p in prompts:
            ts = datetime.fromtimestamp(p["ts_ms"] / 1000, tz=VN_TZ).isoformat()
            entry = {
                "ts": ts,
                "tool": "opencode",
                "event": "UserPrompt",
                "entry_id": f"opencode-{p['part_id']}",
                "session_id": p["session_id"],
                "model": p["model"],
                "repo": repo,
                "branch": branch,
                "commit": commit,
                "student": student,
                "prompt": p["text"],
                "response_summary": "",
            }
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return len(prompts)


def tick(db_path: Path, repo_root: str, repo: str, branch: str,
         commit: str, student: str) -> int:
    """One poll iteration. Returns number of new entries written."""
    from opencode_watch import open_readonly
    try:
        conn = open_readonly(db_path)
    except FileNotFoundError:
        return 0
    try:
        wm = load_watermark(db_path)
        new = fetch_new_user_prompts(conn, wm, repo_root)
    finally:
        conn.close()
    if not new:
        return 0
    n = emit(new, repo, branch, commit, student)
    save_watermark(new[-1]["ts_ms"], db_path)
    print(f"[opencode-watch] +{n} prompt(s) at {datetime.now(VN_TZ).isoformat(timespec='seconds')}",
          file=sys.stderr)
    return n


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Watch opencode.db for new user prompts, write to .ai-log/."
    )
    parser.add_argument("--once", action="store_true",
                        help="Process pending prompts once, then exit.")
    parser.add_argument("--interval", type=float, default=3.0,
                        help="Poll interval in seconds (default: 3).")
    parser.add_argument("--no-repo-filter", action="store_true",
                        help="Don't filter sessions by current repo.")
    parser.add_argument("--db", help="Path to opencode.db (overrides env/default).")
    args = parser.parse_args()

    db_path = Path(args.db) if args.db else Path(
        os.environ.get("OPENCODE_DB", DEFAULT_DB)
    )
    if not db_path.exists():
        print(f"[opencode-watch] {db_path} not found — nothing to watch.",
              file=sys.stderr)
        sys.exit(0)

    repo_root = "" if args.no_repo_filter else str(Path.cwd())
    repo = git("git remote get-url origin").split("/")[-1].replace(".git", "")
    if not repo and not args.no_repo_filter:
        repo = Path.cwd().name
    branch = git("git rev-parse --abbrev-ref HEAD")
    commit = git("git rev-parse --short HEAD")
    student = git("git config user.email") or os.environ.get(
        "USERNAME", os.environ.get("USER", "unknown"))

    if args.once:
        n = tick(db_path, repo_root, repo, branch, commit, student)
        if n:
            print(f"[opencode-watch] Flushed {n} pending prompt(s).", file=sys.stderr)
        return

    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)
    print(f"[opencode-watch] Watching {db_path} every {args.interval}s "
          f"(repo={repo or '*'}, Ctrl-C to stop).", file=sys.stderr)

    while _running:
        try:
            tick(db_path, repo_root, repo, branch, commit, student)
        except sqlite3.Error as e:
            print(f"[opencode-watch] DB error: {e} (will retry).", file=sys.stderr)
        # Sleep in small slices so SIGTERM responds fast
        end = time.time() + args.interval
        while _running and time.time() < end:
            time.sleep(0.1)

    print("[opencode-watch] Stopped.", file=sys.stderr)


if __name__ == "__main__":
    main()
