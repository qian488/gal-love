"""大五人格画像：BFI-10 式自编题目与标签映射。

10 道 5 级 Likert 题，每个维度两题（一正一反向计分）。维度得分换算成
0-100 后，按偏离 50 的程度生成推荐标签权重。题目仅供口味推荐使用。
"""

from __future__ import annotations

KEY = "bigfive"
TITLE = "大五人格"
SUBTITLE = "10 题，看看你的开放性、尽责性与情绪倾向"
KIND = "questionnaire"
GROUP = "serious"
ESTIMATED_MINUTES = 2
NOTICE = "题目参考公开的五因素模型自编，仅用于口味推荐。"

DIMENSIONS: tuple[str, ...] = ("O", "C", "E", "A", "N")

DIMENSION_NAMES: dict[str, str] = {
    "O": "开放性",
    "C": "尽责性",
    "E": "外向性",
    "A": "宜人性",
    "N": "神经质",
}

DIMENSION_SHORT: dict[str, str] = {
    "O": "开放",
    "C": "尽责",
    "E": "外向",
    "A": "宜人",
    "N": "神经质",
}

LEVEL_WORDS: dict[str, str] = {"high": "高", "mid": "中", "low": "低"}

# 维度 -> 高/低分对应的库内真实标签。
# 原设定中的 Meta / Harem / Iyashikei / Tragedy 不在库中，分别换成
# Metafiction / Harem Ending / Slice of Life Comedy / Life and Death Drama。
TAG_MAP: dict[str, dict[str, tuple[str, ...]]] = {
    "O": {
        "high": (
            "Science Fiction",
            "Fantasy",
            "Metafiction",
            "Time Loop",
            "Unreliable Narrator",
        ),
        "low": ("School", "Slice of Life", "Romance"),
    },
    "C": {
        "high": ("Multiple Endings", "Branching Plot", "Drama"),
        "low": ("Single Ending", "Kinetic Novel", "Comedy"),
    },
    "E": {
        "high": ("Harem Ending", "Love Triangle", "School", "Comedy"),
        "low": ("Male Protagonist", "Female Protagonist", "Drama"),
    },
    "A": {
        "high": ("Nakige", "Romance", "Slice of Life Comedy", "Slice of Life"),
        "low": ("Thriller", "Revenge", "Life and Death Drama", "Utsuge"),
    },
    "N": {
        "high": ("Horror", "Thriller", "Utsuge", "Psychological Horror"),
        "low": ("Comedy", "Cafe", "Slice of Life"),
    },
}

LIKERT_LABELS: dict[int, str] = {
    -2: "很不同意",
    -1: "不同意",
    0: "中立",
    1: "同意",
    2: "很同意",
}


def _likert(dimension: str, reverse: bool) -> list[dict]:
    """生成 5 级选项；选项上的 tags 仅描述该选择指向的标签方向。"""
    high = TAG_MAP[dimension]["high"]
    low = TAG_MAP[dimension]["low"]
    options: list[dict] = []
    for value in (-2, -1, 0, 1, 2):
        if value == 0:
            tags: dict[str, float] = {}
        else:
            pole = "high" if value > 0 else "low"
            if reverse:
                pole = "low" if pole == "high" else "high"
            tags = {name: 1.0 for name in (high if pole == "high" else low)}
        options.append(
            {
                "id": str(value),
                "label": LIKERT_LABELS[value],
                "value": value,
                "tags": tags,
            }
        )
    return options


