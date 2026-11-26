from __future__ import annotations

import re
import sqlite3
from pathlib import Path

import pytest

from app.normalize import json_loads, normalize_text
from app.tag_zh import (
    TAG_ZH_MAP,
    backfill_tag_names,
    canonical_lookup,
    canonical_lookup_keys,
)

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "gallove.db"


def _all_spellings():
    for canonical, (name_zh, aliases) in TAG_ZH_MAP.items():
        yield canonical, canonical
        yield canonical, name_zh
        for alias in aliases:
            yield canonical, alias


def test_entry_count():
    # 89 legacy entries + 255 cont/tech entries added by the tagging work.
    assert len(TAG_ZH_MAP) >= 340


def test_chinese_names_are_valid():
    for canonical, (name_zh, _aliases) in TAG_ZH_MAP.items():
        assert name_zh, f"{canonical} has no Chinese name"
        assert len(name_zh) <= 12, f"{canonical} Chinese name too long: {name_zh}"
        assert re.search(r"[\u4e00-\u9fff]", name_zh), (
            f"{canonical} Chinese name must contain CJK characters, got {name_zh!r}"
        )


def test_aliases_are_globally_unique():
    owner: dict[str, str] = {}
    conflicts: list[str] = []
    for canonical, spelling in _all_spellings():
        key = normalize_text(spelling)
        if not key:
            continue
        previous = owner.get(key)
        if previous is not None and previous != canonical:
            conflicts.append(f"{spelling!r}: {previous} vs {canonical}")
        owner[key] = canonical
    assert not conflicts, "aliases mapped to multiple canonicals:\n" + "\n".join(conflicts)


def test_each_entry_has_two_to_four_aliases():
    for canonical, (_name_zh, aliases) in TAG_ZH_MAP.items():
        values = {normalize_text(alias) for alias in aliases if normalize_text(alias)}
        assert 2 <= len(values) <= 4, f"{canonical} has {len(values)} aliases"


def test_canonical_lookup_resolves_chinese_and_english_aliases():
    info = canonical_lookup("男主视角")
    assert info is not None and info[0] == "male protagonist"
    # Chinese alias
    assert canonical_lookup("男主角")[0] == "male protagonist"
    # English alias
    assert canonical_lookup("male protag")[0] == "male protagonist"
    # Canonical spelling itself
    assert canonical_lookup("Male Protagonist")[0] == "male protagonist"

    info = canonical_lookup("分支剧情")
    assert info is not None and info[0] == "branching plot"
    assert canonical_lookup("分支故事")[0] == "branching plot"
    assert canonical_lookup("branching narrative")[0] == "branching plot"

    assert canonical_lookup("视觉小说")[0] == "visual novel"
    assert canonical_lookup("不存在的标签") is None


def test_canonical_lookup_keys_cover_all_spellings():
    keys = canonical_lookup_keys("Male Protagonist")
    assert normalize_text("男主视角") in keys
    assert normalize_text("男主角") in keys
    assert normalize_text("male protag") in keys


@pytest.mark.skipif(not DB_PATH.exists(), reason="repository database not available")
def test_non_ero_top_280_hit_rate():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    try:
        rows = connection.execute(
            """
            SELECT t.name, COUNT(*) AS n
            FROM work_tags wt
            JOIN tags t ON t.id = wt.tag_id
            WHERE t.category != 'ero'
            GROUP BY t.id
            ORDER BY n DESC
            LIMIT 280
            """
        ).fetchall()
    finally:
        connection.close()

    assert len(rows) == 280
    hits = sum(1 for row in rows if canonical_lookup(row["name"]) is not None)
    assert hits >= 250, f"only {hits}/280 non-ero high-frequency tags are mapped"


def test_backfill_fills_existing_rows_and_is_idempotent(conn):
    conn.execute(
        """
        INSERT INTO tags(name, normalized_name, category, source, name_zh, aliases)
        VALUES(?, ?, ?, ?, NULL, NULL)
        """,
        ("Male Protagonist", normalize_text("Male Protagonist"), "cont", "test"),
    )
    conn.execute(
        """
        INSERT INTO tags(name, normalized_name, category, source, name_zh, aliases)
        VALUES(?, ?, ?, ?, '', NULL)
        """,
        ("Branching Plot", normalize_text("Branching Plot"), "tech", "test"),
    )
    conn.execute(
        """
        INSERT INTO tags(name, normalized_name, category, source, name_zh, aliases)
        VALUES(?, ?, ?, ?, ?, NULL)
        """,
        ("No Sexual Content", normalize_text("No Sexual Content"), "tech", "test", "custom value"),
    )
    conn.commit()

    first = backfill_tag_names(conn)
    assert first["tags_updated"] >= 2

    male = conn.execute(
        "SELECT id, name_zh, aliases FROM tags WHERE normalized_name = ?",
        (normalize_text("Male Protagonist"),),
    ).fetchone()
    assert male is not None
    assert male["name_zh"] == "男主视角"
    male_aliases = json_loads(male["aliases"], [])
    assert "男主角" in male_aliases
    assert "male protag" in male_aliases

    branching = conn.execute(
        "SELECT name_zh FROM tags WHERE normalized_name = ?",
        (normalize_text("Branching Plot"),),
    ).fetchone()
    assert branching is not None
    assert branching["name_zh"] == "分支剧情"  # empty string was treated as unset

    custom = conn.execute(
        "SELECT name_zh FROM tags WHERE normalized_name = ?",
        (normalize_text("No Sexual Content"),),
    ).fetchone()
    assert custom is not None
    assert custom["name_zh"] == "custom value"  # existing non-empty value preserved

    alias_row = conn.execute(
        "SELECT tag_id, lang, source FROM tag_aliases WHERE alias_normalized = ?",
        (normalize_text("男主角"),),
    ).fetchone()
    assert alias_row is not None
    assert alias_row["tag_id"] == male["id"]
    assert alias_row["source"] == "builtin"

    zh_name_row = conn.execute(
        "SELECT tag_id, lang FROM tag_aliases WHERE alias_normalized = ?",
        (normalize_text("男主视角"),),
    ).fetchone()
    assert zh_name_row is not None
    assert zh_name_row["tag_id"] == male["id"]
    assert zh_name_row["lang"] == "zh"

    alias_count = conn.execute("SELECT COUNT(*) AS n FROM tag_aliases").fetchone()["n"]

    # Second run must not change names/aliases nor register duplicate alias rows.
    second = backfill_tag_names(conn)
    assert second["aliases_added"] == 0
    assert conn.execute("SELECT COUNT(*) AS n FROM tag_aliases").fetchone()["n"] == alias_count

    male_again = conn.execute(
        "SELECT name_zh, aliases FROM tags WHERE normalized_name = ?",
        (normalize_text("Male Protagonist"),),
    ).fetchone()
    assert male_again["name_zh"] == "男主视角"
    assert json_loads(male_again["aliases"], []) == male_aliases
