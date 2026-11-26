"""Entry and feedback persistence helpers."""

from __future__ import annotations

import sqlite3
from typing import Any

from ..normalize import now_iso
from ._works import get_work

ENTRY_STATUSES = {"want", "playing", "finished", "dropped"}
FEEDBACK_KINDS = {"not_interested", "like", "dislike", "seen"}


def get_entries(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT work_id, status, rating, favorite, notes, started_at, finished_at, updated_at "
        "FROM my_entries ORDER BY updated_at DESC"
    ).fetchall()
    result: list[dict[str, Any]] = []
    for row in rows:
        work = get_work(conn, int(row["work_id"]))
        if not work:
            continue
        work["entry"] = {
            "status": row["status"],
            "rating": row["rating"],
            "favorite": bool(row["favorite"]),
            "notes": row["notes"],
            "started_at": row["started_at"],
            "finished_at": row["finished_at"],
            "updated_at": row["updated_at"],
        }
        result.append(work)
    return result


def upsert_entry(conn: sqlite3.Connection, work_id: int, data: dict[str, Any]) -> dict[str, Any] | None:
    existing = conn.execute("SELECT * FROM my_entries WHERE work_id = ?", (work_id,)).fetchone()
    status = data.get("status") or (existing["status"] if existing else "want")
    if status not in ENTRY_STATUSES:
        raise ValueError(f"invalid status: {status}")
    rating = data.get("rating", existing["rating"] if existing else None)
    if rating is not None:
        rating = float(rating)
        if rating < 0 or rating > 10:
            raise ValueError("rating must be between 0 and 10")
    favorite = data.get("favorite")
    if favorite is None:
        favorite = bool(existing["favorite"]) if existing else False
    notes = data.get("notes", existing["notes"] if existing else None)
    timestamp = now_iso()
    conn.execute(
        """
        INSERT INTO my_entries(work_id, status, rating, favorite, notes, started_at, finished_at, updated_at)
        VALUES(?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(work_id) DO UPDATE SET
            status = excluded.status,
            rating = excluded.rating,
            favorite = excluded.favorite,
            notes = excluded.notes,
            updated_at = excluded.updated_at
        """,
        (
            work_id,
            status,
            rating,
            1 if favorite else 0,
            notes,
            data.get("started_at", existing["started_at"] if existing else None),
            data.get("finished_at", existing["finished_at"] if existing else None),
            timestamp,
        ),
    )
    conn.commit()
    return get_work(conn, work_id)


def delete_entry(conn: sqlite3.Connection, work_id: int) -> None:
    conn.execute("DELETE FROM my_entries WHERE work_id = ?", (work_id,))
    conn.commit()


def add_feedback(conn: sqlite3.Connection, work_id: int, kind: str, note: str | None = None) -> None:
    if kind not in FEEDBACK_KINDS:
        raise ValueError(f"invalid feedback kind: {kind}")
    conn.execute(
        """
        INSERT INTO feedback(work_id, kind, note, created_at)
        VALUES(?, ?, ?, ?)
        ON CONFLICT(work_id, kind) DO UPDATE SET note = excluded.note, created_at = excluded.created_at
        """,
        (work_id, kind, note, now_iso()),
    )
    conn.commit()


def get_feedback_work_ids(conn: sqlite3.Connection, kind: str = "not_interested") -> set[int]:
    return {
        int(row["work_id"])
        for row in conn.execute("SELECT work_id FROM feedback WHERE kind = ?", (kind,)).fetchall()
    }
