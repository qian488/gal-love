"""SQLite schema and connection helpers."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from .tag_zh import backfill_tag_names

SCHEMA = """
CREATE TABLE IF NOT EXISTS works (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    normalized_title TEXT NOT NULL,
    original_title TEXT,
    romanized_title TEXT,
    description TEXT,
    cover_url TEXT,
    release_date TEXT,
    release_year INTEGER,
    length_minutes INTEGER,
    length_label INTEGER,
    platforms TEXT NOT NULL DEFAULT '[]',
    languages TEXT NOT NULL DEFAULT '[]',
    vndb_rating REAL,
    vndb_votecount INTEGER,
    bangumi_rating REAL,
    bangumi_votecount INTEGER,
    rating REAL,
    rating_count INTEGER,
    nsfw INTEGER NOT NULL DEFAULT 0,
    source TEXT NOT NULL DEFAULT 'manual',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_works_normalized_title ON works(normalized_title);
CREATE INDEX IF NOT EXISTS idx_works_rating ON works(rating DESC);
CREATE INDEX IF NOT EXISTS idx_works_release_year ON works(release_year);
CREATE INDEX IF NOT EXISTS idx_works_nsfw ON works(nsfw);

CREATE TABLE IF NOT EXISTS titles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    work_id INTEGER NOT NULL REFERENCES works(id) ON DELETE CASCADE,
    lang TEXT NOT NULL DEFAULT '',
    title TEXT NOT NULL,
    normalized_title TEXT NOT NULL,
    latin TEXT,
    official INTEGER NOT NULL DEFAULT 0,
    is_main INTEGER NOT NULL DEFAULT 0,
    source TEXT NOT NULL,
    UNIQUE(work_id, lang, normalized_title)
);

CREATE INDEX IF NOT EXISTS idx_titles_normalized ON titles(normalized_title);
CREATE INDEX IF NOT EXISTS idx_titles_work ON titles(work_id);

CREATE TABLE IF NOT EXISTS tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    normalized_name TEXT NOT NULL UNIQUE,
    category TEXT,
    source TEXT,
    name_zh TEXT,
    aliases TEXT
);

CREATE TABLE IF NOT EXISTS tag_aliases (
    alias_normalized TEXT PRIMARY KEY,
    tag_id INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
    lang TEXT,
    source TEXT
);

CREATE INDEX IF NOT EXISTS idx_tag_aliases_tag ON tag_aliases(tag_id);

CREATE TABLE IF NOT EXISTS work_tags (
    work_id INTEGER NOT NULL REFERENCES works(id) ON DELETE CASCADE,
    tag_id INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
    weight REAL NOT NULL DEFAULT 1.0,
    spoiler INTEGER NOT NULL DEFAULT 0,
    source TEXT NOT NULL DEFAULT 'manual',
    PRIMARY KEY(work_id, tag_id, source)
);

CREATE INDEX IF NOT EXISTS idx_work_tags_tag ON work_tags(tag_id);

CREATE TABLE IF NOT EXISTS companies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    normalized_name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS work_companies (
    work_id INTEGER NOT NULL REFERENCES works(id) ON DELETE CASCADE,
    company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    role TEXT NOT NULL DEFAULT 'developer',
    source TEXT NOT NULL DEFAULT 'manual',
    PRIMARY KEY(work_id, company_id, role, source)
);

CREATE TABLE IF NOT EXISTS external_refs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    work_id INTEGER NOT NULL REFERENCES works(id) ON DELETE CASCADE,
    source TEXT NOT NULL,
    external_id TEXT NOT NULL,
    url TEXT,
    raw_json TEXT,
    fetched_at TEXT NOT NULL,
    UNIQUE(source, external_id)
);

CREATE INDEX IF NOT EXISTS idx_external_refs_work ON external_refs(work_id);

CREATE TABLE IF NOT EXISTS my_entries (
    work_id INTEGER PRIMARY KEY REFERENCES works(id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'want',
    rating REAL,
    favorite INTEGER NOT NULL DEFAULT 0,
    notes TEXT,
    started_at TEXT,
    finished_at TEXT,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_my_entries_status ON my_entries(status);

CREATE TABLE IF NOT EXISTS feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    work_id INTEGER NOT NULL REFERENCES works(id) ON DELETE CASCADE,
    kind TEXT NOT NULL,
    note TEXT,
    created_at TEXT NOT NULL,
    UNIQUE(work_id, kind)
);

CREATE INDEX IF NOT EXISTS idx_feedback_kind ON feedback(kind);

CREATE TABLE IF NOT EXISTS recommendations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id TEXT NOT NULL,
    work_id INTEGER NOT NULL REFERENCES works(id) ON DELETE CASCADE,
    score REAL NOT NULL,
    reason TEXT,
    algorithm_version TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_recommendations_batch ON recommendations(batch_id);
CREATE INDEX IF NOT EXISTS idx_recommendations_work ON recommendations(work_id);

CREATE TABLE IF NOT EXISTS sync_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    status TEXT NOT NULL,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    stats_json TEXT,
    error TEXT
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS app_meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS merge_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id INTEGER NOT NULL,
    target_id INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    snapshot_json TEXT
);

CREATE INDEX IF NOT EXISTS idx_merge_log_source ON merge_log(source_id);
"""


def _migrate_schema(conn: sqlite3.Connection) -> None:
    """Add newer optional columns to pre-existing databases, idempotently.

    ``CREATE TABLE IF NOT EXISTS`` does not touch tables that already exist,
    so older ``data/gallove.db`` files need explicit ALTER TABLE statements.
    """
    tag_columns = {row["name"] for row in conn.execute("PRAGMA table_info(tags)")}
    if tag_columns and "name_zh" not in tag_columns:
        conn.execute("ALTER TABLE tags ADD COLUMN name_zh TEXT")
    if tag_columns and "aliases" not in tag_columns:
        conn.execute("ALTER TABLE tags ADD COLUMN aliases TEXT")


def connect(db_path: str | Path) -> sqlite3.Connection:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn


def init_db(db_path: str | Path) -> None:
    conn = connect(db_path)
    try:
        conn.executescript(SCHEMA)
        _migrate_schema(conn)
        backfill_tag_names(conn)
        conn.commit()
    finally:
        conn.close()


@contextmanager
def db_session(db_path: str | Path) -> Iterator[sqlite3.Connection]:
    conn = connect(db_path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
