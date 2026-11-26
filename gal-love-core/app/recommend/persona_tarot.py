"""塔罗一抽：纯娱乐的主题抽取玩法。

牌面本身不写入设置，只把抽到牌面的标签权重汇总成一个临时画像，
直接注入推荐引擎，用来挑出与牌面气质相符的作品。
"""

from __future__ import annotations

import random
import sqlite3
from datetime import date
from typing import Any

from . import persona
from .engine import FeatureIndex, recommend

KEY = "tarot"
TITLE = "塔罗一抽"
SUBTITLE = "抽 1–3 张，由牌面决定今晚玩什么"
KIND = "draw"
GROUP = "play"
ESTIMATED_MINUTES = 1
QUESTIONS: list[dict[str, Any]] = []
NOTICE = "纯娱乐玩法，牌面只用于挑选推荐主题。"

SPREAD_POSITIONS: dict[int, list[str]] = {
    1: ["今日指引"],
    3: ["主题", "阻碍", "建议"],
}

# 22 张大阿卡纳。标签使用 VNDB 规范英文标签名，便于命中库内真实标签。
MAJOR_ARCANA: list[dict[str, Any]] = [
    {
        "id": "major-00",
        "name": "The Fool",
        "name_zh": "愚者",
        "tags": {"adventure": 1.0, "comedy": 0.6, "fantasy": 0.4},
        "themes": ["启程", "未知"],
        "meaning": "带着好奇心迈出第一步，未知本身就是礼物。",
    },
    {
        "id": "major-01",
        "name": "The Magician",
        "name_zh": "魔术师",
        "tags": {"magic": 1.0, "fantasy": 0.8, "drama": 0.3},
        "themes": ["创造", "掌控"],
        "meaning": "手边的资源已经足够，缺的只是动手去做。",
    },
    {
        "id": "major-02",
        "name": "The High Priestess",
        "name_zh": "女祭司",
        "tags": {"mystery": 1.0, "psychological": 0.8, "supernatural": 0.4},
        "themes": ["直觉", "秘密"],
        "meaning": "答案藏在沉默里，先听见自己的声音。",
    },
    {
        "id": "major-03",
        "name": "The Empress",
        "name_zh": "皇后",
        "tags": {"romance": 0.8, "slice of life": 0.8, "family": 0.5},
        "themes": ["丰饶", "温柔"],
        "meaning": "好好被照顾，也好好照顾喜欢的人。",
    },
    {
        "id": "major-04",
        "name": "The Emperor",
        "name_zh": "皇帝",
        "tags": {"historical": 0.8, "war": 0.5, "drama": 0.6},
        "themes": ["秩序", "责任"],
        "meaning": "规则带来安全感，也带来必须承担的重量。",
    },
    {
        "id": "major-05",
        "name": "The Hierophant",
        "name_zh": "教皇",
        "tags": {"philosophical": 0.8, "historical": 0.6, "drama": 0.4},
        "themes": ["传统", "信念"],
        "meaning": "旧的答案仍能指路，但需要你来重新解释。",
    },
    {
        "id": "major-06",
        "name": "The Lovers",
        "name_zh": "恋人",
        "tags": {"romance": 1.2, "drama": 0.6},
        "themes": ["羁绊", "选择"],
        "meaning": "心动的瞬间，也是一次必须做出的选择。",
    },
    {
        "id": "major-07",
        "name": "The Chariot",
        "name_zh": "战车",
        "tags": {"action": 1.0, "sports": 0.7, "adventure": 0.5},
        "themes": ["前进", "胜利"],
        "meaning": "把方向握紧，速度自然会替你开路。",
    },
    {
        "id": "major-08",
        "name": "Strength",
        "name_zh": "力量",
        "tags": {"drama": 0.6, "friendship": 0.6, "psychological": 0.4},
        "themes": ["勇气", "驯服"],
        "meaning": "真正的强大，是温柔地安抚内心的野兽。",
    },
    {
        "id": "major-09",
        "name": "The Hermit",
        "name_zh": "隐者",
        "tags": {"psychological": 0.9, "philosophical": 0.8, "slice of life": 0.4},
        "themes": ["独处", "内省"],
        "meaning": "暂时退后一步，独处会给出更清晰的答案。",
    },
    {
        "id": "major-10",
        "name": "Wheel of Fortune",
        "name_zh": "命运之轮",
        "tags": {"fantasy": 0.6, "drama": 0.6, "mystery": 0.4},
        "themes": ["转机", "循环"],
        "meaning": "轮盘正在转动，顺势而为比硬撑更有效。",
    },
    {
        "id": "major-11",
        "name": "Justice",
        "name_zh": "正义",
        "tags": {"detective": 0.9, "mystery": 0.7, "drama": 0.5},
        "themes": ["因果", "抉择"],
        "meaning": "每个选择都有代价，诚实地面对它。",
    },
    {
        "id": "major-12",
        "name": "The Hanged Man",
        "name_zh": "倒吊人",
        "tags": {"philosophical": 0.9, "tragedy": 0.6, "psychological": 0.5},
        "themes": ["等待", "换位"],
        "meaning": "停住不是放弃，换个角度世界就不同了。",
    },
    {
        "id": "major-13",
        "name": "Death",
        "name_zh": "死神",
        "tags": {"tragedy": 0.9, "horror": 0.6, "drama": 0.6},
        "themes": ["结束", "重生"],
        "meaning": "旧章节必须落幕，新故事才有位置开始。",
    },
    {
        "id": "major-14",
        "name": "Temperance",
        "name_zh": "节制",
        "tags": {"slice of life": 0.8, "drama": 0.6, "philosophical": 0.4},
        "themes": ["调和", "耐心"],
        "meaning": "把两种极端兑成一杯刚好入口的温度。",
    },
    {
        "id": "major-15",
        "name": "The Devil",
        "name_zh": "恶魔",
        "tags": {"psychological": 0.9, "horror": 0.7, "thriller": 0.6},
        "themes": ["欲望", "束缚"],
        "meaning": "看清让你上瘾的东西，锁链其实握在自己手里。",
    },
    {
        "id": "major-16",
        "name": "The Tower",
        "name_zh": "塔",
        "tags": {"thriller": 0.9, "horror": 0.8, "tragedy": 0.6},
        "themes": ["崩塌", "突变"],
        "meaning": "突如其来的崩塌，清空了本就不稳的地基。",
    },
    {
        "id": "major-17",
        "name": "The Star",
        "name_zh": "星星",
        "tags": {"drama": 0.7, "tearjerker": 0.6, "romance": 0.4},
        "themes": ["希望", "治愈"],
        "meaning": "在最低处抬头，仍有一颗星为你亮着。",
    },
    {
        "id": "major-18",
        "name": "The Moon",
        "name_zh": "月亮",
        "tags": {"mystery": 0.9, "horror": 0.7, "supernatural": 0.6},
        "themes": ["幻象", "潜意识"],
        "meaning": "雾里看到的未必是真相，先别急着下结论。",
    },
    {
        "id": "major-19",
        "name": "The Sun",
        "name_zh": "太阳",
        "tags": {"comedy": 0.9, "slice of life": 0.8, "romance": 0.4},
        "themes": ["明亮", "成就"],
        "meaning": "大大方方地开心，好事值得被看见。",
    },
    {
        "id": "major-20",
        "name": "Judgement",
        "name_zh": "审判",
        "tags": {"drama": 0.8, "mystery": 0.5, "philosophical": 0.5},
        "themes": ["觉醒", "召唤"],
        "meaning": "过去的回声在叫你，是时候回应它了。",
    },
    {
        "id": "major-21",
        "name": "The World",
        "name_zh": "世界",
        "tags": {"drama": 0.7, "fantasy": 0.6, "multiple endings": 0.5},
        "themes": ["完成", "圆满"],
        "meaning": "一圈走完，你终于可以安心地合上这本书。",
    },
]

