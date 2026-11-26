from __future__ import annotations

import pytest

from app.recommend import persona
from app.recommend.engine import UserProfile, _profile_source_name
from app.repository import get_settings


class FakeIndex:
    """build_tag_profile 只依赖 tag_names，用最小替身避免建库。"""

    tag_names = {1: "Mystery", 2: "Romance", 3: "Drama"}


def _library_profile() -> UserProfile:
    return UserProfile(
        vector={1: 1.0},
        negative_vector={},
        company_weights={},
        liked_work_ids=[],
        disliked_work_ids=set(),
        year_center=None,
        length_center=None,
        has_profile=True,
    )


def test_registry_exposes_quiz_metadata():
    assert "quiz" in persona.provider_keys()
    items = persona.list_providers({})
    quiz = next(item for item in items if item["key"] == "quiz")
    assert quiz["title"] == "口味测试"
    assert quiz["kind"] == "questionnaire"
    assert quiz["question_count"] == 8
    assert quiz["completed"] is False


def test_source_pattern_covers_every_registered_provider():
    pattern = persona.source_pattern()
    for key in persona.provider_keys():
        assert key in pattern
    for base in ("auto", "library", "all"):
        assert base in pattern


def test_provider_payload_and_save_roundtrip(conn):
    empty = persona.provider_payload(conn, "quiz")
    assert empty["result"]["completed"] is False
    assert empty["questions"]

    saved = persona.save_provider(conn, "quiz", {"q_story": "story_plot"})
    assert saved["result"]["tags"]["Drama"] == pytest.approx(1.2)
    assert saved["result"]["completed"] is False

    settings = get_settings(conn)
    # 新结构可读，同时保留了旧的 quiz_answers / quiz_profile。
    assert settings["persona_profiles"]["quiz"]["profile"]["tags"]["Drama"] == pytest.approx(1.2)
    assert settings["quiz_answers"] == {"q_story": "story_plot"}
    assert settings["quiz_profile"]["tags"]["Drama"] == pytest.approx(1.2)


def test_unknown_provider_raises_keyerror(conn):
    with pytest.raises(KeyError):
        persona.provider_payload(conn, "not_a_provider")
    with pytest.raises(KeyError):
        persona.save_provider(conn, "not_a_provider", {})


def test_legacy_quiz_settings_are_migrated_for_reads(conn):
    from app.repository import set_settings

    set_settings(
        conn,
        {
            "quiz_answers": {"q_story": "story_plot"},
            "quiz_profile": {"tags": {"Drama": 1.2}, "labels": ["剧情向"], "completed": False},
        },
    )
    items = {item["key"]: item for item in persona.list_providers(get_settings(conn))}
    assert items["quiz"]["completed"] is False
    profile = persona.resolve_profile(
        conn, FakeIndex(), "quiz", _library_profile(), get_settings(conn)
    )
    assert 3 in profile.vector


def test_build_tag_profile_normalizes_and_skips_unknown_tags():
    result = {
        "tags": {"Mystery": 1.5, "romance": 1.0, "Nonexistent Tag": 9.0},
        "labels": ["悬疑", "恋爱"],
        "year_center": "2018",
        "length_center": 600,
    }
    profile = persona.build_tag_profile(result, FakeIndex(), "quiz")
    assert set(profile.vector) == {1, 2}
    assert profile.vector[1] > profile.vector[2]
    assert profile.has_profile is True
    assert profile.source == "quiz"
    assert profile.quiz_labels == ["悬疑", "恋爱"]
    assert profile.year_center == pytest.approx(2018.0)
    assert profile.length_center == pytest.approx(600.0)


def test_merge_profiles_weighted_prefers_heavier_source():
    left = UserProfile(
        vector={1: 1.0},
        negative_vector={},
        company_weights={},
        liked_work_ids=[],
        disliked_work_ids=set(),
        year_center=2010.0,
        length_center=None,
        has_profile=True,
        source="quiz",
        quiz_labels=["悬疑"],
    )
    right = UserProfile(
        vector={2: 1.0},
        negative_vector={},
        company_weights={},
        liked_work_ids=[],
        disliked_work_ids=set(),
        year_center=2020.0,
        length_center=None,
        has_profile=True,
        source="motivation",
        quiz_labels=["恋爱"],
    )
    merged = persona.merge_profiles_weighted([(left, 0.3), (right, 0.1)])
    assert merged is not None
    assert merged.source == "all"
    assert merged.vector[1] > merged.vector[2]
    assert merged.year_center == pytest.approx(2012.5)
    assert merged.quiz_labels == ["悬疑", "恋爱"]


def test_merge_profiles_weighted_ignores_empty_profiles():
    assert persona.merge_profiles_weighted([]) is None
    empty = UserProfile(
        vector={},
        negative_vector={},
        company_weights={},
        liked_work_ids=[],
        disliked_work_ids=set(),
        year_center=None,
        length_center=None,
        has_profile=False,
    )
    assert persona.merge_profiles_weighted([(empty, 1.0)]) is None


def test_resolve_profile_by_source(conn):
    persona.save_provider(conn, "quiz", {"q_story": "story_plot"})
    settings = get_settings(conn)
    index = FakeIndex()
    library = _library_profile()

    assert persona.resolve_profile(conn, index, "library", library, settings) is library

    quiz_profile = persona.resolve_profile(conn, index, "quiz", library, settings)
    assert quiz_profile.source == "quiz"
    assert 3 in quiz_profile.vector  # Drama
    assert quiz_profile.vector[3] > quiz_profile.vector[1]  # Drama 权重高于 Mystery

    merged = persona.resolve_profile(conn, index, "all", library, settings)
    assert merged.source == "all"
    assert 1 in merged.vector and 3 in merged.vector

    missing = persona.resolve_profile(conn, index, "motivation", library, settings)
    assert missing.has_profile is False


def test_auto_source_follows_quiz_merge_home(conn):
    settings = get_settings(conn)
    assert _profile_source_name("auto", settings) == "library"

    persona.save_provider(conn, "quiz", {"q_story": "story_plot"})
    settings = get_settings(conn)
    assert _profile_source_name("auto", settings) == "all"

    settings["quiz_merge_home"] = False
    assert _profile_source_name("auto", settings) == "library"

    with pytest.raises(ValueError):
        _profile_source_name("bogus", settings)


def test_home_profile_sources_limits_merge(conn):
    persona.save_provider(conn, "quiz", {"q_story": "story_plot"})
    from app.repository import set_settings

    set_settings(conn, {"home_profile_sources": ["library"]})
    settings = get_settings(conn)
    merged = persona.resolve_profile(conn, FakeIndex(), "all", _library_profile(), settings)
    assert merged.source == "library"
    assert 3 not in merged.vector
