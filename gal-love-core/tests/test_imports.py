"""Tests for incremental VNDB/Bangumi imports and the sync scheduler."""

from __future__ import annotations

import sqlite3
from typing import Any

import pytest

from app.ingest.bangumi import import_bangumi
from app.ingest.state import (
    KEY_BANGUMI_LAST_FETCH_AT,
    KEY_VNDB_LAST_FETCH_AT,
    KEY_VNDB_LAST_MAX_VOTECOUNT,
    get_meta,
)
from app.ingest.vndb import import_vndb
from app.normalize import json_dumps
from app.repository import get_sync_runs
from app.scheduler import run_once

FIXED_TIME = "2020-01-01T00:00:00+00:00"


@pytest.fixture(autouse=True)
def _fixed_clock(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make fetched_at and cursors deterministic so early-stop rules are testable."""
    monkeypatch.setattr("app.ingest.state.now_iso", lambda: FIXED_TIME)
    monkeypatch.setattr("app.repository.now_iso", lambda: FIXED_TIME)


class FakeClient:
    """In-memory stand-in for VndbClient / BangumiClient (no network)."""

    def __init__(self, pages: list[list[dict[str, Any]]]) -> None:
        self.pages = pages
        self.page_calls = 0
        self.closed = False

    def fetch_top_pages(self, limit: int = 100, **kwargs: Any):
        for page in self.pages:
            self.page_calls += 1
            yield list(page)

    def fetch_top(self, limit: int = 100, **kwargs: Any):
        for page in self.pages:
            self.page_calls += 1
            yield from page

    def close(self) -> None:
        self.closed = True


def vn(vn_id: str, title: str, votes: int) -> dict[str, Any]:
    return {
        "id": vn_id,
        "title": title,
        "alttitle": None,
        "titles": [],
        "aliases": [],
        "tags": [],
        "developers": [],
        "votecount": votes,
        "rating": 8.0,
        "image": {"url": None, "sexual": 0},
        "released": "2020-01-01",
        "length": None,
        "length_minutes": None,
        "platforms": ["Windows"],
        "languages": ["ja"],
        "description": f"desc {title}",
    }


def bgm(subject_id: int, name: str, name_cn: str, total: int = 200) -> dict[str, Any]:
    return {
        "id": subject_id,
        "name": name,
        "name_cn": name_cn,
        "tags": [{"name": "视觉小说", "count": 50}],
        "rating": {"score": 8.0, "total": total},
        "infobox": [],
        "date": "2020-01-01",
        "images": {"large": "https://img.example/cover.jpg"},
        "summary": "摘要",
    }


def test_first_vndb_import_writes_cursor(conn: sqlite3.Connection) -> None:
    pages = [
        [vn("v1", "VN One", 500), vn("v2", "VN Two", 400)],
        [vn("v3", "VN Three", 300)],
    ]
    client = FakeClient(pages)

    result = import_vndb(conn, limit=3, client=client)

    assert result["new"] == 3
    assert result["updated"] == 0
    assert result["unchanged"] == 0
    assert result["imported"] == 3
    assert result["failed"] == 0
    assert client.page_calls == 2
    assert result["cursor"]["last_fetch_at"] == FIXED_TIME
    assert result["cursor"]["last_max_votecount"] == 500
    assert get_meta(conn, KEY_VNDB_LAST_FETCH_AT) == FIXED_TIME
    assert get_meta(conn, KEY_VNDB_LAST_MAX_VOTECOUNT) == 500


def test_incremental_no_changes_stops_after_first_page(conn: sqlite3.Connection) -> None:
    first_pages = [
        [vn("v1", "VN One", 500), vn("v2", "VN Two", 400)],
        [vn("v3", "VN Three", 300)],
    ]
    import_vndb(conn, limit=3, client=FakeClient(first_pages))

    # Second page would only be fetched if early-stop failed.
    second_client = FakeClient(first_pages + [[vn("v4", "VN Four", 200)]])
    result = import_vndb(conn, limit=4, client=second_client)

    assert second_client.page_calls == 1
    assert result["early_stopped"] is True
    assert result["new"] == 0
    assert result["updated"] == 0
    assert result["unchanged"] == 2
    assert result["imported"] == 0


def test_incremental_detects_new_and_updated_entries(conn: sqlite3.Connection) -> None:
    import_vndb(
        conn,
        limit=2,
        client=FakeClient([[vn("v1", "VN One", 500), vn("v2", "VN Two", 400)]]),
    )

    changed_page = [
        vn("v1", "VN One Revised", 600),  # updated
        vn("v3", "VN Three", 350),  # new
        vn("v2", "VN Two", 400),  # unchanged
    ]
    result = import_vndb(conn, limit=3, client=FakeClient([changed_page]))

    assert result["new"] == 1
    assert result["updated"] == 1
    assert result["unchanged"] == 1
    assert result["imported"] == 2
    assert result["early_stopped"] is False
    assert result["cursor"]["last_max_votecount"] == 600

    # save_work_payload deliberately keeps an existing non-Chinese title, but
    # external ratings/votes and raw_json must be refreshed.
    row = conn.execute(
        "SELECT works.vndb_votecount, external_refs.raw_json FROM works "
        "JOIN external_refs ON works.id = external_refs.work_id "
        "WHERE external_refs.source = 'vndb' AND external_refs.external_id = 'v1'"
    ).fetchone()
    assert row["vndb_votecount"] == 600
    assert "VN One Revised" in row["raw_json"]


def test_stats_are_written_into_sync_runs(conn: sqlite3.Connection) -> None:
    import_vndb(conn, limit=1, client=FakeClient([[vn("v1", "VN One", 500)]]))

    runs = get_sync_runs(conn, limit=1)
    assert len(runs) == 1
    run = runs[0]
    assert run["source"] == "vndb"
    assert run["status"] == "success"
    for key in ("new", "updated", "unchanged", "cursor"):
        assert key in run["stats"]
    assert run["stats"]["new"] == 1


def test_full_mode_does_not_early_stop(conn: sqlite3.Connection) -> None:
    pages = [[vn("v1", "VN One", 500)], [vn("v2", "VN Two", 400)]]
    import_vndb(conn, limit=2, client=FakeClient(pages))

    client = FakeClient(pages)
    result = import_vndb(conn, limit=2, client=client, incremental=False)

    assert client.page_calls == 2
    assert result["incremental"] is False
    assert result["early_stopped"] is False
    assert result["updated"] == 2
    assert result["unchanged"] == 0


def test_bangumi_incremental_counts_and_cursor(conn: sqlite3.Connection) -> None:
    pages = [
        [bgm(1, "Game A", "游戏甲", 300), bgm(2, "Game B", "游戏乙", 200)],
        [bgm(3, "Game C", "游戏丙", 100)],
    ]
    first = import_bangumi(conn, limit=3, client=FakeClient(pages))
    assert first["new"] == 3
    assert get_meta(conn, KEY_BANGUMI_LAST_FETCH_AT) == FIXED_TIME

    client = FakeClient(pages + [[bgm(4, "Game D", "游戏丁", 50)]])
    second = import_bangumi(conn, limit=4, client=client)
    assert client.page_calls == 1
    assert second["unchanged"] == 2
    assert second["new"] == 0
    assert second["early_stopped"] is True


def test_scheduler_run_once_writes_sync_runs(
    db_path: Any, conn: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "app.ingest.vndb.VndbClient",
        lambda: FakeClient([[vn("v1", "VN One", 500), vn("v2", "VN Two", 400)]]),
    )
    monkeypatch.setattr(
        "app.ingest.bangumi.BangumiClient",
        lambda: FakeClient([[bgm(1, "Game A", "游戏甲", 300)]]),
    )

    result = run_once(db_path, sources=["vndb", "bangumi"])

    assert set(result["sources"]) == {"vndb", "bangumi"}
    assert result["sources"]["vndb"]["new"] == 2
    assert result["sources"]["bangumi"]["new"] == 1
    runs = get_sync_runs(conn, limit=10)
    assert {run["source"] for run in runs} == {"vndb", "bangumi"}
    assert all(run["status"] == "success" for run in runs)


def test_incremental_preserves_manual_fields(conn: sqlite3.Connection) -> None:
    from tests.helpers import add_work

    work_id = add_work(conn, title="Manual VN", source="manual", rating=9.0)
    conn.execute(
        "INSERT INTO external_refs(work_id, source, external_id, url, raw_json, fetched_at) "
        "VALUES(?, 'vndb', 'v9', NULL, ?, ?)",
        (work_id, json_dumps({"id": "v9", "title": "Old"}), FIXED_TIME),
    )
    conn.commit()

    result = import_vndb(conn, limit=1, client=FakeClient([[vn("v9", "External VN", 700)]]))

    assert result["updated"] == 1
    row = conn.execute("SELECT title, description FROM works WHERE id = ?", (work_id,)).fetchone()
    assert row["title"] == "Manual VN"
    assert row["description"] == "Manual VN description"
