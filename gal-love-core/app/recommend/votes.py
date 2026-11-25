"""VNDB votes dump import into an independent SQLite database.

The votes database is deliberately kept separate from the main library database so
that Phase 3 never changes the main schema. A dump line looks like::

    v123 u456 80 2020-01-01

Scores are stored normalized to 0..1 (VNDB uses a 0..100 scale).
"""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path

from ..db import connect

VOTES_DB_NAME = "votes.db"
VOTE_SCALE = 100.0

SCHEMA = """
CREATE TABLE IF NOT EXISTS votes (
    user_id  INTEGER NOT NULL,
    vndb_id  INTEGER NOT NULL,
    score    REAL NOT NULL CHECK(score >= 0.0 AND score <= 1.0),
    voted_at TEXT,
    PRIMARY KEY (user_id, vndb_id)
);
CREATE INDEX IF NOT EXISTS idx_votes_vndb ON votes(vndb_id);
CREATE INDEX IF NOT EXISTS idx_votes_user ON votes(user_id);

CREATE TABLE IF NOT EXISTS vote_items (
    vndb_id    INTEGER PRIMARY KEY,
    vote_count INTEGER NOT NULL,
    mean_score REAL NOT NULL
);
"""

# Both space and tab separated dumps are accepted; the date column is optional.
_VOTE_LINE = re.compile(
    r"^\s*v(?P<vndb>\d+)\s+u(?P<user>\d+)\s+(?P<score>\d{1,3}(?:\.\d+)?)(?:\s+(?P<date>\S+))?\s*$"
)


def votes_db_path(db_path: Path | str) -> Path:
    """Return the default votes database path for a main database path.

    ``<data>/gallove.db`` -> ``<data>/votes.db``. If a directory is passed, the
    votes database is placed directly inside it.
    """
    path = Path(db_path).expanduser()
    parent = path if path.is_dir() or not path.name else path.parent
    return (parent / VOTES_DB_NAME).resolve() if path.is_absolute() else parent / VOTES_DB_NAME


def init_votes_db(path: Path | str) -> Path:
    """Create the votes schema (idempotent) and return the database path."""
    target = Path(path).expanduser()
    connection = connect(target)
    try:
        connection.executescript(SCHEMA)
        connection.commit()
    finally:
        connection.close()
    return target


def _target_votes_db(db_path: Path | str) -> Path:
    """Resolve a votes database path, never writing votes into the main library."""
    path = Path(db_path).expanduser()
    if path.is_dir():
        return path / VOTES_DB_NAME
    if path.is_file() and path.name != VOTES_DB_NAME:
        connection: sqlite3.Connection | None = None
        try:
            connection = sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)
            is_main = connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'works'"
            ).fetchone()
            if is_main:
                return votes_db_path(path)
        except sqlite3.Error:
            pass
        finally:
            if connection is not None:
                connection.close()
    return path


def parse_vote_line(line: str) -> tuple[int, int, float, str | None] | None:
    """Parse one votes.txt line; return ``(vndb_id, user_id, score, date)``.

    Returns ``None`` for comments, blank lines and malformed rows.
    """
    text = line.strip()
    if not text or text.startswith("--"):
        return None
    # Inline comments are rare but harmless to strip.
    text = text.split("--", 1)[0].strip()
    match = _VOTE_LINE.match(text)
    if not match:
        return None
    raw_score = float(match.group("score"))
    if not 0.0 <= raw_score <= VOTE_SCALE:
        return None
    date = match.group("date")
    return (
        int(match.group("vndb")),
        int(match.group("user")),
        round(raw_score / VOTE_SCALE, 4),
        date or None,
    )


