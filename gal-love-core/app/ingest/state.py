"""Incremental sync cursors and entry classification.

State is stored as key/value rows in ``app_meta`` so that no schema change or
repository.py modification is required.  Cursor keys are stable and documented:

    vndb.last_fetch_at
    vndb.last_max_votecount
    bangumi.last_fetch_at
    bangumi.last_max_votecount
"""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from ..normalize import json_loads, now_iso

# Public cursor keys (also handy for tests / debugging via ``app_meta``).
KEY_VNDB_LAST_FETCH_AT = "vndb.last_fetch_at"
KEY_VNDB_LAST_MAX_VOTECOUNT = "vndb.last_max_votecount"
KEY_BANGUMI_LAST_FETCH_AT = "bangumi.last_fetch_at"
KEY_BANGUMI_LAST_MAX_VOTECOUNT = "bangumi.last_max_votecount"

_ALLOWED_FIELDS: dict[str, tuple[str, ...]] = {
    "vndb": ("last_fetch_at", "last_max_votecount"),
    "bangumi": ("last_fetch_at", "last_max_votecount"),
}


def get_meta(conn: sqlite3.Connection, key: str, default: Any = None) -> Any:
    row = conn.execute("SELECT value FROM app_meta WHERE key = ?", (key,)).fetchone()
    if row is None:
        return default
    return json_loads(row["value"], row["value"])


def set_meta(conn: sqlite3.Connection, key: str, value: Any) -> None:
    conn.execute(
        "INSERT INTO app_meta(key, value) VALUES(?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, json.dumps(value, ensure_ascii=False)),
    )
    conn.commit()


def delete_meta(conn: sqlite3.Connection, key: str) -> None:
    conn.execute("DELETE FROM app_meta WHERE key = ?", (key,))
    conn.commit()


def load_cursor(conn: sqlite3.Connection, source: str) -> dict[str, Any]:
    """Return the persisted cursor for *source* (empty dict on first run)."""
    cursor: dict[str, Any] = {}
    for field in _ALLOWED_FIELDS.get(source, ()):
        value = get_meta(conn, f"{source}.{field}")
        if value is not None:
            cursor[field] = value
    return cursor


def save_cursor(conn: sqlite3.Connection, source: str, cursor: dict[str, Any]) -> None:
    """Persist cursor fields; unknown fields are ignored."""
    for field in _ALLOWED_FIELDS.get(source, ()):
        if field in cursor and cursor[field] is not None:
            set_meta(conn, f"{source}.{field}", cursor[field])


def reset_cursor(conn: sqlite3.Connection, source: str) -> None:
    for field in _ALLOWED_FIELDS.get(source, ()):
        delete_meta(conn, f"{source}.{field}")


def fingerprint(value: Any) -> str:
    """Stable representation of raw API payloads for change detection."""
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def classify_entry(
    conn: sqlite3.Connection, source: str, external_id: Any, raw: dict[str, Any]
) -> tuple[str, str | None]:
    """Classify a fetched entry as ``new`` / ``updated`` / ``unchanged``.

    Returns a ``(status, previous_fetched_at)`` tuple.  ``previous_fetched_at``
    comes from ``external_refs`` and is compared with the local cursor by the
    importer when deciding whether a page can be skipped early.
    """
    row = conn.execute(
        "SELECT raw_json, fetched_at FROM external_refs WHERE source = ? AND external_id = ?",
        (source, str(external_id)),
    ).fetchone()
    if row is None:
        return "new", None
    stored = fingerprint(json_loads(row["raw_json"], None))
    if stored == fingerprint(raw):
        return "unchanged", row["fetched_at"]
    return "updated", row["fetched_at"]


def cursor_time() -> str:
    """Current UTC timestamp used when advancing cursors (monkeypatch-friendly)."""
    return now_iso()