_SUITS: list[dict[str, Any]] = [
    {
        "key": "wands",
        "name": "Wands",
        "name_zh": "权杖",
        "theme": "热情与行动",
        "tags": {"adventure": 1.0, "action": 0.8, "fantasy": 0.5},
    },
    {
        "key": "cups",
        "name": "Cups",
        "name_zh": "圣杯",
        "theme": "情感与关系",
        "tags": {"romance": 1.0, "drama": 0.8, "slice of life": 0.4},
    },
    {
        "key": "swords",
        "name": "Swords",
        "name_zh": "宝剑",
        "theme": "理智与冲突",
        "tags": {"mystery": 1.0, "thriller": 0.8, "psychological": 0.5},
    },
    {
        "key": "pentacles",
        "name": "Pentacles",
        "name_zh": "星币",
        "theme": "现实与积累",
        "tags": {"drama": 0.8, "slice of life": 0.8, "historical": 0.4},
    },
]

_RANKS: list[dict[str, Any]] = [
    {"key": "ace", "name": "Ace", "name_zh": "王牌", "theme": "新的起点", "tags": {"magic": 0.3}},
    {"key": "2", "name": "Two", "name_zh": "二", "theme": "抉择与平衡", "tags": {"friendship": 0.2}},
    {"key": "3", "name": "Three", "name_zh": "三", "theme": "合作与成长", "tags": {"friendship": 0.3}},
    {"key": "4", "name": "Four", "name_zh": "四", "theme": "安定与守护", "tags": {"family": 0.2}},
    {"key": "5", "name": "Five", "name_zh": "五", "theme": "摩擦与失去", "tags": {"tragedy": 0.2}},
    {"key": "6", "name": "Six", "name_zh": "六", "theme": "启程与回忆", "tags": {"travel": 0.3}},
    {"key": "7", "name": "Seven", "name_zh": "七", "theme": "试探与迷雾", "tags": {"psychological": 0.2}},
    {"key": "8", "name": "Eight", "name_zh": "八", "theme": "加速与专注", "tags": {"action": 0.2}},
    {"key": "9", "name": "Nine", "name_zh": "九", "theme": "坚持与焦虑", "tags": {"psychological": 0.2}},
    {"key": "10", "name": "Ten", "name_zh": "十", "theme": "收束与圆满", "tags": {"family": 0.2}},
    {"key": "page", "name": "Page", "name_zh": "侍从", "theme": "学习与好奇", "tags": {"school": 0.3}},
    {"key": "knight", "name": "Knight", "name_zh": "骑士", "theme": "冲锋与远行", "tags": {"adventure": 0.3}},
    {"key": "queen", "name": "Queen", "name_zh": "王后", "theme": "包容与直觉", "tags": {"romance": 0.2}},
    {"key": "king", "name": "King", "name_zh": "国王", "theme": "掌控与决断", "tags": {"war": 0.2}},
]


