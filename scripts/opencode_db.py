"""
OpenCode SQLite helpers — read-only access to ~/.local/share/opencode/opencode.db.

OpenCode stores sessions in a Drizzle/SQLite DB. Each user prompt is split
across three tables: `session` (cwd + model), `message` (role + parent chain),
`part` (the actual text content with `type="text"`). This module hides the
JOIN behind a single generator.
"""
import json
import os
import sqlite3
from pathlib import Path

DEFAULT_DB = Path.home() / ".local" / "share" / "opencode" / "opencode.db"


def open_db(path: Path | None = None) -> sqlite3.Connection:
    """Open the OpenCode DB read-only. Uses a URI so we never lock against the
    running OpenCode process even when it has the WAL handle."""
    db = path or Path(os.environ.get("OPENCODE_DB", DEFAULT_DB))
    if not db.exists():
        raise FileNotFoundError(f"OpenCode DB not found: {db}")
    uri = f"file:{db}?mode=ro"
    return sqlite3.connect(uri, uri=True)


def iter_user_prompts(conn: sqlite3.Connection, repo_path: str,
                      cutoff_ms: int | None,
                      only_session: str | None) -> dict:
    """Yield dicts {session_id, ts_ms, part_id, text, model} for every user
    prompt that belongs to `repo_path` (matched as session.directory prefix).

    cutoff_ms is an inclusive lower bound on time_created (Unix ms)."""
    sql = """
        SELECT s.id, s.model, p.id, p.time_created,
               json_extract(p.data, '$.text')
        FROM session s
        JOIN message m ON m.session_id = s.id
        JOIN part    p ON p.message_id = m.id
        WHERE (s.directory = :repo OR s.directory LIKE :repo_like)
          AND json_extract(m.data, '$.role') = 'user'
          AND json_extract(p.data, '$.type') = 'text'
          AND (:only IS NULL OR s.id = :only)
          AND (:cutoff IS NULL OR p.time_created >= :cutoff)
        ORDER BY s.time_created ASC, p.time_created ASC
    """
    params = {
        "repo": repo_path,
        "repo_like": repo_path + "%",
        "only": only_session,
        "cutoff": cutoff_ms,
    }
    cur = conn.cursor()
    cur.execute(sql, params)
    for sid, model_json, pid, ts_ms, text in cur.fetchall():
        if not text or len(text.strip()) < 2:
            continue
        try:
            model = json.loads(model_json).get("id", "") if model_json else ""
        except (TypeError, json.JSONDecodeError):
            model = ""
        yield {
            "session_id": sid,
            "part_id": pid,
            "ts_ms": ts_ms,
            "text": text.strip()[:1000],
            "model": model,
        }
