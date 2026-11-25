from __future__ import annotations

import sqlite3

import pytest

from app.recommend.engine import (
    ALGORITHM_VERSION,
    HYBRID_ALGORITHM_VERSION,
    algorithm_version,
    build_profile,
    recommend,
    similar_works,
)
from app.recommend.votes import (
    get_votes_stats,
    import_votes_dump,
    votes_db_path,
)
from app.repository import add_feedback, upsert_entry
from scripts.evaluate import evaluate, ndcg_at_k, recall_at_k

from .helpers import add_work


def _seed(conn):
    liked = add_work(
        conn,
        title="Liked Romance",
        tags=["romance", "school", "drama"],
        rating=9.0,
        companies=["Studio A"],
    )
    close = add_work(
        conn,
        title="Close Candidate",
        tags=["romance", "school", "comedy"],
        rating=8.6,
        companies=["Studio A"],
    )
    far = add_work(
        conn,
        title="Far Candidate",
        tags=["horror", "gore"],
        rating=8.5,
        companies=["Studio Z"],
    )
    return liked, close, far


def test_profile_uses_positive_and_negative_ratings(conn):
    liked, close, far = _seed(conn)
    upsert_entry(conn, liked, {"status": "finished", "rating": 9.0})
    upsert_entry(conn, far, {"status": "dropped", "rating": 2.0})

    from app.recommend.engine import FeatureIndex

    index = FeatureIndex.build(conn)
    profile = build_profile(conn, index)

    assert profile.has_profile is True
    assert profile.liked_work_ids and profile.liked_work_ids[0][0] == liked
    assert far in profile.disliked_work_ids
    assert profile.vector
    assert profile.negative_vector


def test_recommend_excludes_played_and_prefers_similar_content(conn):
    liked, close, far = _seed(conn)
    upsert_entry(conn, liked, {"status": "finished", "rating": 9.5})

    items = recommend(conn, limit=10)
    ids = [item["id"] for item in items]

    assert liked not in ids
    assert close in ids
    assert ids.index(close) < ids.index(far)
    close_item = next(item for item in items if item["id"] == close)
    assert "Liked Romance" in close_item["reason"]
    assert close_item["algorithm_version"] == "content-v1"
    assert 0.0 <= close_item["score"] <= 1.0


def test_recommend_excludes_not_interested(conn):
    liked, close, far = _seed(conn)
    upsert_entry(conn, liked, {"status": "finished", "rating": 9.0})
    add_feedback(conn, close, "not_interested")

    ids = [item["id"] for item in recommend(conn, limit=10)]
    assert close not in ids
    assert far in ids


def test_recommend_nsfw_filter(conn):
    liked, _, _ = _seed(conn)
    upsert_entry(conn, liked, {"status": "finished", "rating": 9.5})
    nsfw = add_work(conn, title="NSFW Work", tags=["romance", "school"], nsfw=True)

    assert nsfw not in [item["id"] for item in recommend(conn, limit=10)]
    assert nsfw in [item["id"] for item in recommend(conn, limit=10, include_nsfw=True)]


def test_cold_start_reasons_and_quality_order(conn):
    high = add_work(conn, title="High Quality", tags=["drama"], rating=9.2)
    low = add_work(conn, title="Low Quality", tags=["drama"], rating=6.0)

    items = recommend(conn, limit=10)
    assert [item["id"] for item in items] == [high, low]
    assert all(item["reason"] for item in items)
    assert "高口碑" in items[0]["reason"]


def test_similar_works_share_tags(conn):
    target = add_work(conn, title="Target", tags=["mystery", "science fiction"], rating=8.8)
    similar = add_work(
        conn, title="Similar", tags=["mystery", "science fiction"], rating=8.7
    )
    add_work(conn, title="Unrelated", tags=["cooking"], rating=7.0)

    items = similar_works(conn, target, limit=5)
    assert items
    assert items[0]["id"] == similar
    assert "Target" in items[0]["reason"]
    assert "mystery" in items[0]["shared_tags"]
    assert all(item["id"] != target for item in items)


