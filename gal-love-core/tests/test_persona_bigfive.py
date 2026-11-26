from __future__ import annotations

import pytest

from app.recommend import persona
from app.recommend.persona_bigfive import (
    DIMENSIONS,
    KEY,
    QUESTIONS,
    TAG_MAP,
    calculate,
    filter_answers,
)
from app.repository import get_settings


def _answer_all(option_id: str) -> dict[str, str]:
    return {question["id"]: option_id for question in QUESTIONS}


def _neutral_with(dimension: str, positive: str, reverse: str) -> dict[str, str]:
    answers = _answer_all("0")
    for question in QUESTIONS:
        if question["dimension"] != dimension:
            continue
        answers[question["id"]] = reverse if question["reverse"] else positive
    return answers


def test_questions_shape_and_dimension_balance():
    assert KEY == "bigfive"
    assert len(QUESTIONS) == 10
    question_ids = [question["id"] for question in QUESTIONS]
    assert len(set(question_ids)) == len(QUESTIONS)

    for dimension in DIMENSIONS:
        items = [question for question in QUESTIONS if question["dimension"] == dimension]
        assert len(items) == 2
        assert {bool(question["reverse"]) for question in items} == {True, False}

    for question in QUESTIONS:
        assert question["dimension"] in DIMENSIONS
        option_ids = [option["id"] for option in question["options"]]
        assert option_ids == ["-2", "-1", "0", "1", "2"]
        assert len(set(option_ids)) == len(option_ids)
        for option in question["options"]:
            assert option["label"]
            assert option["value"] in (-2, -1, 0, 1, 2)
            assert isinstance(option["tags"], dict)
            assert all(weight > 0 for weight in option["tags"].values())
            allowed = set(TAG_MAP[question["dimension"]]["high"]) | set(
                TAG_MAP[question["dimension"]]["low"]
            )
            assert set(option["tags"]).issubset(allowed)


def test_all_agree_does_not_max_out_reverse_dimensions():
    result = calculate(_answer_all("2"))

    assert result["completed"] is True
    # 每个维度一正一反向，全选“很同意”时正反相抵，不应得到满分。
    assert result["scores"] == {dimension: 50 for dimension in DIMENSIONS}
    assert result["tags"] == {}
    assert result["labels"] == ["开放性中", "尽责性中", "外向性中", "宜人性中", "神经质中"]
    assert result["code"] == "中开放·中尽责·中外向·中宜人·中神经质"


def test_all_disagree_is_also_neutral():
    result = calculate(_answer_all("-2"))

    assert result["scores"] == {dimension: 50 for dimension in DIMENSIONS}
    assert result["completed"] is True


def test_high_openness_generates_high_pole_tags():
    result = calculate(_neutral_with("O", positive="2", reverse="-2"))

    assert result["scores"]["O"] == 100
    assert result["scores"]["C"] == 50
    assert result["labels"][0] == "开放性高"
    assert result["code"].startswith("高开放")
    assert set(result["tags"]) == set(TAG_MAP["O"]["high"])
    assert result["tags"]["Science Fiction"] == pytest.approx(1.2)
    assert "School" not in result["tags"]


def test_low_openness_generates_low_pole_tags():
    result = calculate(_neutral_with("O", positive="-2", reverse="2"))

    assert result["scores"]["O"] == 0
    assert result["labels"][0] == "开放性低"
    assert result["code"].startswith("低开放")
    assert set(result["tags"]) == set(TAG_MAP["O"]["low"])
    assert result["tags"]["Slice of Life"] == pytest.approx(1.2)


def test_high_neuroticism_maps_to_horror_and_thriller():
    result = calculate(_neutral_with("N", positive="2", reverse="-2"))

    assert result["scores"]["N"] == 100
    assert result["labels"][-1] == "神经质高"
    assert result["code"].endswith("高神经质")
    assert set(result["tags"]) == set(TAG_MAP["N"]["high"])
    assert "Horror" in result["tags"]
    assert "Psychological Horror" in result["tags"]


def test_partial_and_empty_answers_are_not_completed():
    partial = calculate({QUESTIONS[0]["id"]: "2"})
    assert partial["completed"] is False
    assert partial["scores"]["O"] == 75
    assert partial["tags"]["Science Fiction"] == pytest.approx(0.6)

    empty = calculate({})
    assert empty["completed"] is False
    assert empty["scores"] == {dimension: 50 for dimension in DIMENSIONS}
    assert empty["tags"] == {}
    assert empty["code"] == "中开放·中尽责·中外向·中宜人·中神经质"
    assert empty["year_center"] is None
    assert empty["length_center"] is None


def test_filter_answers_keeps_only_valid_pairs():
    invalid = {
        "unknown_question": "2",
        "bf_o_pos": "99",
        "bf_o_neg": {"nested": "value"},
        123: "2",
    }
    assert filter_answers(invalid) == {}
    assert filter_answers(None) == {}
    assert calculate(invalid) == calculate({})

    mixed = filter_answers({**invalid, "bf_o_pos": "-1"})
    assert mixed == {"bf_o_pos": "-1"}


def test_provider_registration_and_metadata():
    assert "bigfive" in persona.provider_keys()
    items = {item["key"]: item for item in persona.list_providers({})}
    meta = items["bigfive"]
    assert meta["title"] == "大五人格"
    assert meta["kind"] == "questionnaire"
    assert meta["group"] == "serious"
    assert meta["question_count"] == 10
    assert meta["completed"] is False


def test_save_provider_roundtrip(conn):
    answers = _answer_all("2")
    saved = persona.save_provider(conn, "bigfive", answers)

    assert saved["result"]["completed"] is True
    assert saved["result"]["scores"] == {dimension: 50 for dimension in DIMENSIONS}
    assert saved["answers"] == answers
    assert len(saved["questions"]) == 10

    settings = get_settings(conn)
    bucket = settings["persona_profiles"]["bigfive"]
    assert bucket["profile"]["completed"] is True
    assert bucket["answers"] == answers

    payload = persona.provider_payload(conn, "bigfive")
    assert payload["result"]["completed"] is True
    assert payload["question_count"] == 10