def _build_minor_arcana() -> list[dict[str, Any]]:
    cards: list[dict[str, Any]] = []
    for suit in _SUITS:
        for rank in _RANKS:
            tags: dict[str, float] = dict(suit["tags"])
            for name, weight in rank["tags"].items():
                tags[name] = round(tags.get(name, 0.0) + weight, 3)
            cards.append(
                {
                    "id": f"{suit['key']}-{rank['key']}",
                    "name": f"{rank['name']} of {suit['name']}",
                    "name_zh": f"{suit['name_zh']}{rank['name_zh']}",
                    "tags": tags,
                    "themes": [suit["theme"], rank["theme"]],
                    "meaning": f"{suit['theme']}的{rank['theme']}：把它用在今晚的选择上。",
                }
            )
    return cards


CARDS: list[dict[str, Any]] = [*MAJOR_ARCANA, *_build_minor_arcana()]


def calculate(answers: dict[str, Any]) -> dict[str, Any]:
    """塔罗不产生持久画像，保持 provider 契约的空画像。"""
    return {
        "code": "",
        "labels": [],
        "tags": {},
        "year_center": None,
        "length_center": None,
        "completed": False,
    }


def _normalize_spread(spread: Any) -> int:
    try:
        value = int(spread)
    except (TypeError, ValueError):
        value = 1
    return 3 if value >= 3 else 1


def draw(
    conn: sqlite3.Connection, *, spread: int = 1, seed: str | None = None
) -> dict[str, Any]:
    """按 seed 抽牌（默认按日期稳定），并返回牌面与推荐结果。"""
    spread = _normalize_spread(spread)
    positions = SPREAD_POSITIONS[spread]
    effective_seed = str(seed) if seed not in (None, "") else date.today().isoformat()
    rng = random.Random(effective_seed)

    indices = rng.sample(range(len(CARDS)), spread)
    cards: list[dict[str, Any]] = []
    aggregate: dict[str, float] = {}
    for position, index in zip(positions, indices):
        card = CARDS[index]
        reversed_ = rng.random() < 0.5
        scale = 0.5 if reversed_ else 1.0
        tags = {
            name: round(float(weight) * scale, 4)
            for name, weight in (card["tags"] or {}).items()
        }
        meaning = ("逆位：" + card["meaning"]) if reversed_ else card["meaning"]
        cards.append(
            {
                "id": card["id"],
                "name": card["name"],
                "name_zh": card["name_zh"],
                "position": position,
                "reversed": reversed_,
                "tags": tags,
                "themes": list(card["themes"]),
                "meaning": meaning,
            }
        )
        for name, weight in tags.items():
            aggregate[name] = aggregate.get(name, 0.0) + weight

    result = {
        "code": ("今日指引：" if spread == 1 else "三张牌阵：")
        + "·".join(card["name_zh"] for card in cards),
        "labels": [card["name_zh"] for card in cards],
        "tags": {
            name: round(weight, 4)
            for name, weight in sorted(aggregate.items(), key=lambda item: (-item[1], item[0]))
        },
        "year_center": None,
        "length_center": None,
        "completed": False,
    }

    index = FeatureIndex.build(conn)
    profile = persona.build_tag_profile(result, index, KEY)
    items = recommend(conn, limit=8, profile_source=KEY, profile_override=profile)
    return {
        "cards": cards,
        "result": result,
        "items": items,
        "spread": spread,
        "seed": effective_seed,
    }
