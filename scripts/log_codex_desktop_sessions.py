#!/usr/bin/env python3
"""Mirror user prompts from local Codex Desktop transcripts into .ai-log."""

import argparse
import json
import os
import re
import subprocess
import time
from datetime import datetime
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SESSIONS_ROOT = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")) / "sessions"
LOG_DIR = Path(os.environ.get("AI_LOG_DIR", REPO_ROOT / ".ai-log"))
LOG_FILE = LOG_DIR / "session.jsonl"
SECRET_PATTERNS = (
    re.compile(r"\bhf_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\bai20k_[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\bKGAT_[A-Za-z0-9_-]{20,}\b"),
)
INTERNAL_REVIEW_PREFIXES = (
    "The following is the Codex agent history whose request action you are assessing.",
    "The following is the Codex agent history added since your last approval assessment.",
)


def is_internal_review_prompt(text: str) -> bool:
    """Exclude approval-review envelopes that are not authored by the user."""
    return text.startswith(INTERNAL_REVIEW_PREFIXES)


def redact_secrets(text: str) -> str:
    """Keep prompt context while excluding common API-token formats from AI usage logs."""
    for pattern in SECRET_PATTERNS:
        text = pattern.sub("[REDACTED_API_TOKEN]", text)
    return text


def normalized(path: str) -> str:
    return os.path.normcase(os.path.normpath(path))


def git(*args: str) -> str:
    try:
        result = subprocess.run(["git", *args], cwd=REPO_ROOT, text=True,
                                capture_output=True, check=False)
        return result.stdout.strip()
    except OSError:
        return ""


def logged_ids() -> set[str]:
    if not LOG_FILE.exists():
        return set()
    ids = set()
    for line in LOG_FILE.read_text(encoding="utf-8").splitlines():
        try:
            entry_id = json.loads(line).get("entry_id")
            if entry_id:
                ids.add(entry_id)
        except json.JSONDecodeError:
            continue
    return ids


def sanitize_existing_log() -> int:
    """Redact tokens that may have been written by older logger versions."""
    if not LOG_FILE.exists():
        return 0
    changed = 0
    sanitized_lines = []
    for line in LOG_FILE.read_text(encoding="utf-8").splitlines():
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            sanitized_lines.append(line)
            continue
        for field in ("prompt", "response_summary"):
            value = entry.get(field)
            if isinstance(value, str):
                redacted = redact_secrets(value)
                changed += redacted != value
                entry[field] = redacted
        sanitized_lines.append(json.dumps(entry, ensure_ascii=False))
    if changed:
        LOG_FILE.write_text("\n".join(sanitized_lines) + "\n", encoding="utf-8")
    return changed


def transcript_prompts() -> list[dict]:
    repo = normalized(str(REPO_ROOT))
    prompts = []
    for transcript in SESSIONS_ROOT.rglob("*.jsonl"):
        session_id = ""
        cwd = ""
        try:
            with transcript.open(encoding="utf-8", errors="replace") as stream:
                for line_number, line in enumerate(stream):
                    try:
                        record = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    payload = record.get("payload", {})
                    if record.get("type") == "session_meta":
                        session_id = payload.get("session_id", "")
                        cwd = payload.get("cwd", "")
                        continue
                    if normalized(cwd) != repo or record.get("type") != "response_item":
                        continue
                    if payload.get("role") != "user":
                        continue
                    content = payload.get("content", [])
                    text = "\n".join(
                        item.get("text", "") for item in content
                        if item.get("type") == "input_text"
                    ).strip()
                    if not text or "<environment_context>" in text or is_internal_review_prompt(text):
                        continue
                    message_id = payload.get("id") or str(line_number)
                    prompts.append({
                        "entry_id": f"codex-desktop-{session_id}-{message_id}",
                        "ts": record.get("timestamp") or datetime.now().astimezone().isoformat(),
                        "session_id": session_id,
                        "prompt": redact_secrets(text),
                    })
        except OSError:
            continue
    return prompts


def scan() -> int:
    sanitize_existing_log()
    known = logged_ids()
    new_entries = [entry for entry in transcript_prompts() if entry["entry_id"] not in known]
    if not new_entries:
        return 0
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    common = {
        "tool": "codex",
        "event": "TranscriptUserPrompt",
        "model": "",
        "repo": git("remote", "get-url", "origin").split("/")[-1].removesuffix(".git") or REPO_ROOT.name,
        "branch": git("rev-parse", "--abbrev-ref", "HEAD"),
        "commit": git("rev-parse", "--short", "HEAD"),
        "student": git("config", "user.email"),
    }
    with LOG_FILE.open("a", encoding="utf-8") as output:
        for entry in new_entries:
            output.write(json.dumps(common | entry, ensure_ascii=False) + "\n")
    return len(new_entries)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--watch", action="store_true")
    parser.add_argument("--interval", type=float, default=3.0)
    args = parser.parse_args()
    while True:
        count = scan()
        if count:
            print(f"[ai-log] Logged {count} Codex Desktop prompt(s).", flush=True)
        if not args.watch:
            return
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
