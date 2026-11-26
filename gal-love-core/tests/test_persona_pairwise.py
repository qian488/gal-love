from __future__ import annotations

from app.recommend import persona
from app.recommend.persona_pairwise import (
    KEY,
    calculate,
    next_pairs,
    record_choice,
    reset,
)
from app.repository import get_settings, upsert_entry

from .helpers import add_work


def _tag_names(work: dict) -> set[str]:
    return {tag["name"] for tag in work.get("tags") or []}


def _seed_works(conn, count: int = 8) -> list[int]:
    tag_sets = [
        ["romance", "school"],
        ["horror", "mystery"],
        ["drama", "slice of life"],
        ["fantasy", "adventure"],
        ["comedy", "friendship"],
        ["sci-fi", "psychological"],
        ["historical", "war"],
        ["sports", "music"],
        ["detective", "thriller"],
        ["magic", "supernatural"],
    ]
    ids: list[int] = []
    for index in range(count):
        ids.append(
            add_work(
                conn,
                title=f"Pairwise Work {index}",
                tags=tag_sets[index % len(tag_sets)],
                rating=8.0 + index * 0.1,
                year=2010 + index,
            )
        )
    return ids


def test_provider_is_registered():
    module = persona.get_provider(KEY)
    assert module.KEY == "pairwise"
    assert module.KIND == "pairwise"
    items = {item["key"]: item for item in persona.list_providers({})}
    assert items[KEY]["title"] == "作品二选一"
    assert items[KEY]["completed"] is False


def test_calculate_returns_empty_profile():
    result = calculate({})
    assert result["tags"] == {}
    assert result["completed"] is False
    assert result["labels"] == []


def test_next_pairs_structure_and_distinct_sides(conn):
    _seed_works(conn, 8)

    pairs = next_pairs(conn, count=1)
    assert len(pairs) == 1
    pair = pairs[0]
    assert set(pair) == {"left", "right"}
    for side in ("left", "right"):
        work = pair[side]
        assert work["id"] > 0
        assert work["title"]
        assert "cover_url" in work
        assert work["tags"]
    assert pair["left"]["id"] != pair["right"]["id"]


def test_next_pairs_prefers_low_tag_overlap(conn):
    for index in range(3):
        add_work(conn, title=f"Romance {index}", tags=["romance", "school"], rating=8.0)
    for index in range(3):
        add_work(conn, title=f"Horror {index}", tags=["horror", "mystery"], rating=8.0)

    pairs = next_pairs(conn, count=1)
    assert len(pairs) == 1
    left_tags = _tag_names(pairs[0]["left"])
    right_tags = _tag_names(pairs[0]["right"])
    assert left_tags and right_tags
    assert left_tags & right_tags == set()


def test_next_pairs_excludes_library_entries(conn):
    ids = _seed_works(conn, 10)
    entered = set(ids[:4])
    for work_id in entered:
        upsert_entry(conn, work_id, {"status": "finished"})

    seen: set[int] = set()
    for _ in range(3):
        for pair in next_pairs(conn, count=2):
            seen.update((pair["left"]["id"], pair["right"]["id"]))
    assert seen
    assert seen & entered == set()


def test_next_pairs_respects_nsfw_flag(conn):
    for index in range(3):
        add_work(conn, title=f"Safe {index}", tags=["romance", "school"], rating=8.0)
    nsfw = add_work(
        conn, title="Adult Only", tags=["horror", "mystery"], rating=8.0, nsfw=True
    )

    quiet_ids = {
        work["id"]
        for pair in next_pairs(conn, count=2, include_nsfw=False)
        for work in (pair["left"], pair["right"])
    }
    assert nsfw not in quiet_ids
    seen_ids = {
        work["id"]
        for pair in next_pairs(conn, count=2, include_nsfw=True)
        for work in (pair["left"], pair["right"])
    }
    assert nsfw in seen_ids


def test_record_choice_completes_after_ten_rounds(conn):
    ids = _seed_works(conn, 6)

    for round_index in range(10):
        result = record_choice(
            conn,
            winner_id=ids[round_index % len(ids)],
            loser_id=ids[(round_index + 1) % len(ids)],
        )
        if round_index < 9:
            assert result["completed"] is False
            assert result["answered"] == round_index + 1

    assert result["completed"] is True
    assert result["answered"] == 10
    assert result["tags"]
    assert len(result["labels"]) <= 2
    assert result["code"].startswith("偏好")
    assert result["year_center"] is not None
    assert result["negative_tags"]

    stored = get_settings(conn)["persona_profiles"]["pairwise"]
    assert stored["profile"]["completed"] is True
    assert len(stored["answers"]["choices"]) == 10
    assert stored["answers"]["completed"] is True


def test_skipped_round_only_records_recent(conn):
    ids = _seed_works(conn, 4)

    result = record_choice(conn, winner_id=ids[0], loser_id=ids[1], skipped=True)
    assert result["tags"] == {}
    assert result["completed"] is False
    assert result["answered"] == 0

    answers = get_settings(conn)["persona_profiles"]["pairwise"]["answers"]
    assert len(answers["choices"]) == 1
    assert answers["choices"][0]["skipped"] is True
    assert set(answers["recent"]) == {ids[0], ids[1]}


def test_reset_clears_pairwise_only(conn):
    ids = _seed_works(conn, 4)
    persona.save_provider(conn, "quiz", {"q_story": "story_plot"})
    record_choice(conn, winner_id=ids[0], loser_id=ids[1])

    reset(conn)

    profiles = get_settings(conn)["persona_profiles"]
    assert "pairwise" not in profiles
    assert profiles["quiz"]["profile"]["tags"]
    assert persona.provider_payload(conn, "pairwise")["result"]["completed"] is False


def test_next_pairs_insufficient_data_returns_empty(conn):
    assert next_pairs(conn) == []

    add_work(conn, title="Only One", tags=["romance"], rating=8.0)
    assert next_pairs(conn, count=3) == []


def test_next_pairs_does_not_repeat_recent_immediately(conn):
    _seed_works(conn, 10)

    first = next_pairs(conn, count=1)
    first_ids = {first[0]["left"]["id"], first[0]["right"]["id"]}
    second = next_pairs(conn, count=1)
    second_ids = {second[0]["left"]["id"], second[0]["right"]["id"]}
    assert first_ids
    assert second_ids
    assert first_ids & second_ids == set()

    recent = get_settings(conn)["persona_profiles"]["pairwise"]["answers"]["recent"]
    assert set(recent[-4:]) == first_ids | second_ids


def test_record_choice_missing_work_does_not_raise(conn):
    result = record_choice(conn, winner_id=999, loser_id=998)
    assert result["tags"] == {}
    assert result["answered"] == 1
