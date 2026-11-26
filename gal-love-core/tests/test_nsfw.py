from __future__ import annotations

from app.nsfw import allows, normalize_policy, sql_clause
from app.recommend.engine import recommend
from app.repository import get_settings, search_works, set_settings

from .helpers import add_work


def _seed(conn):
    sfw = add_work(conn, title="All Ages Story", tags=["drama"], rating=9.0)
    story = add_work(
        conn, title="Adult Story", tags=["drama", "mystery"], rating=8.9, nsfw=True
    )
    nukige = add_work(conn, title="Adult Nukige", tags=["nukige"], rating=8.8, nsfw=True)
    return sfw, story, nukige


def test_normalize_policy_accepts_legacy_values():
    assert normalize_policy(True) == "all"
    assert normalize_policy(False) == "off"
    assert normalize_policy(None) == "off"
    assert normalize_policy("STORY") == "story"
    assert normalize_policy("story_only") == "story"
    assert normalize_policy("nonsense") == "off"


def test_allows_matrix():
    assert allows("off", nsfw=False) is True
    assert allows("off", nsfw=True) is False
    assert allows("story", nsfw=True, is_nukige=False) is True
    assert allows("story", nsfw=True, is_nukige=True) is False
    assert allows("all", nsfw=True, is_nukige=True) is True


def test_sql_clause_for_each_level():
    assert sql_clause("off") == "w.nsfw = 0"
    assert "nukige" in (sql_clause("story") or "").casefold()
    assert sql_clause("all") is None
    assert sql_clause("off", work_alias="work") == "work.nsfw = 0"


def test_search_respects_policy(conn):
    _seed(conn)
    assert search_works(conn, nsfw_policy="off")["total"] == 1
    assert search_works(conn, nsfw_policy="story")["total"] == 2
    assert search_works(conn, nsfw_policy="all")["total"] == 3

    # 旧的布尔参数继续可用：False=off，True=all
    assert search_works(conn, include_nsfw=False)["total"] == 1
    assert search_works(conn, include_nsfw=True)["total"] == 3


def test_settings_translate_legacy_fields(conn):
    settings = get_settings(conn)
    assert settings["nsfw_policy"] == "off"
    assert settings["include_nsfw"] is False
    assert settings["home_profile_sources"] is None
    assert settings["quiz_merge_home"] is True

    set_settings(conn, {"include_nsfw": True})
    settings = get_settings(conn)
    assert settings["nsfw_policy"] == "all"
    assert settings["include_nsfw"] is True

    set_settings(conn, {"nsfw_policy": "story"})
    settings = get_settings(conn)
    assert settings["nsfw_policy"] == "story"
    assert settings["include_nsfw"] is False

    set_settings(conn, {"quiz_merge_home": False})
    settings = get_settings(conn)
    assert settings["home_profile_sources"] == ["library"]
    assert settings["quiz_merge_home"] is False

    set_settings(conn, {"home_profile_sources": ["library", "quiz"]})
    settings = get_settings(conn)
    assert settings["home_profile_sources"] == ["library", "quiz"]
    assert settings["quiz_merge_home"] is True


def test_recommend_respects_policy(conn):
    sfw, story, nukige = _seed(conn)

    off = {item["id"] for item in recommend(conn, limit=10, nsfw_policy="off")}
    assert off == {sfw}

    story_pool = {item["id"] for item in recommend(conn, limit=10, nsfw_policy="story")}
    assert story_pool == {sfw, story}

    all_pool = {item["id"] for item in recommend(conn, limit=10, nsfw_policy="all")}
    assert all_pool == {sfw, story, nukige}


def test_recommend_reads_policy_from_settings(conn):
    sfw, story, nukige = _seed(conn)
    set_settings(conn, {"nsfw_policy": "story"})

    ids = {item["id"] for item in recommend(conn, limit=10)}
    assert ids == {sfw, story}
