from __future__ import annotations

import re

from app.recommend import persona
from app.recommend.persona_enneagram import (
    CENTER_BY_TYPE,
    NEIGHBORS,
    QUESTIONS,
    TYPE_SLOTS,
    calculate,
    filter_answers,
)
from app.repository import get_settings

ALL_TYPES = tuple(range(1, 10))


def _option_map(question: dict, type_no: int) -> str:
    return next(option["id"] for option in question["options"] if option["type"] == type_no)


def _answers_for_type(type_no: int) -> dict[str, str]:
    """在出现该类型的每道题上都选它（其余题留空）。"""
    return {
        question["id"]: _option_map(question, type_no)
        for question in QUESTIONS
        if any(option["type"] == type_no for option in question["options"])
    }


def _complete_answers() -> dict[str, str]:
    """每道题都作答，用于验证 completed 与分数归一化。"""
    return {
        question["id"]: question["options"][index % len(question["options"])]["id"]
        for index, question in enumerate(QUESTIONS)
    }


def test_questions_shape_and_option_uniqueness():
    assert len(QUESTIONS) == 18
    question_ids = [question["id"] for question in QUESTIONS]
    assert len(set(question_ids)) == len(QUESTIONS)

    option_ids: list[str] = []
    for question in QUESTIONS:
        assert question["title"]
        options = question["options"]
        assert len(options) == 4
        assert len({option["id"] for option in options}) == 4
        assert len({option["type"] for option in options}) == 4
        for option in options:
            assert option["label"]
            assert option["type"] in ALL_TYPES
            assert option["tags"]
            assert all(weight > 0 for weight in option["tags"].values())
            option_ids.extend([option["id"]])
    assert len(set(option_ids)) == len(option_ids)

    # 九型各出现 8 次，合计 72 个选项。
    assert TYPE_SLOTS == {type_no: 8 for type_no in ALL_TYPES}


def test_same_type_answers_pick_that_main_type_and_adjacent_wing():
    for type_no in ALL_TYPES:
        result = calculate(_answers_for_type(type_no))

        assert result["scores"][str(type_no)] == 100
        assert result["code"].startswith(f"{type_no}w")
        assert re.fullmatch(r"[1-9]w[1-9] .+", result["code"])
        assert result["wing"] in NEIGHBORS[type_no]
        assert result["center"] == CENTER_BY_TYPE[type_no]
        assert result["labels"][0]
        assert result["labels"][2] == result["center"]
        # 只答了 8/18 题，不应算完成。
        assert result["completed"] is False
        assert result["tags"]


def test_wing_tie_prefers_larger_number():
    # 主型 4 得 4 票，3 与 5 各 2 票；侧翼同分时取编号更大的 5。
    answers = {
        "q01": _option_map(QUESTIONS[0], 4),
        "q04": _option_map(QUESTIONS[3], 4),
        "q10": _option_map(QUESTIONS[9], 4),
        "q13": _option_map(QUESTIONS[12], 4),
        "q03": _option_map(QUESTIONS[2], 3),
        "q12": _option_map(QUESTIONS[11], 3),
        "q02": _option_map(QUESTIONS[1], 5),
        "q11": _option_map(QUESTIONS[10], 5),
    }
    result = calculate(answers)
    assert result["code"].startswith("4w5")
    assert result["wing"] == 5
    assert result["scores"]["4"] == 50


def test_invalid_answers_are_ignored_and_empty_result_is_safe():
    invalid = {
        "q01": "not_an_option",
        "nope": "q01_t1",
        "q02": 123,  # type: ignore[dict-item]
        "q03": {"nested": "value"},  # type: ignore[dict-item]
    }
    assert filter_answers(invalid) == {}
    assert calculate(invalid) == calculate({})

    empty = calculate({})
    assert empty["tags"] == {}
    assert empty["labels"] == []
    assert empty["code"] == ""
    assert empty["completed"] is False
    assert empty["wing"] is None
    assert empty["center"] is None
    assert empty["scores"] == {str(type_no): 0 for type_no in ALL_TYPES}
    assert empty["year_center"] is None
    assert empty["length_center"] is None


def test_complete_answers_mark_completed_and_scores_stay_in_range():
    result = calculate(_complete_answers())
    assert result["completed"] is True
    assert len(result["scores"]) == 9
    for score in result["scores"].values():
        assert isinstance(score, int)
        assert 0 <= score <= 100
    assert sum(result["scores"].values()) > 0
    assert result["wing"] in NEIGHBORS[int(result["code"][0])]


def test_provider_is_registered_with_metadata(conn):
    assert "enneagram" in persona.provider_keys()
    assert persona.get_provider("enneagram").KEY == "enneagram"

    payload = persona.provider_payload(conn, "enneagram")
    assert payload["key"] == "enneagram"
    assert payload["title"] == "九型人格"
    assert payload["kind"] == "questionnaire"
    assert payload["group"] == "fun"
    assert payload["question_count"] == 18
    assert payload["notice"] == "娱乐向自我探索，不作为心理诊断。"
    assert payload["result"]["completed"] is False


def test_save_provider_roundtrip(conn):
    answers = _answers_for_type(4)
    saved = persona.save_provider(conn, "enneagram", answers)

    assert saved["answers"] == answers
    assert saved["result"]["code"].startswith("4w")
    assert saved["result"]["completed"] is False

    settings = get_settings(conn)
    bucket = settings["persona_profiles"]["enneagram"]
    assert bucket["answers"] == answers
    assert bucket["profile"]["wing"] == saved["result"]["wing"]
    assert bucket["updated_at"]

    again = persona.provider_payload(conn, "enneagram")
    assert again["result"] == saved["result"]

    listed = {item["key"]: item for item in persona.list_providers(settings)}
    assert listed["enneagram"]["completed"] is False
    assert listed["enneagram"]["code"] == saved["result"]["code"]
