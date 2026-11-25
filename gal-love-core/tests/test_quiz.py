from __future__ import annotations

from app.recommend.quiz import AXIS_ORDER, QUESTIONS, calculate_profile, filter_answers


def _valid_question_ids() -> set[str]:
    return {question["id"] for question in QUESTIONS}


def test_questions_shape_and_real_tag_names():
    assert len(QUESTIONS) == 8
    assert len(_valid_question_ids()) == len(QUESTIONS)
    for question in QUESTIONS:
        assert question["id"]
        assert question["title"]
        option_ids = [option["id"] for option in question["options"]]
        assert len(option_ids) >= 2
        assert len(set(option_ids)) == len(option_ids)
        for option in question["options"]:
            assert option["label"]
            assert option["tags"]
            assert all(isinstance(name, str) and name for name in option["tags"])
            assert all(weight > 0 for weight in option["tags"].values())
            assert set(option["axes"]).issubset(AXIS_ORDER)


def test_calculate_profile_accumulates_weights_and_axis_labels():
    result = calculate_profile(
        {
            "q_story": "story_plot",  # Drama 1.2, Mystery 0.6
            "q_atmosphere": "atm_mystery",  # Mystery 1.4, Thriller 0.6
            "q_pace": "pace_slow",  # Slice of Life 1.0, Drama 0.6
            "q_ending": "end_branch",  # Multiple Endings 1.4, Branching Plot 1.0
        }
    )

    assert result["tags"]["Mystery"] == 2.0
    assert result["tags"]["Drama"] == 1.8
    assert result["tags"]["Thriller"] == 0.6
    assert result["labels"] == ["剧情向", "悬疑", "慢热", "多结局"]
    assert result["code"] == "剧情向·悬疑·慢热·多结局"
    assert result["completed"] is False
    assert result["year_center"] is None
    assert result["length_center"] is None


def test_calculate_profile_ignores_invalid_answers():
    invalid = {
        "unknown_question": "story_plot",
        "q_story": "unknown_option",
        "q_atmosphere": 123,  # type: ignore[dict-item]
        "q_pace": {"nested": "value"},  # type: ignore[dict-item]
    }

    assert filter_answers(invalid) == {}
    assert calculate_profile(invalid) == calculate_profile({})
    empty = calculate_profile({})
    assert empty["tags"] == {}
    assert empty["completed"] is False
    assert len(empty["labels"]) == 4
    assert len(empty["code"].split("·")) == 4


def test_calculate_profile_keeps_only_valid_pairs_and_marks_completed():
    partial = calculate_profile({"q_story": "story_plot", "q_ending": "bogus"})
    assert set(partial["tags"]) == {"Drama", "Mystery"}
    assert partial["completed"] is False

    complete = calculate_profile(
        {
            "q_story": "story_plot",
            "q_atmosphere": "atm_bright",
            "q_pace": "pace_short",  # length 180
            "q_ending": "end_true",
            "q_world": "world_school",  # year 2018
            "q_protagonist": "hero_male",
            "q_content": "content_none",
            "q_time": "time_long",  # length 3600
            "not_a_question": "whatever",
        }
    )
    assert complete["completed"] is True
    assert complete["year_center"] == 2018
    assert complete["length_center"] == 1890
    assert "One True End" in complete["tags"]
