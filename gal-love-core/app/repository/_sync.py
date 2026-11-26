"""Sync run, recommendation cache and stats helpers."""

from __future__ import annotations

import sqlite3
import uuid
from typing import Any

from ..normalize import json_dumps, json_loads, now_iso


def start_sync_run(conn: sqlite3.Connection, source: str) -> int:
    cur = conn.execute(
        "INSERT INTO sync_runs(source, status, started_at) VALUES(?, 'running', ?)",
        (source, now_iso()),
    )
    conn.commit()
    return int(cur.lastrowid)


def finish_sync_run(
    conn: sqlite3.Connection,
    run_id: int,
    status: str,
    stats: dict[str, Any] | None = None,
    error: str | None = None,
) -> None:
    conn.execute(
        "UPDATE sync_runs SET status = ?, finished_at = ?, stats_json = ?, error = ? WHERE id = ?",
        (status, now_iso(), json_dumps(stats or {}), error, run_id),
    )
    conn.commit()


def get_sync_runs(conn: sqlite3.Connection, limit: int = 20) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT * FROM sync_runs ORDER BY id DESC LIMIT ?", (max(1, min(100, limit)),)
    ).fetchall()
    result = []
    for row in rows:
        item = dict(row)
        item["stats"] = json_loads(item.pop("stats_json"), {})
        result.append(item)
    return result


def prune_recommendations(conn: sqlite3.Connection, keep_batches: int = 20) -> int:
    """Keep only the most recent ``keep_batches`` batches, deleting older rows.

    Batches are ranked by their latest ``created_at`` (ties broken by
    ``batch_id``).  Returns the number of deleted rows.
    """
    keep = max(1, int(keep_batches))
    cur = conn.execute(
        """
        DELETE FROM recommendations
        WHERE batch_id IN (
            SELECT batch_id FROM (
                SELECT batch_id, MAX(created_at) AS last_at
                FROM recommendations
                GROUP BY batch_id
                ORDER BY last_at DESC, batch_id DESC
                LIMIT -1 OFFSET ?
            )
        )
        """,
        (keep,),
    )
    removed = max(0, cur.rowcount)
    conn.commit()
    return removed


def save_recommendations(
    conn: sqlite3.Connection,
    items: list[dict[str, Any]],
    algorithm_version: str = "content-v1",
) -> str:
    batch_id = uuid.uuid4().hex
    timestamp = now_iso()
    conn.executemany(
        """
        INSERT INTO recommendations(batch_id, work_id, score, reason, algorithm_version, created_at)
        VALUES(?, ?, ?, ?, ?, ?)
        """,
        [
            (batch_id, item["id"], item["score"], item.get("reason"), algorithm_version, timestamp)
            for item in items
        ],
    )
    conn.commit()
    prune_recommendations(conn)
    return batch_id


def get_stats(conn: sqlite3.Connection) -> dict[str, Any]:
    def count(table: str) -> int:
        return int(conn.execute(f"SELECT COUNT(*) AS c FROM {table}").fetchone()["c"])

    return {
        "works": count("works"),
        "tags": count("tags"),
        "companies": count("companies"),
        "entries": count("my_entries"),
        "feedback": count("feedback"),
        "recommendations": count("recommendations"),
        "sync_runs": count("sync_runs"),
    }
