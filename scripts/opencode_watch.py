"""
Polling helpers for the opencode.db-wal change detector.

We don't use SQLite triggers (the running OpenCode process owns the WAL,
attaching a trigger would require RW access and would conflict). Instead we
poll the part table for new rows whose time_created is greater than the last
seen watermark, and only emit those. The watermark is persisted in a small
JSON file next to the DB.
"""
import json
import os
import sqlite3
from pathlib import Path

from opencode_db import DEFAULT_DB

WATERMARK_FILE = Path.home() / ".local" / "share" / "opencode" / ".scanner_watermark"


def _watermark_path(path: Path | None) -> Path:
    if path is None:
        return WATERMARK_FILE
    return path.parent / ".scanner_watermark"


def load_watermark(path: Path | None = None) -> int:
    """Return last seen `part.time_created` (ms). 0 if no watermark yet."""
    p = _watermark_path(path)
    if not p.exists():
        return 0
    try:
        return int(json.loads(p.read_text(encoding="utf-8")).get("ts_ms", 0))
    except (OSError, ValueError, json.JSONDecodeError):
        return 0


def save_watermark(ts_ms: int, path: Path | None = None) -> None:
    p = _watermark_path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"ts_ms": ts_ms}), encoding="utf-8")


def fetch_new_user_prompts(conn: sqlite3.Connection, since_ms: int,
                            repo_path: str) -> list[dict]:
    """Return user prompts newer than `since_ms` for this repo, oldest first."""
    sql = """
        SELECT s.id, s.model, p.id, p.time_created,
               json_extract(p.data, '$.text')
        FROM session s
        JOIN message m ON m.session_id = s.id
        JOIN part    p ON p.message_id = m.id
        WHERE (s.directory = :repo OR s.directory LIKE :repo_like)
          AND json_extract(m.data, '$.role') = 'user'
          AND json_extract(p.data, '$.type') = 'text'
          AND p.time_created > :since
        ORDER BY p.time_created ASC
    """
    cur = conn.cursor()
    cur.execute(sql, {
        "repo": repo_path,
        "repo_like": repo_path + "%",
        "since": since_ms,
    })
    out: list[dict] = []
    for sid, model_json, pid, ts_ms, text in cur.fetchall():
        if not text or len(text.strip()) < 2:
            continue
        try:
            model = json.loads(model_json).get("id", "") if model_json else ""
        except (TypeError, json.JSONDecodeError):
            model = ""
        out.append({
            "session_id": sid,
            "part_id": pid,
            "ts_ms": ts_ms,
            "text": text.strip()[:1000],
            "model": model,
        })
    return out


def open_readonly(db_path: Path | None = None) -> sqlite3.Connection:
    db = db_path or Path(os.environ.get("OPENCODE_DB", DEFAULT_DB))
    if not db.exists():
        raise FileNotFoundError(f"OpenCode DB not found: {db}")
    return sqlite3.connect(f"file:{db}?mode=ro", uri=True)