# --- Phase 3: votes import, item-CF and hybrid ranking -----------------------


def _write_dump(path, text: str):
    path.write_text(text, encoding="utf-8")
    return path


def test_votes_dump_import_and_aggregation(tmp_path):
    dump = _write_dump(
        tmp_path / "votes.txt",
        "-- VNDB votes dump\n"
        "v1 u1 90 2020-01-01\n"
        "v1\tu2\t80\t2020-01-02\n"
        "v2 u1 100\n"
        "v2 u3 70 2020-01-03\n"
        "v3 u4 150 2020-01-04\n"
        "this line is broken\n\n",
    )
    votes_path = votes_db_path(tmp_path / "gallove.db")
    assert votes_path.name == "votes.db"
    assert votes_path.parent == tmp_path

    stats = import_votes_dump(dump, votes_path, min_votes=2)
    assert stats["parsed"] == 4
    assert stats["comments"] == 1
    assert stats["skipped"] == 2
    assert stats["items_imported"] == 2
    assert stats["votes_imported"] == 4
    assert stats["imported"] == 4

    db_stats = get_votes_stats(votes_path)
    assert db_stats["available"] is True
    assert db_stats["votes"] == 4
    assert db_stats["users"] == 3
    assert db_stats["items"] == 2

    check = sqlite3.connect(votes_path)
    try:
        scores = [
            row[0]
            for row in check.execute("SELECT score FROM votes WHERE vndb_id = 1 ORDER BY user_id")
        ]
        assert scores == pytest.approx([0.9, 0.8])
        aggregate = check.execute(
            "SELECT vote_count, mean_score FROM vote_items WHERE vndb_id = 1"
        ).fetchone()
        assert aggregate[0] == 2
        assert aggregate[1] == pytest.approx(0.85)
    finally:
        check.close()


def test_import_votes_dump_limit_keeps_top_items(tmp_path):
    dump = _write_dump(
        tmp_path / "votes.txt",
        "".join(f"v{vndb} u{user} 90\n" for vndb in (1, 2, 3) for user in (1, 2)),
    )
    stats = import_votes_dump(dump, tmp_path / "votes.db", min_votes=2, limit=2)
    assert stats["votes_imported"] == 2
    assert stats["items_imported"] == 1
    assert get_votes_stats(tmp_path / "votes.db")["votes"] == 2


def _seed_cf_votes(conn, tmp_path):
    """Six liked works co-voted with a target work, and a content-similar rival."""
    seed_ids = []
    for vndb_id in (1, 4, 5, 6, 7, 9):
        work_id = add_work(
            conn,
            title=f"Liked {vndb_id}",
            tags=["drama", "school"],
            rating=9.0,
            source="vndb",
            external_id=str(vndb_id),
        )
        upsert_entry(conn, work_id, {"status": "finished", "rating": 9.0, "favorite": True})
        seed_ids.append(work_id)

    boosted = add_work(
        conn, title="CF Boosted", tags=["horror"], rating=9.2,
        source="vndb", external_id="2",
    )
    plain = add_work(
        conn, title="Content Plain", tags=["drama"], rating=7.5,
        source="vndb", external_id="3",
    )

    lines = ["-- synthetic item-CF votes"]
    for user in range(1, 11):
        for vndb_id in (1, 4, 5, 6, 7, 9):
            lines.append(f"v{vndb_id} u{user} 80")
        lines.append(f"v2 u{user} 90")
        lines.append(f"v8 u{user} 10")  # centering anchor
        if user <= 3:
            lines.append(f"v3 u{user} 10")  # negative signal for the rival
    dump = _write_dump(tmp_path / "votes.txt", "\n".join(lines) + "\n")
    votes_path = votes_db_path(tmp_path / "gallove.db")
    import_votes_dump(dump, votes_path, min_votes=2)
    return votes_path, seed_ids, boosted, plain


