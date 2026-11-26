"""十二星座画像：用生日得到太阳星座并映射到库内真实标签。

纯娱乐玩法，不涉及题目。支持 ``YYYY-MM-DD`` 与 ``MM-DD`` 两种生日写法，
非法或缺失生日时返回未完成画像，不抛异常。
"""

from __future__ import annotations

from datetime import datetime

KEY = "zodiac"
TITLE = "十二星座"
SUBTITLE = "填个生日，看看星座口味"
KIND = "birthday"
GROUP = "fun"
ESTIMATED_MINUTES = 1
QUESTIONS: list[dict] = []
NOTICE = "纯娱乐玩法，标签映射不代表科学结论。"

# start 为太阳星座起始日（含当天）。摩羯座跨年，单独兜底。
SIGNS: list[dict] = [
    {
        "key": "aries",
        "name": "白羊座",
        "element": "火",
        "mode": "基本",
        "start": (3, 21),
        "labels": ["火象", "基本宫", "直率热烈"],
        "tags": {"Action": 1.2, "Sword Combat": 0.8, "High Fantasy": 0.6},
    },
    {
        "key": "taurus",
        "name": "金牛座",
        "element": "土",
        "mode": "固定",
        "start": (4, 20),
        "labels": ["土象", "固定宫", "稳定务实"],
        "tags": {
            "Slice of Life": 1.2,
            "Food Discussions": 0.9,
            "Cafe": 0.7,
            "Slow-burn Romance": 0.5,
        },
    },
    {
        "key": "gemini",
        "name": "双子座",
        "element": "风",
        "mode": "变动",
        "start": (5, 21),
        "labels": ["风象", "变动宫", "机敏多变"],
        "tags": {"Comedy": 1.2, "Parody": 0.9, "School Life Comedy": 0.7},
    },
    {
        "key": "cancer",
        "name": "巨蟹座",
        "element": "水",
        "mode": "基本",
        "start": (6, 22),
        "labels": ["水象", "基本宫", "温柔念旧"],
        "tags": {
            "Romance": 1.2,
            "Nakige": 1.0,
            "Family Drama": 0.8,
            "Slice of Life Drama": 0.6,
        },
    },
    {
        "key": "leo",
        "name": "狮子座",
        "element": "火",
        "mode": "固定",
        "start": (7, 23),
        "labels": ["火象", "固定宫", "自信耀眼"],
        "tags": {"Drama": 1.2, "Royal Protagonist": 0.9, "Royal Heroine": 0.7, "Comedy": 0.5},
    },
    {
        "key": "virgo",
        "name": "处女座",
        "element": "土",
        "mode": "变动",
        "start": (8, 23),
        "labels": ["土象", "变动宫", "细致理性"],
        "tags": {"Mystery": 1.2, "Detective Work": 1.0, "Murder Mystery": 0.7},
    },
    {
        "key": "libra",
        "name": "天秤座",
        "element": "风",
        "mode": "基本",
        "start": (9, 23),
        "labels": ["风象", "基本宫", "温和平衡"],
        "tags": {
            "Romance": 1.2,
            "Love Triangle": 0.9,
            "Dramatic Love Triangle": 0.7,
            "Romance Between Protagonists": 0.5,
        },
    },
    {
        "key": "scorpio",
        "name": "天蝎座",
        "element": "水",
        "mode": "固定",
        "start": (10, 24),
        "labels": ["水象", "固定宫", "深情专注"],
        "tags": {
            "Thriller": 1.2,
            "Revenge": 1.0,
            "Psychological Horror": 0.8,
            "Dark Fantasy": 0.6,
        },
    },
    {
        "key": "sagittarius",
        "name": "射手座",
        "element": "火",
        "mode": "变动",
        "start": (11, 23),
        "labels": ["火象", "变动宫", "自由冒险"],
        "tags": {"Fantasy": 1.2, "High Fantasy": 0.9, "Journey": 0.8, "Time Travel": 0.5},
    },
    {
        "key": "capricorn",
        "name": "摩羯座",
        "element": "土",
        "mode": "基本",
        "start": (12, 22),
        "labels": ["土象", "基本宫", "沉稳执着"],
        "tags": {"Drama": 1.2, "Politics": 1.0, "War": 0.8, "Crime": 0.6},
    },
    {
        "key": "aquarius",
        "name": "水瓶座",
        "element": "风",
        "mode": "固定",
        "start": (1, 20),
        "labels": ["风象", "固定宫", "独立求新"],
        "tags": {
            "Science Fiction": 1.2,
            "Metafiction": 1.0,
            "Time Loop": 0.8,
            "Unreliable Narrator": 0.6,
        },
    },
    {
        "key": "pisces",
        "name": "双鱼座",
        "element": "水",
        "mode": "变动",
        "start": (2, 19),
        "labels": ["水象", "变动宫", "浪漫共情"],
        "tags": {
            "Utsuge": 1.2,
            "Life and Death Drama": 0.9,
            "Nakige": 0.7,
            "Drama": 0.5,
        },
    },
]

_SIGNS_BY_START = sorted(SIGNS, key=lambda sign: sign["start"])
_CAPRICORN = next(sign for sign in SIGNS if sign["key"] == "capricorn")


def _parse_birthday(value: object) -> tuple[int, int] | None:
    """解析 YYYY-MM-DD / MM-DD，返回 (月, 日)；非法输入返回 None。"""
    if not isinstance(value, str):
        return None
    parts = value.strip().split("-")
    if len(parts) == 3:
        year_text, month_text, day_text = parts
        if len(year_text) != 4 or not year_text.isdigit():
            return None
        year = int(year_text)
    elif len(parts) == 2:
        month_text, day_text = parts
        year = 2000  # 闰年，方便 02-29 这类无年份生日通过校验
    else:
        return None
    try:
        parsed = datetime(year, int(month_text), int(day_text))
    except (TypeError, ValueError):
        return None
    return parsed.month, parsed.day


def _sign_for(month: int, day: int) -> dict:
    for sign in reversed(_SIGNS_BY_START):
        if (month, day) >= sign["start"]:
            return sign
    return _CAPRICORN


def _empty_result() -> dict:
    return {
        "code": "",
        "labels": [],
        "tags": {},
        "year_center": None,
        "length_center": None,
        "completed": False,
        "scores": {},
    }


def calculate(answers: dict[str, str] | None) -> dict:
    """根据生日返回星座画像；任何异常输入都退化为未完成画像。"""
    if not isinstance(answers, dict):
        return _empty_result()
    birthday = _parse_birthday(answers.get("birthday"))
    if birthday is None:
        return _empty_result()

    sign = _sign_for(*birthday)
    return {
        "code": f"{sign['name']}·{sign['element']}象·{sign['mode']}宫",
        "labels": list(sign["labels"]),
        "tags": dict(sign["tags"]),
        "year_center": None,
        "length_center": None,
        "completed": True,
        "scores": {"element": sign["element"], "mode": sign["mode"]},
    }
