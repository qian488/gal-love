from __future__ import annotations

import pytest

from app.normalize import json_loads, normalize_text
from app.tag_zh import backfill_tag_names
from app.repository import (
    add_feedback,
    find_duplicate_candidates,
    get_entries,
    get_work,
    list_tags,
    merge_works,
    save_work_payload,
    search_works,
    upsert_entry,
)
from app.tag_zh import TAG_ZH_MAP, canonical_lookup

from .helpers import add_work


def test_upsert_is_idempotent_by_external_id(conn):
    payload = {
        "source": "vndb",
        "external_id": "v1",
        "title": "Example VN",
        "description": "first",
        "vndb_rating": 80,
        "vndb_votecount": 120,
        "tags": [{"name": "Romance", "weight": 2.0}],
        "companies": [{"name": "Studio A", "role": "developer"}],
    }
    work_id = save_work_payload(conn, payload)
    payload["description"] = "updated"
    payload["tags"] = [{"name": "School", "weight": 3.0}]
    same_id = save_work_payload(conn, payload)
    assert same_id == work_id
    work = get_work(conn, work_id)
    assert work is not None
    assert work["description"] == "updated"
    tags = {tag["name"] for tag in work["tags"]}
    assert "School" in tags
    assert len(work["external_refs"]) == 1


def test_manual_data_is_not_overwritten_by_external_source(conn):
    work_id = add_work(conn, title="Manual Work", companies=["Manual Studio"])
    # Add a field that can be overwritten by external data.
    conn.execute(
        "UPDATE works SET description = ? WHERE id = ?", ("my own description", work_id)
    )
    conn.commit()
    save_work_payload(
        conn,
        {
            "source": "vndb",
            "external_id": "v99",
            "title": "Manual Work",
            "description": "external description",
            "vndb_rating": 90,
            "vndb_votecount": 500,
        },
    )
    work = get_work(conn, work_id)
    assert work is not None
    assert work["description"] == "my own description"
    assert work["vndb_rating"] == 90


def test_search_by_title_tag_and_status(conn):
    a = add_work(conn, title="Sakura Summer", tags=["school", "romance"])
    b = add_work(conn, title="Dark Night", tags=["horror"])
    assert search_works(conn, query="Sakura")["total"] == 1
    assert search_works(conn, tag="romance")["total"] == 1
    upsert_entry(conn, a, {"status": "finished", "rating": 9})
    assert search_works(conn, status="finished")["items"][0]["id"] == a
    assert search_works(conn, status="none")["items"][0]["id"] == b


def test_entry_roundtrip_and_feedback(conn):
    work_id = add_work(conn, title="Entry Work", tags=["drama"])
    upsert_entry(conn, work_id, {"status": "playing", "rating": 8.5, "favorite": True})
    entries = get_entries(conn)
    assert len(entries) == 1
    assert entries[0]["entry"]["status"] == "playing"
    assert entries[0]["entry"]["favorite"] is True
    add_feedback(conn, work_id, "not_interested")
    assert conn.execute("SELECT COUNT(*) AS c FROM feedback").fetchone()["c"] == 1


def test_title_normalization_handles_fullwidth(conn):
    work_id = add_work(conn, title="ＡＢＣ　物語")
    row = conn.execute("SELECT normalized_title FROM works WHERE id = ?", (work_id,)).fetchone()
    assert row["normalized_title"] == normalize_text("ＡＢＣ　物語")
    assert normalize_text("ＡＢＣ　物語") == "abc物語"


def test_normalize_text_enhancements():
    assert normalize_text("恋爱") == normalize_text("戀愛")
    assert normalize_text("Hello, World!") == "helloworld"
    assert normalize_text("ＡＢＣ　物語") == "abc物語"


def test_builtin_tag_mapping_coverage():
    assert len(TAG_ZH_MAP) >= 50
    assert canonical_lookup("Comedy")[0] == "comedy"
    assert canonical_lookup("校园")[0] == "school"
    assert canonical_lookup("视觉小说")[1] == "视觉小说"
    assert canonical_lookup("不存在的标签") is None


def test_tag_alias_and_chinese_name_collapse_to_one_tag(conn):
    add_work(conn, title="Alias A", source="vndb", external_id="v1", tags=["Romance"])
    add_work(conn, title="Alias B", source="bangumi", external_id="b1", tags=["恋爱"])
    add_work(conn, title="Alias C", tags=["love"])

    rows = conn.execute("SELECT id, name, name_zh, aliases FROM tags").fetchall()
    assert len(rows) == 1
    assert rows[0]["name_zh"] == "恋爱"
    assert "love" in json_loads(rows[0]["aliases"], [])
    assert conn.execute("SELECT COUNT(*) AS c FROM tag_aliases").fetchone()["c"] >= 2

    assert search_works(conn, tag="恋爱")["total"] == 3
    assert search_works(conn, tag="love")["total"] == 3
    listed = list_tags(conn, query="恋爱")
    assert len(listed) == 1
    assert listed[0]["name_zh"] == "恋爱"
    assert listed[0]["work_count"] == 3