def test_hybrid_cf_boosts_ranking_and_reasons(conn, tmp_path):
    votes_path, seeds, boosted, plain = _seed_cf_votes(conn, tmp_path)

    assert algorithm_version(conn, votes_db=votes_path) == HYBRID_ALGORITHM_VERSION

    content_items = recommend(conn, algorithm="content", limit=10, votes_db=votes_path)
    hybrid_items = recommend(conn, algorithm="auto", limit=10, votes_db=votes_path)

    def rank(items, work_id):
        return [item["id"] for item in items].index(work_id)

    assert rank(hybrid_items, boosted) < rank(content_items, boosted)
    assert all(item["algorithm_version"] == HYBRID_ALGORITHM_VERSION for item in hybrid_items)
    boosted_item = next(item for item in hybrid_items if item["id"] == boosted)
    assert "投票口味相近的玩家也喜欢" in boosted_item["reason"]
    assert 0.0 <= boosted_item["score"] <= 1.0
    # CF neighbors also enrich similar_works.
    related = similar_works(conn, seeds[0], limit=5, votes_db=votes_path)
    assert any("投票口味相近的玩家" in item["reason"] for item in related)


def test_hybrid_degrades_gracefully_without_votes(conn):
    liked, close, far = _seed(conn)
    upsert_entry(conn, liked, {"status": "finished", "rating": 9.0})

    assert algorithm_version(conn) == ALGORITHM_VERSION
    for mode in (None, "auto", "hybrid"):
        items = recommend(conn, limit=10, algorithm=mode)
        assert items
        assert all(item["algorithm_version"] == ALGORITHM_VERSION for item in items)
        assert close in [item["id"] for item in items]

    with pytest.raises(ValueError):
        recommend(conn, algorithm="unknown")


def test_explicit_content_ignores_available_votes(conn, tmp_path):
    votes_path, seeds, boosted, _ = _seed_cf_votes(conn, tmp_path)
    items = recommend(conn, limit=10, algorithm="content", votes_db=votes_path)
    assert items
    assert all(item["algorithm_version"] == ALGORITHM_VERSION for item in items)
    assert all("投票口味相近的玩家" not in item["reason"] for item in items)


def test_metric_helpers():
    assert recall_at_k([1, 2, 3], [3, 4], k=3) == pytest.approx(0.5)
    assert ndcg_at_k([3, 1], [3], k=2) == pytest.approx(1.0)
    assert ndcg_at_k([1, 3], [3], k=2) == pytest.approx(1.0 / 1.584962500721156)


def test_evaluate_holdout_metrics(conn):
    for index in range(8):
        work_id = add_work(
            conn,
            title=f"Rated Work {index}",
            tags=["drama" if index % 2 else "romance"],
            rating=8.0 + index * 0.1,
        )
        upsert_entry(conn, work_id, {"status": "finished", "rating": 8.0 + index * 0.1})

    summary = evaluate(conn, algorithm="content", seed=42)
    assert summary["evaluated"] is True
    assert summary["holdout_size"] == 2
    assert summary["algorithm_version"] == ALGORITHM_VERSION
    assert 0.0 <= summary["recall_at_20"] <= 1.0
    assert 0.0 <= summary["ndcg_at_20"] <= 1.0
    assert 0.0 <= summary["tag_diversity"] <= 1.0
    assert 0.0 <= summary["catalog_coverage"] <= 1.0
    assert summary["hits"] == sorted(summary["hits"])
    assert len(summary["hits"]) <= summary["holdout_size"]


def test_evaluate_with_hybrid_votes(conn, tmp_path):
    votes_path, seeds, boosted, plain = _seed_cf_votes(conn, tmp_path)
    summary = evaluate(conn, algorithm="auto", votes_db=votes_path, seed=7)
    assert summary["evaluated"] is True
    assert summary["algorithm_version"] == HYBRID_ALGORITHM_VERSION
    assert summary["rated_entries"] >= 6


def test_evaluate_insufficient_ratings(conn):
    for index in range(3):
        work_id = add_work(conn, title=f"Few {index}", tags=["drama"], rating=8.0)
        upsert_entry(conn, work_id, {"status": "finished", "rating": 8.0})
    summary = evaluate(conn)
    assert summary["evaluated"] is False
    assert "不足 6 条" in summary["message"]
