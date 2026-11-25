from __future__ import annotations

from app.ingest.bangumi import looks_like_avg, parse_subject
from app.ingest.vndb import parse_vn


VNDB_VN = {
    "id": "v17",
    "title": "Ever17 -the out of infinity-",
    "alttitle": "Ever17 -the out of infinity-",
    "titles": [
        {"lang": "en", "title": "Ever17", "latin": None, "official": True, "main": False},
        {"lang": "zh-Hans", "title": "时空轮回", "latin": None, "official": True, "main": True},
        {"lang": "ja", "title": "Ever17", "latin": None, "official": True, "main": False},
    ],
    "aliases": ["E17"],
    "released": "2002-08-29",
    "languages": ["en", "ja", "zh-Hans"],
    "platforms": ["win", "psp"],
    "image": {"url": "https://t.vndb.org/cv/17.jpg", "sexual": 0.2},
    "length": 3,
    "length_minutes": 2100,
    "description": "A visual novel set in an underwater theme park.",
    "rating": 84.5,
    "votecount": 4200,
    "tags": [
        {"id": "g1", "name": "Science Fiction", "rating": 2.5, "spoiler": 0, "category": "cont"},
        {"id": "g2", "name": "Mystery", "rating": 2.0, "spoiler": 0, "category": "cont"},
    ],
    "developers": [{"id": "p1", "name": "KID"}],
}


BANGUMI_SUBJECT = {
    "id": 12345,
    "type": 4,
    "name": "Ever17 -the out of infinity-",
    "name_cn": "时空轮回",
    "summary": "海底主题公园的悬疑视觉小说。",
    "date": "2002-08-29",
    "images": {"large": "https://lain.bgm.tv/pic/cover/l/xx.jpg"},
    "rating": {"score": 8.8, "total": 3210},
    "collection_total": 5000,
    "tags": [
        {"name": "视觉小说", "count": 180},
        {"name": "悬疑", "count": 90},
    ],
    "infobox": [
        {"key": "开发", "value": "KID"},
        {"key": "平台", "value": [{"v": "PC"}, {"v": "PSP"}]},
        {"key": "游戏时间", "value": "30小时"},
        {"key": "别名", "value": ["E17", "时空轮回"]},
    ],
}


def test_parse_vndb_prefers_chinese_title_and_normalizes_fields():
    payload = parse_vn(VNDB_VN)

    assert payload["source"] == "vndb"
    assert payload["external_id"] == "v17"
    assert payload["title"] == "时空轮回"
    assert payload["title_zh"] == "时空轮回"
    assert payload["original_title"] == "Ever17 -the out of infinity-"
    assert payload["release_date"] == "2002-08-29"
    assert payload["release_year"] == 2002
    assert payload["length_minutes"] == 2100
    assert payload["vndb_rating"] == 84.5
    assert payload["vndb_votecount"] == 4200
    assert payload["nsfw"] is False
    assert payload["cover_url"] == "https://t.vndb.org/cv/17.jpg"
    assert {company["name"] for company in payload["companies"]} == {"KID"}
    assert [tag["name"] for tag in payload["tags"]] == ["Science Fiction", "Mystery"]
    assert payload["tags"][0]["weight"] == 2.5
    assert "E17" in payload["aliases"]
    assert any(item["lang"].startswith("zh") for item in payload["titles"])


def test_parse_vndb_detects_nsfw():
    vn = dict(VNDB_VN)
    vn["tags"] = [
        {"id": "g9", "name": "Sexual Content", "rating": 2.0, "spoiler": 0, "category": "ero"}
    ]
    payload = parse_vn(vn)
    assert payload["nsfw"] is True


def test_parse_bangumi_extracts_infobox_and_rating():
    payload = parse_subject(BANGUMI_SUBJECT)

    assert payload["source"] == "bangumi"
    assert payload["external_id"] == "12345"
    assert payload["title"] == "时空轮回"
    assert payload["title_zh"] == "时空轮回"
    assert payload["original_title"] == "Ever17 -the out of infinity-"
    assert payload["release_year"] == 2002
    assert payload["bangumi_rating"] == 8.8
    assert payload["bangumi_votecount"] == 3210
    assert payload["length_minutes"] == 1800
    assert {company["name"] for company in payload["companies"]} == {"KID"}
    assert {platform.casefold() for platform in payload["platforms"]} == {"pc", "psp"}
    assert payload["cover_url"].endswith("xx.jpg")
    assert payload["nsfw"] is False
    assert [tag["name"] for tag in payload["tags"]] == ["视觉小说", "悬疑"]
    assert payload["tags"][0]["weight"] > 1.0


def test_bangumi_avg_filter():
    assert looks_like_avg(BANGUMI_SUBJECT) is True

    non_avg = dict(BANGUMI_SUBJECT)
    non_avg["tags"] = [{"name": "动作", "count": 10}]
    non_avg["summary"] = "一款动作游戏。"
    assert looks_like_avg(non_avg) is False

    untagged = dict(BANGUMI_SUBJECT)
    untagged["tags"] = []
    untagged["summary"] = "A game without tags."
    assert looks_like_avg(untagged) is True