def test_duplicate_candidates_and_merge(conn):
    source = add_work(
        conn,
        title="Same Title",
        companies=["Studio X"],
        year=2020,
        source="vndb",
        external_id="s1",
    )
    target = add_work(
        conn,
        title="Same Title 续篇",
        companies=["Studio X"],
        year=2020,
        source="bangumi",
        external_id="t1",
    )
    # 两条记录来自不同来源，但共享一个别名——这才是判定重复的强信号。
    conn.execute(
        "INSERT INTO titles(work_id, lang, title, normalized_title, official, is_main, source) "
        "VALUES(?, 'alias', 'Same Title', ?, 0, 0, 'manual')",
        (target, normalize_text("Same Title")),
    )
    conn.commit()
    upsert_entry(
        conn, source, {"status": "finished", "rating": 9, "favorite": True, "notes": "mine"}
    )
    add_feedback(conn, source, "not_interested", "duplicate")

    candidates = find_duplicate_candidates(conn)
    match = [
        item
        for item in candidates
        if {item["work_id"], item["other_id"]} == {source, target}
    ]
    assert match
    assert match[0]["score"] >= 0.75
    assert match[0]["reasons"]

    result = merge_works(conn, source, target)
    assert result["ok"] is True
    assert result["source_id"] == source
    assert result["target_id"] == target
    assert result["moved"]["external_refs"] >= 1
    assert result["moved"]["titles"] >= 1
    assert result["moved"]["feedback"] == 1
    assert result["moved"]["my_entries"] == 1

    assert get_work(conn, source) is None
    merged = get_work(conn, target)
    assert merged is not None
    assert merged["entry"]["status"] == "finished"
    assert merged["entry"]["favorite"] is True
    assert merged["entry"]["notes"] == "mine"
    assert any(ref["external_id"] == "s1" for ref in merged["external_refs"])
    assert conn.execute("SELECT COUNT(*) AS c FROM merge_log").fetchone()["c"] == 1
    assert find_duplicate_candidates(conn) == []


def test_backfill_translates_legacy_tags(conn):
    conn.execute(
        "INSERT INTO tags(name, normalized_name, category, source) VALUES('Romance', 'romance', 'cont', 'vndb')"
    )
    conn.commit()
    before = list_tags(conn, query="恋爱")
    assert before == []

    stats = backfill_tag_names(conn)
    assert stats["tags_updated"] >= 1
    listed = list_tags(conn, query="恋爱")
    assert any(item["name"] == "Romance" and item["name_zh"] == "恋爱" for item in listed)


def test_company_and_year_alone_is_not_duplicate(conn):
    first = add_work(conn, title="Different Work A", companies=["Studio X"], year=2020)
    second = add_work(conn, title="Different Work B", companies=["Studio X"], year=2020)
    assert find_duplicate_candidates(conn) == []
    assert find_duplicate_candidates(conn, min_score=0.1) == []
    assert get_work(conn, first) is not None
    assert get_work(conn, second) is not None


def test_merge_validation_errors(conn):
    first = add_work(conn, title="Merge First")
    second = add_work(conn, title="Merge Second")
    with pytest.raises(ValueError, match="同一部"):
        merge_works(conn, first, first)
    with pytest.raises(ValueError, match="不存在"):
        merge_works(conn, 9999, first)
    with pytest.raises(ValueError, match="不存在"):
        merge_works(conn, first, 9999)
    assert get_work(conn, second) is not None


def test_search_filters_platform_language_year_and_length(conn):
    save_work_payload(
        conn,
        {
            "source": "manual",
            "title": "Filtered A",
            "release_year": 2018,
            "length_minutes": 90,
            "platforms": ["Windows", "Linux"],
            "languages": ["zh", "en"],
        },
    )
    save_work_payload(
        conn,
        {
            "source": "manual",
            "title": "Filtered B",
            "release_year": 2022,
            "length_minutes": 300,
            "platforms": ["Switch"],
            "languages": ["ja"],
        },
    )
    assert search_works(conn, platform="Windows")["total"] == 1
    assert search_works(conn, platform="windows")["total"] == 1
    assert search_works(conn, language="zh")["total"] == 1
    assert search_works(conn, min_year=2020)["total"] == 1
    assert search_works(conn, max_length_minutes=120)["total"] == 1
    combined = search_works(
        conn, platform="Windows", language="zh", min_year=2017, max_length_minutes=120
    )
    assert combined["total"] == 1
    assert combined["page"] == 1 and combined["limit"] == 20
    assert search_works(conn, platform="PS5")["total"] == 0


def test_search_relevance_ranking(conn):
    exact = save_work_payload(conn, {"source": "manual", "title": "Sakura"})
    prefix = save_work_payload(conn, {"source": "manual", "title": "Sakura Story"})
    contains = save_work_payload(conn, {"source": "manual", "title": "My Sakura Memory"})
    result = search_works(conn, query="sakura", sort="title")
    assert [item["id"] for item in result["items"]] == [exact, prefix, contains]


def test_query_matches_chinese_tag_and_alias_title(conn):
    add_work(conn, title="Plain Work", tags=["romance"])
    save_work_payload(
        conn,
        {
            "source": "manual",
            "title": "Main Title",
            "titles": [{"title": "中文别名", "lang": "zh"}],
        },
    )
    assert search_works(conn, query="恋爱")["total"] == 1
    assert search_works(conn, query="love")["total"] == 1
    assert search_works(conn, query="中文别名")["total"] == 1
