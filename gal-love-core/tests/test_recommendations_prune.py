from __future__ import annotations

from app.repository import prune_recommendations, save_recommendations

from .helpers import add_work


def _insert_batches(
    conn, batches: int, *, per_batch: int = 2, start_day: int = 1
) -> tuple[int, list[str]]:
    """Insert ``batches`` recommendation batches with distinct created_at values."""
    work_id = add_work(conn, title="Prune Test Work")
    batch_ids: list[str] = []
    for index in range(batches):
        batch_id = f"batch-{index:03d}"
        batch_ids.append(batch_id)
        created_at = f"2024-01-{start_day + index:02d}T00:00:00+00:00"
        for slot in range(per_batch):
            conn.execute(
                "INSERT INTO recommendations"
                "(batch_id, work_id, score, reason, algorithm_version, created_at) "
                "VALUES(?, ?, ?, ?, ?, ?)",
                (batch_id, work_id, 1.0 - slot * 0.01, None, "test", created_at),
            )
    conn.commit()
    return work_id, batch_ids


def _count(conn, sql: str, params: tuple = ()) -> int:
    return int(conn.execute(sql, params).fetchone()["c"])


def test_prune_keeps_latest_batches(conn):
    _, batch_ids = _insert_batches(conn, 25)

    removed = prune_recommendations(conn, keep_batches=20)

    assert removed == 10
    assert _count(conn, "SELECT COUNT(*) AS c FROM recommendations") == 40
    # Only the newest 20 batches survive.
    assert _count(conn, "SELECT COUNT(DISTINCT batch_id) AS c FROM recommendations") == 20
    # The oldest batch is gone, the newest is intact.
    assert (
        _count(
            conn,
            "SELECT COUNT(*) AS c FROM recommendations WHERE batch_id = ?",
            (batch_ids[0],),
        )
        == 0
    )
    assert (
        _count(
            conn,
            "SELECT COUNT(*) AS c FROM recommendations WHERE batch_id = ?",
            (batch_ids[-1],),
        )
        == 2
    )


def test_prune_zero_is_treated_as_one(conn):
    _, batch_ids = _insert_batches(conn, 5)

    removed = prune_recommendations(conn, keep_batches=0)

    assert removed == 8
    assert _count(conn, "SELECT COUNT(*) AS c FROM recommendations") == 2
    assert _count(conn, "SELECT COUNT(DISTINCT batch_id) AS c FROM recommendations") == 1
    survivors = {
        row["batch_id"]
        for row in conn.execute("SELECT DISTINCT batch_id FROM recommendations").fetchall()
    }
    assert survivors == {batch_ids[-1]}


def test_prune_is_noop_when_within_limit(conn):
    _insert_batches(conn, 3)

    assert prune_recommendations(conn, keep_batches=20) == 0
    assert _count(conn, "SELECT COUNT(*) AS c FROM recommendations") == 6


def test_save_recommendations_prunes_automatically(conn):
    work_id = add_work(conn, title="Auto Prune Work")
    items = [{"id": work_id, "score": 1.0}]

    for _ in range(25):
        save_recommendations(conn, items)

    assert _count(conn, "SELECT COUNT(*) AS c FROM recommendations") == 20
    assert _count(conn, "SELECT COUNT(DISTINCT batch_id) AS c FROM recommendations") == 20
