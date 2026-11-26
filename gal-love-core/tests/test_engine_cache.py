"""FeatureIndex cross-request cache and tag-category weighting."""

from __future__ import annotations

import pytest

from app.db import connect, init_db
from app.recommend.engine import (
    CATEGORY_WEIGHTS,
    FeatureIndex,
    clear_index_cache,
)
from app.repository import save_work_payload

from .helpers import add_work


@pytest.fixture(autouse=True)
def _isolate_cache():
    clear_index_cache()
    try:
        yield
    finally:
        clear_index_cache()


def _add_categorized_work(
    conn, title: str, tags: list[tuple[str, str | None]], weight: float = 2.0
) -> int:
    payload = {
        "source": "manual",
        "external_id": None,
        "title": title,
        "description": f"{title} description",
        "release_date": "2020-01-01",
        "manual_rating": 8.0,
        "nsfw": False,
        "tags": [
            {"name": name, "weight": weight, "spoiler": 0, "category": category}
            for name, category in tags
        ],
        "companies": [],
        "titles": [],
    }
    return save_work_payload(conn, payload)


def _tag_id(index: FeatureIndex, name: str) -> int:
    return next(tag_id for tag_id, stored in index.tag_names.items() if stored == name)


def test_build_is_cached_within_same_database(conn):
    add_work(conn, title="Cached Work", tags=["drama"])

    first = FeatureIndex.build(conn)
    second = FeatureIndex.build(conn)

    assert first is second


def test_inserting_a_work_invalidates_the_cache(conn):
    add_work(conn, title="First", tags=["drama"])

    first = FeatureIndex.build(conn)
    add_work(conn, title="Second", tags=["comedy"])
    second = FeatureIndex.build(conn)

    assert second is not first
    assert len(second.works) == len(first.works) + 1


def test_adding_a_work_tag_invalidates_the_cache(conn):
    work_id = add_work(conn, title="Tagless", tags=[])

    first = FeatureIndex.build(conn)
    assert first.works[work_id].vector == {}

    conn.execute(
        """
        INSERT INTO tags(name, normalized_name, category, source)
        VALUES('late-tag', 'late-tag', 'cont', 'manual')
        """
    )
    tag_id = conn.execute(
        "SELECT id FROM tags WHERE normalized_name = 'late-tag'"
    ).fetchone()["id"]
    conn.execute(
        "INSERT INTO work_tags(work_id, tag_id, weight, spoiler, source) VALUES(?, ?, 1.0, 0, 'manual')",
        (work_id, tag_id),
    )
    conn.commit()

    second = FeatureIndex.build(conn)

    assert second is not first
    assert second.works[work_id].vector


def test_different_database_files_do_not_share_cache(conn, tmp_path):
    other_path = tmp_path / "other.db"
    init_db(other_path)
    other = connect(other_path)
    try:
        add_work(conn, title="Only Here", tags=["drama"])

        index_main = FeatureIndex.build(conn)
        index_other = FeatureIndex.build(other)

        assert index_main is not index_other
        assert len(index_main.works) == 1
        assert len(index_other.works) == 0

        # Each database keeps its own cached object.
        assert FeatureIndex.build(conn) is index_main
        assert FeatureIndex.build(other) is index_other
    finally:
        other.close()


def test_clear_index_cache_forces_a_rebuild(conn):
    add_work(conn, title="Cached Work", tags=["drama"])

    first = FeatureIndex.build(conn)
    assert FeatureIndex.build(conn) is first

    clear_index_cache()
    rebuilt = FeatureIndex.build(conn)

    assert rebuilt is not first
    assert set(rebuilt.works) == set(first.works)


def test_ero_tags_are_downweighted_to_a_quarter(conn):
    work_id = _add_categorized_work(
        conn,
        "Mixed Categories",
        [("Ero Thing", "ero"), ("Cont Thing", "cont")],
    )

    index = FeatureIndex.build(conn)
    ero_id = _tag_id(index, "Ero Thing")
    cont_id = _tag_id(index, "Cont Thing")
    vector = index.works[work_id].vector

    # Same raw weight and document frequency (each tag occurs once), so the
    # only difference is the category multiplier: ero 0.25 vs cont 1.0.
    assert CATEGORY_WEIGHTS["ero"] / CATEGORY_WEIGHTS["cont"] == pytest.approx(0.25)
    assert vector[ero_id] / vector[cont_id] == pytest.approx(0.25, rel=1e-9)


def test_category_downweighting_does_not_touch_tag_names(conn):
    work_id = _add_categorized_work(
        conn,
        "Mixed Categories",
        [("Ero Thing", "ero"), ("Cont Thing", "cont")],
    )

    index = FeatureIndex.build(conn)

    assert index.works[work_id].tag_ids
    assert index.tag_names[_tag_id(index, "Ero Thing")] == "Ero Thing"
    assert index.tag_names[_tag_id(index, "Cont Thing")] == "Cont Thing"


def test_custom_category_weights_change_the_cache_key(conn):
    work_id = _add_categorized_work(
        conn,
        "Mixed Categories",
        [("Ero Thing", "ero"), ("Cont Thing", "cont")],
    )

    default_index = FeatureIndex.build(conn)
    neutral_index = FeatureIndex.build(conn, category_weights={"ero": 1.0, "cont": 1.0})

    assert neutral_index is not default_index
    ero_id = _tag_id(neutral_index, "Ero Thing")
    cont_id = _tag_id(neutral_index, "Cont Thing")
    vector = neutral_index.works[work_id].vector
    assert vector[ero_id] / vector[cont_id] == pytest.approx(1.0, rel=1e-9)
