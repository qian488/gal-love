from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from app.recommend import persona
from app.recommend import persona_motivation as motivation
from app.repository import get_settings

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "gallove.db"


def _extreme_answers(sign: int = 1) -> dict[str, str]:
    """每题都选分数最高（sign=1）或最低（sign=-1）的选项。"""
    answers: dict[str, str] = {}
    for question in motivation.QUESTIONS:
        option = max(question["options"], key=lambda item: item["score"] * sign)
        answers[question["id"]] = option["id"]
    return answers


def test_questions_shape_and_option_ids():
    assert len(motivation.QUESTIONS) == 24
    question_ids = [question["id"] for question in motivation.QUESTIONS]
    assert len(set(question_ids)) == 24

    dimensions = {question["dimension"] for question in motivation.QUESTIONS}
    assert dimensions == set(motivation.DIMENSION_ORDER)
    for dimension in motivation.DIMENSION_ORDER:
        assert sum(1 for q in motivation.QUESTIONS if q["dimension"] == dimension) == 3

    option_ids: set[str] = set()
    for question in motivation.QUESTIONS:
        assert question["id"]
        assert question["title"]
        assert len(question["options"]) == 5
        scores = [option["score"] for option in question["options"]]
        assert scores == [-2, -1, 0, 1, 2]
        prefix = question["dimension"].lower()
        for index, option in enumerate(question["options"], start=1):
            assert option["id"] == f"{prefix}_{question['id'].rsplit('_', 1)[-1]}_{index}"
            assert option["id"] not in option_ids
            option_ids.add(option["id"])
            assert option["label"]
            assert option["tags"]
            assert all(isinstance(name, str) and name for name in option["tags"])
            assert all(weight > 0 for weight in option["tags"].values())


def test_all_highest_answers_raise_every_dimension():
    result = motivation.calculate(_extreme_answers(1))

    assert result["completed"] is True
    assert set(result["scores"]) == set(motivation.DIMENSION_ORDER)
    assert all(score == 100 for score in result["scores"].values())
    assert result["tags"]
    assert all(weight > 0 for weight in result["tags"].values())
    assert "Drama" in result["tags"]
    assert "Branching Plot" in result["tags"]
    assert result["length_center"] == 2020
    assert 2010 <= result["year_center"] <= 2013
    assert len(result["labels"]) == 2
    assert len(result["code"].split("·")) == 2


def test_all_lowest_answers_produce_low_scores_and_low_tags():
    result = motivation.calculate(_extreme_answers(-1))

    assert result["completed"] is True
    assert all(score == 0 for score in result["scores"].values())
    assert "Drama" not in result["tags"]
    assert "Comedy" in result["tags"]
    assert "Slice of Life" in result["tags"]


def test_single_dimension_answers_only_move_that_dimension():
    story_question = next(q for q in motivation.QUESTIONS if q["dimension"] == "Story")
    top_option = max(story_question["options"], key=lambda item: item["score"])
    result = motivation.calculate({story_question["id"]: top_option["id"]})

    assert result["completed"] is False
    assert result["scores"]["Story"] > 50
    for dimension in motivation.DIMENSION_ORDER:
        if dimension != "Story":
            assert result["scores"][dimension] == 50


def test_invalid_and_missing_answers_are_ignored():
    invalid = {
        "unknown_question": "story_1_1",
        "mot_story_1": "not_an_option",
        "mot_story_2": 123,
        "mot_story_3": {"nested": "value"},
    }

    assert motivation.filter_answers(invalid) == {}
    assert motivation.filter_answers(None) == {}  # type: ignore[arg-type]
    assert motivation.calculate(invalid) == motivation.calculate({})

    empty = motivation.calculate({})
    assert empty["tags"] == {}
    assert empty["completed"] is False
    assert empty["year_center"] is None
    assert empty["length_center"] is None
    assert all(score == 50 for score in empty["scores"].values())
    assert len(empty["labels"]) == 2


def test_provider_is_registered_with_framework():
    assert "motivation" in persona.provider_keys()

    items = {item["key"]: item for item in persona.list_providers({})}
    motivation_meta = items["motivation"]
    assert motivation_meta["title"] == "玩家动机"
    assert motivation_meta["subtitle"] == "24 题，测你从视觉小说里想获得什么体验"
    assert motivation_meta["kind"] == "questionnaire"
    assert motivation_meta["group"] == "serious"
    assert motivation_meta["question_count"] == 24
    assert motivation_meta["completed"] is False


def test_save_provider_roundtrip(conn):
    answers = _extreme_answers(1)
    saved = persona.save_provider(conn, "motivation", answers)

    assert saved["key"] == "motivation"
    assert saved["result"]["completed"] is True
    assert saved["result"]["tags"]["Drama"] > 0

    settings = get_settings(conn)
    bucket = settings["persona_profiles"]["motivation"]
    assert bucket["answers"] == answers
    assert bucket["profile"]["completed"] is True
    assert bucket["profile"]["tags"]["Drama"] > 0
    assert bucket["updated_at"]


def test_partial_save_keeps_only_valid_pairs(conn):
    answers = dict(_extreme_answers(1))
    answers["mot_story_1"] = "bogus_option"
    answers["not_a_question"] = "whatever"

    cleaned = motivation.filter_answers(answers)
    assert "mot_story_1" not in cleaned
    assert "not_a_question" not in cleaned
    assert len(cleaned) == 23

    saved = persona.save_provider(conn, "motivation", answers)
    assert saved["result"]["completed"] is False


@pytest.mark.skipif(not DB_PATH.exists(), reason="本地词库不存在")
def test_every_used_tag_exists_in_database():
    connection = sqlite3.connect(DB_PATH)
    try:
        names = {row[0] for row in connection.execute("select name from tags")}
    finally:
        connection.close()

    used = set()
    for question in motivation.QUESTIONS:
        for option in question["options"]:
            used.update((option.get("tags") or {}).keys())
    for mapping in motivation.DIMENSION_TAGS.values():
        for group in mapping.values():
            used.update(name for name, _ in group)

    missing = sorted(used - names)
    assert missing == []