def import_votes_dump(
    dump_path: Path | str,
    db_path: Path | str,
    *,
    min_votes: int = 10,
    limit: int | None = None,
) -> dict:
    """Import a VNDB votes dump into ``db_path`` (a votes database).

    Rows are deduplicated by ``(user_id, vndb_id)`` (last occurrence wins) and
    grouped by ``vndb_id``. Only works with at least ``min_votes`` distinct
    voters are imported. Works are taken in descending vote-count order until
    ``limit`` vote rows have been stored; ``limit=None`` means no cap.

    ``vote_items`` keeps the per-work aggregate (count and mean score).
    """
    source = Path(dump_path).expanduser()
    if not source.is_file():
        raise FileNotFoundError(f"votes dump not found: {source}")

    target = _target_votes_db(db_path)

    by_work: dict[int, dict[int, tuple[float, str | None]]] = {}
    lines = parsed = skipped = comments = 0
    with source.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            lines += 1
            text = line.strip()
            if not text:
                continue
            if text.startswith("--"):
                comments += 1
                continue
            parsed_row = parse_vote_line(line)
            if parsed_row is None:
                skipped += 1
                continue
            parsed += 1
            vndb_id, user_id, score, voted_at = parsed_row
            bucket = by_work.setdefault(vndb_id, {})
            bucket[user_id] = (score, voted_at)

    threshold = max(0, int(min_votes))
    eligible = sorted(
        ((vndb_id, users) for vndb_id, users in by_work.items() if len(users) >= threshold),
        key=lambda item: (-len(item[1]), item[0]),
    )

    rows: list[tuple[int, int, float, str | None]] = []
    for vndb_id, users in eligible:
        work_rows = [
            (vndb_id, user_id, score, voted_at)
            for user_id, (score, voted_at) in sorted(users.items())
        ]
        if limit is not None and len(rows) + len(work_rows) > limit:
            continue
        rows.extend(work_rows)
        if limit is not None and len(rows) >= limit:
            break

    init_votes_db(target)
    connection = connect(target)
    try:
        connection.executemany(
            "INSERT INTO votes(user_id, vndb_id, score, voted_at) VALUES(?, ?, ?, ?) "
            "ON CONFLICT(user_id, vndb_id) DO UPDATE SET score = excluded.score, voted_at = excluded.voted_at",
            [(user_id, vndb_id, score, voted_at) for vndb_id, user_id, score, voted_at in rows],
        )
        connection.execute("DELETE FROM vote_items")
        connection.execute(
            """
            INSERT INTO vote_items(vndb_id, vote_count, mean_score)
            SELECT vndb_id, COUNT(*), AVG(score) FROM votes GROUP BY vndb_id
            """
        )
        connection.commit()
    finally:
        connection.close()

    imported_users = {user_id for _, user_id, _, _ in rows}
    return {
        "dump": str(source),
        "db": str(target),
        "lines": lines,
        "parsed": parsed,
        "skipped": skipped,
        "comments": comments,
        "min_votes": threshold,
        "limit": limit,
        "candidates": len(eligible),
        "items_imported": len({vndb_id for vndb_id, _, _, _ in rows}),
        "votes_imported": len(rows),
        "imported": len(rows),
        "users": len(imported_users),
    }


def get_votes_stats(db_path: Path | str) -> dict:
    """Return votes database statistics; zeros when the database is absent."""
    target = _target_votes_db(db_path)
    stats: dict = {
        "path": str(target),
        "available": False,
        "votes": 0,
        "users": 0,
        "items": 0,
        "mean_score": None,
        "min_vote_count": 0,
        "max_vote_count": 0,
    }
    if not target.is_file():
        return stats
    connection: sqlite3.Connection | None = None
    try:
        connection = sqlite3.connect(str(target))
        connection.row_factory = sqlite3.Row
        row = connection.execute(
            "SELECT COUNT(*) AS votes, COUNT(DISTINCT user_id) AS users, AVG(score) AS mean_score FROM votes"
        ).fetchone()
        item_row = connection.execute(
            "SELECT COUNT(*) AS items, MIN(vote_count) AS min_count, MAX(vote_count) AS max_count FROM vote_items"
        ).fetchone()
        stats.update(
            {
                "available": True,
                "votes": int(row["votes"] or 0),
                "users": int(row["users"] or 0),
                "items": int(item_row["items"] or 0),
                "mean_score": round(float(row["mean_score"]), 4) if row["mean_score"] is not None else None,
                "min_vote_count": int(item_row["min_count"] or 0),
                "max_vote_count": int(item_row["max_count"] or 0),
            }
        )
    except sqlite3.Error:
        pass
    finally:
        if connection is not None:
            connection.close()
    return stats


def has_votes(db_path: Path | str) -> bool:
    """True when a usable votes database exists at ``db_path``."""
    return get_votes_stats(db_path)["votes"] > 0
