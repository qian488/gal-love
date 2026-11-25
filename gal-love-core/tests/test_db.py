"""Regression tests for the database connection layer."""

from __future__ import annotations

import sqlite3
import threading
from pathlib import Path

from app.db import connect


def test_connection_is_safe_across_threads(db_path: Path) -> None:
    """FastAPI dispatches sync generator dependencies and sync endpoints to
    arbitrary threadpool workers, so create / query / close may each happen on
    a different thread. A per-request connection must tolerate that, otherwise
    the API randomly answers 500 with ``SQLite objects created in a thread can
    only be used in that same thread``.
    """
    created: list[sqlite3.Connection] = []
    errors: list[BaseException] = []
    counts: list[int] = []

    def create() -> None:
        try:
            created.append(connect(db_path))
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)

    creator = threading.Thread(target=create)
    creator.start()
    creator.join(timeout=5)
    assert created, f"creating the connection failed: {errors!r}"
    conn = created[0]

    # Query from yet another thread (the main thread here).
    try:
        counts.append(int(conn.execute("SELECT COUNT(*) AS c FROM works").fetchone()["c"]))
    except BaseException as exc:  # noqa: BLE001
        errors.append(exc)

    def close() -> None:
        try:
            conn.close()
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)

    closer = threading.Thread(target=close)
    closer.start()
    closer.join(timeout=5)

    assert not creator.is_alive() and not closer.is_alive(), "worker thread hung"
    assert not errors, f"cross-thread connection use failed: {errors!r}"
    assert counts == [0]