QUESTIONS: list[dict] = [
    {
        "id": "bf_o_pos",
        "title": "我有很多想象力，喜欢接触新奇的想法。",
        "dimension": "O",
        "reverse": False,
        "options": _likert("O", False),
    },
    {
        "id": "bf_o_neg",
        "title": "我对抽象、艺术或思辨性的东西不太感兴趣。",
        "dimension": "O",
        "reverse": True,
        "options": _likert("O", True),
    },
    {
        "id": "bf_c_pos",
        "title": "我做事有条理，会按计划把事情完成。",
        "dimension": "C",
        "reverse": False,
        "options": _likert("C", False),
    },
    {
        "id": "bf_c_neg",
        "title": "我常常拖延，东西也放得乱七八糟。",
        "dimension": "C",
        "reverse": True,
        "options": _likert("C", True),
    },
    {
        "id": "bf_e_pos",
        "title": "我性格外向，喜欢和别人待在一起。",
        "dimension": "E",
        "reverse": False,
        "options": _likert("E", False),
    },
    {
        "id": "bf_e_neg",
        "title": "我比较安静，习惯先观察再开口。",
        "dimension": "E",
        "reverse": True,
        "options": _likert("E", True),
    },
    {
        "id": "bf_a_pos",
        "title": "我待人温和，愿意体谅别人的感受。",
        "dimension": "A",
        "reverse": False,
        "options": _likert("A", False),
    },
    {
        "id": "bf_a_neg",
        "title": "我有时会对别人挑剔，显得有点冷淡。",
        "dimension": "A",
        "reverse": True,
        "options": _likert("A", True),
    },
    {
        "id": "bf_n_pos",
        "title": "我容易紧张，情绪起伏比较大。",
        "dimension": "N",
        "reverse": False,
        "options": _likert("N", False),
    },
    {
        "id": "bf_n_neg",
        "title": "我大多数时候心态放松，不容易焦虑。",
        "dimension": "N",
        "reverse": True,
        "options": _likert("N", True),
    },
]

_QUESTION_MAP = {question["id"]: question for question in QUESTIONS}
_OPTION_VALUES = {
    option["id"]: int(option["value"])
    for question in QUESTIONS
    for option in question["options"]
}
_OPTION_IDS = frozenset(_OPTION_VALUES)


def filter_answers(answers: dict[str, str] | None) -> dict[str, str]:
    """只保留合法的 question_id -> option_id，其余忽略。"""
    if not isinstance(answers, dict):
        return {}
    cleaned: dict[str, str] = {}
    for question_id, option_id in answers.items():
        if not isinstance(question_id, str) or question_id not in _QUESTION_MAP:
            continue
        try:
            option_key = str(option_id)
        except Exception:  # noqa: BLE001 - 非法对象按无效答案处理
            continue
        if option_key in _OPTION_IDS:
            cleaned[question_id] = option_key
    return cleaned


def _level(score: int) -> str:
    if score >= 65:
        return "high"
    if score <= 35:
        return "low"
    return "mid"


def calculate(answers: dict[str, str] | None) -> dict:
    """按维度汇总得分并生成标签；缺失题目按中立处理。"""
    cleaned = filter_answers(answers)
    raw: dict[str, int] = {dimension: 0 for dimension in DIMENSIONS}
    for question in QUESTIONS:
        option_id = cleaned.get(question["id"])
        if option_id is None:
            continue
        value = _OPTION_VALUES[option_id]
        raw[question["dimension"]] += -value if question["reverse"] else value

    scores = {
        dimension: max(0, min(100, round((raw[dimension] + 4) / 8 * 100)))
        for dimension in DIMENSIONS
    }

    tags: dict[str, float] = {}
    for dimension in DIMENSIONS:
        score = scores[dimension]
        weight = abs(score - 50) / 50 * 1.2
        if weight <= 0:
            continue
        pole = "high" if score > 50 else "low"
        for name in TAG_MAP[dimension][pole]:
            tags[name] = tags.get(name, 0.0) + weight

    levels = {dimension: _level(scores[dimension]) for dimension in DIMENSIONS}
    labels = [
        f"{DIMENSION_NAMES[dimension]}{LEVEL_WORDS[levels[dimension]]}"
        for dimension in DIMENSIONS
    ]
    code = "·".join(
        f"{LEVEL_WORDS[levels[dimension]]}{DIMENSION_SHORT[dimension]}"
        for dimension in DIMENSIONS
    )

    return {
        "code": code,
        "labels": labels,
        "tags": {
            name: round(weight, 4)
            for name, weight in sorted(tags.items(), key=lambda item: (-item[1], item[0]))
        },
        "year_center": None,
        "length_center": None,
        "completed": len(cleaned) == len(QUESTIONS),
        "scores": scores,
    }
