from __future__ import annotations

import pytest

from app.recommend import persona
from app.recommend.persona_zodiac import KEY, QUESTIONS, SIGNS, calculate
from app.repository import get_settings


def test_metadata_and_sign_table_shape():
    assert KEY == "zodiac"
    assert QUESTIONS == []
    assert len(SIGNS) == 12
    assert len({sign["key"] for sign in SIGNS}) == 12
    assert len({sign["name"] for sign in SIGNS}) == 12

    for sign in SIGNS:
        assert sign["name"].endswith("座")
        assert sign["element"] in {"火", "土", "风", "水"}
        assert sign["mode"] in {"基本", "固定", "变动"}
        assert len(sign["labels"]) >= 2
        assert 3 <= len(sign["tags"]) <= 5
        assert all(isinstance(name, str) and name for name in sign["tags"])
        assert all(weight > 0 for weight in sign["tags"].values())


def test_scorpio_normal_calculation():
    result = calculate({"birthday": "1996-11-03"})

    assert result["completed"] is True
    assert result["code"] == "天蝎座·水象·固定宫"
    assert result["labels"] == ["水象", "固定宫", "深情专注"]
    assert result["scores"] == {"element": "水", "mode": "固定"}
    assert "Thriller" in result["tags"]
    assert "Revenge" in result["tags"]
    assert result["year_center"] is None
    assert result["length_center"] is None


@pytest.mark.parametrize(
    ("birthday", "sign_name"),
    [
        ("2000-01-01", "摩羯座"),
        ("2000-01-19", "摩羯座"),
        ("2000-01-20", "水瓶座"),
        ("2000-02-18", "水瓶座"),
        ("2000-02-19", "双鱼座"),
        ("2000-03-20", "双鱼座"),
        ("2000-03-21", "白羊座"),
        ("2000-04-19", "白羊座"),
        ("2000-04-20", "金牛座"),
        ("2000-05-20", "金牛座"),
        ("2000-05-21", "双子座"),
        ("2000-06-21", "双子座"),
        ("2000-06-22", "巨蟹座"),
        ("2000-07-22", "巨蟹座"),
        ("2000-07-23", "狮子座"),
        ("2000-08-22", "狮子座"),
        ("2000-08-23", "处女座"),
        ("2000-09-22", "处女座"),
        ("2000-09-23", "天秤座"),
        ("2000-10-23", "天秤座"),
        ("2000-10-24", "天蝎座"),
        ("2000-11-22", "天蝎座"),
        ("2000-11-23", "射手座"),
        ("2000-12-21", "射手座"),
        ("2000-12-22", "摩羯座"),
        ("2000-12-31", "摩羯座"),
    ],
)
def test_sun_sign_boundaries(birthday: str, sign_name: str):
    result = calculate({"birthday": birthday})

    assert result["completed"] is True
    assert result["code"].startswith(sign_name)


@pytest.mark.parametrize(
    ("birthday", "sign_name"),
    [
        ("11-03", "天蝎座"),
        ("1-20", "水瓶座"),
        ("02-29", "双鱼座"),
    ],
)
def test_month_day_format_is_supported(birthday: str, sign_name: str):
    result = calculate({"birthday": birthday})

    assert result["completed"] is True
    assert result["code"].startswith(sign_name)


@pytest.mark.parametrize(
    "answers",
    [
        {},
        {"birthday": ""},
        {"birthday": "   "},
        {"birthday": None},
        {"birthday": 19961103},
        {"birthday": "1996-13-01"},
        {"birthday": "1996-00-10"},
        {"birthday": "1996-02-30"},
        {"birthday": "1996-11-00"},
        {"birthday": "1996-11-03T00:00:00"},
        {"birthday": "1996/11/03"},
        {"birthday": "not-a-date"},
        {"birthday": "96-11-03"},
        None,
        "1996-11-03",
    ],
)
def test_invalid_birthday_returns_empty_incomplete_result(answers):
    result = calculate(answers)

    assert result["code"] == ""
    assert result["labels"] == []
    assert result["tags"] == {}
    assert result["completed"] is False
    assert result["scores"] == {}


def test_every_month_maps_to_a_complete_profile():
    for month in range(1, 13):
        result = calculate({"birthday": f"2000-{month:02d}-15"})
        assert result["completed"] is True
        assert result["code"]
        assert 3 <= len(result["tags"]) <= 5
        assert result["scores"]["element"] in {"火", "土", "风", "水"}
        assert result["scores"]["mode"] in {"基本", "固定", "变动"}


def test_provider_registration_and_metadata():
    assert "zodiac" in persona.provider_keys()
    items = {item["key"]: item for item in persona.list_providers({})}
    meta = items["zodiac"]
    assert meta["title"] == "十二星座"
    assert meta["kind"] == "birthday"
    assert meta["group"] == "fun"
    assert meta["question_count"] == 0
    assert meta["completed"] is False


def test_save_provider_roundtrip(conn):
    empty = persona.provider_payload(conn, "zodiac")
    assert empty["result"]["completed"] is False
    assert empty["questions"] == []

    saved = persona.save_provider(conn, "zodiac", {"birthday": "1996-11-03"})
    assert saved["result"]["completed"] is True
    assert saved["result"]["code"] == "天蝎座·水象·固定宫"
    assert saved["answers"] == {"birthday": "1996-11-03"}

    settings = get_settings(conn)
    bucket = settings["persona_profiles"]["zodiac"]
    assert bucket["profile"]["completed"] is True
    assert bucket["answers"]["birthday"] == "1996-11-03"

    payload = persona.provider_payload(conn, "zodiac")
    assert payload["result"]["completed"] is True
    assert payload["result"]["tags"]["Thriller"] == pytest.approx(1.2)


def test_invalid_birthday_can_be_saved_without_crashing(conn):
    saved = persona.save_provider(conn, "zodiac", {"birthday": "1996-02-30"})

    assert saved["result"]["completed"] is False
    assert saved["result"]["tags"] == {}
    assert saved["answers"] == {"birthday": "1996-02-30"}
