"""玩家动机画像：24 题，测量你从视觉小说里想获得什么体验。

八个维度各三题、五级 Likert（-2 ~ +2）。维度得分换算成 0-100 的分数后，
再按维度的高低把偏好映射成真实库内英文标签，供推荐引擎构造标签向量。
题目为自编，仅用于口味推荐。
"""

from __future__ import annotations

KEY = "motivation"
TITLE = "玩家动机"
SUBTITLE = "24 题，测你从视觉小说里想获得什么体验"
KIND = "questionnaire"
GROUP = "serious"
ESTIMATED_MINUTES = 5
NOTICE = "维度参考公开的玩家动机模型，题目为自编，仅用于口味推荐。"

DIMENSION_ORDER: tuple[str, ...] = (
    "Story",
    "Fantasy",
    "Design",
    "Discovery",
    "Challenge",
    "Completion",
    "Community",
    "Excitement",
)

# 维度短语：正向用 high，低于中位用 low。
DIMENSION_LABELS: dict[str, dict[str, str]] = {
    "Story": {"high": "剧情驱动", "low": "轻松日常"},
    "Fantasy": {"high": "幻想代入", "low": "现实校园"},
    "Design": {"high": "分支设计", "low": "单线沉浸"},
    "Discovery": {"high": "沉浸探索", "low": "直给叙事"},
    "Challenge": {"high": "挑战解谜", "low": "放松治愈"},
    "Completion": {"high": "全收集", "low": "随缘通关"},
    "Community": {"high": "群像关系", "low": "单人视角"},
    "Excitement": {"high": "刺激节奏", "low": "悠闲慢热"},
}

# 维度 -> 真实库内标签及基准权重。得分 > 50 走 high，< 50 走 low。
DIMENSION_TAGS: dict[str, dict[str, tuple[tuple[str, float], ...]]] = {
    "Story": {
        "high": (("Drama", 1.2), ("Mystery", 0.5), ("Kinetic Novel", 0.4)),
        "low": (("Comedy", 1.2), ("Slice of Life", 0.8)),
    },
    "Fantasy": {
        "high": (("Fantasy", 1.2), ("Science Fiction", 0.7), ("Urban Fantasy", 0.5)),
        "low": (("School", 1.2), ("Slice of Life", 0.7)),
    },
    "Design": {
        "high": (("Branching Plot", 1.3), ("Multiple Endings", 1.1)),
        "low": (("Linear Plot", 1.2), ("One True End", 0.9)),
    },
    "Discovery": {
        "high": (
            ("Mystery", 1.0),
            ("Time Loop", 0.8),
            ("Metafiction", 0.7),
            ("Unreliable Narrator", 0.6),
        ),
        "low": (("Linear Plot", 1.0),),
    },
    "Challenge": {
        "high": (("Mystery", 0.9), ("Puzzle Game", 0.9), ("Detective Work", 0.7)),
        "low": (("Comedy", 0.9), ("Slice of Life", 0.8)),
    },
    "Completion": {
        "high": (
            ("Multiple Endings", 1.2),
            ("Branching Plot", 1.0),
            ("100% Completion Bonus", 0.6),
        ),
        "low": (("Single Ending", 1.1), ("Kinetic Novel", 0.8)),
    },
    "Community": {
        "high": (
            ("Harem Ending", 1.0),
            ("Love Triangle", 1.0),
            ("Romance", 1.2),
            ("School", 0.8),
        ),
        "low": (("Male Protagonist", 0.9), ("Female Protagonist", 0.9)),
    },
    "Excitement": {
        "high": (("Action", 1.2), ("Thriller", 1.0), ("Horror", 0.8)),
        "low": (("Slice of Life", 1.1), ("Comedy", 0.7)),
    },
}

# 每维三题，每题五级，得分 -2 / -1 / 0 / +1 / +2。
_MIN_SCORE = -2
_MAX_SCORE = 2
_MAX_ABS_RAW = 6  # 3 题 * 2 分


def _question(
    dimension: str,
    index: int,
    title: str,
    levels: list[tuple[str, dict[str, float], int | None, int | None]],
    subtitle: str | None = None,
) -> dict:
    prefix = dimension.lower()
    options: list[dict] = []
    for offset, (label, tags, year, length) in enumerate(levels):
        option_id = f"{prefix}_{index}_{offset + 1}"
        option: dict = {
            "id": option_id,
            "label": label,
            "score": _MIN_SCORE + offset,
            "tags": dict(tags),
        }
        if year is not None:
            option["year"] = int(year)
        if length is not None:
            option["length"] = int(length)
        options.append(option)
    data: dict = {
        "id": f"mot_{prefix}_{index}",
        "title": title,
        "dimension": dimension,
        "options": options,
    }
    if subtitle:
        data["subtitle"] = subtitle
    return data


QUESTIONS: list[dict] = [
    # ---------------- Story ----------------
    _question(
        "Story",
        1,
        "读到伏笔和铺垫时，你会主动回看前文吗？",
        [
            ("不会，顺着一路读下去", {"Comedy": 0.3, "Slice of Life": 0.3}, None, None),
            ("只在卡住时翻一下", {"Slice of Life": 0.2}, None, None),
            ("看情况，取决于是否感兴趣", {"Drama": 0.2}, None, None),
            ("会回看关键段落确认线索", {"Drama": 0.4, "Mystery": 0.3}, None, None),
            ("会翻遍所有伏笔并做笔记", {"Drama": 0.5, "Mystery": 0.5, "Kinetic Novel": 0.3}, None, None),
        ],
        subtitle="想想你会不会为了一个细节往回跳",
    ),
    _question(
        "Story",
        2,
        "主线推进与角色日常，你更愿意把时间花在哪边？",
        [
            ("几乎只要角色日常", {"Comedy": 0.4, "Slice of Life": 0.5}, None, None),
            ("日常为主，主线点缀", {"Slice of Life": 0.4, "Romance": 0.3}, None, None),
            ("两者各占一半", {"Drama": 0.2, "Slice of Life": 0.2}, None, None),
            ("主线为主，日常调剂", {"Drama": 0.4, "Mystery": 0.3}, None, None),
            ("全程围绕主线推进", {"Drama": 0.5, "Mystery": 0.4, "Kinetic Novel": 0.3}, None, None),
        ],
    ),
    _question(
        "Story",
        3,
        "读完之后，你希望故事留下什么？",
        [
            ("轻松一笑就够", {"Comedy": 0.5}, None, None),
            ("有点甜就行", {"Romance": 0.4, "Comedy": 0.3}, None, None),
            ("完整讲完就好", {"Drama": 0.2}, None, None),
            ("能回味几天的情感冲击", {"Drama": 0.5, "Nakige": 0.3}, None, None),
            ("值得反复琢磨的主题与结构", {"Drama": 0.5, "Kinetic Novel": 0.4, "Philosophy": 0.3}, None, None),
        ],
    ),
    # ---------------- Fantasy ----------------
    _question(
        "Fantasy",
        1,
        "面对架空世界观（魔法、科幻、妖怪），你的投入程度？",
        [
            ("更想看贴近现实的故事", {"Slice of Life": 0.4, "School": 0.3}, None, None),
            ("设定别太复杂", {"School": 0.3, "Romance": 0.3}, None, None),
            ("轻度设定可以接受", {"Fantasy": 0.2}, None, None),
            ("愿意学习一套新规则", {"Fantasy": 0.4, "Science Fiction": 0.3}, None, None),
            ("越庞大越硬核越兴奋", {"Fantasy": 0.5, "Science Fiction": 0.4, "Magic": 0.3}, None, None),
        ],
    ),
    _question(
        "Fantasy",
        2,
        "你更想扮演哪种身份？",
        [
            ("普通学生，越日常越好", {"School": 0.5, "Slice of Life": 0.3}, 2018, None),
            ("有点特别但仍在现实", {"School": 0.3, "Romance": 0.3}, 2017, None),
            ("都可以", {"Drama": 0.2}, None, None),
            ("异世界冒险者或科幻船员", {"Fantasy": 0.4, "Science Fiction": 0.4}, 2015, None),
            ("非人、妖怪或超能力者", {"Youkai": 0.4, "Demons": 0.3, "Fantasy": 0.4}, 2012, None),
        ],
    ),
    _question(
        "Fantasy",
        3,
        "你希望故事舞台离现实有多远？",
        [
            ("完全现实，最好就在身边", {"Slice of Life": 0.4, "School": 0.4}, 2019, None),
            ("现实中带一点小设定", {"School": 0.3, "Romance": 0.3}, None, None),
            ("现实与幻想各半", {"Drama": 0.2, "Fantasy": 0.2}, None, None),
            ("明确的幻想世界", {"Fantasy": 0.4, "Urban Fantasy": 0.3}, 2014, None),
            ("彻底架空，规则自洽", {"Fantasy": 0.5, "Science Fiction": 0.3}, 2011, None),
        ],
    ),
    # ---------------- Design ----------------
    _question(
        "Design",
        1,
        "选择是否改变结局，对你重要吗？",
        [
            ("不重要，看固定的故事就好", {"Linear Plot": 0.5}, None, None),
            ("有选择但别影响大局", {"Linear Plot": 0.3, "Drama": 0.2}, None, None),
            ("有点分支更好", {"Branching Plot": 0.2}, None, None),
            ("重要，选择应有后果", {"Branching Plot": 0.4, "Multiple Endings": 0.3}, None, None),
            ("非常重要，必须多结局", {"Branching Plot": 0.5, "Multiple Endings": 0.5}, None, None),
        ],
    ),
    _question(
        "Design",
        2,
        "为了看到不同路线，你愿意重玩多少遍？",
        [
            ("一遍就够，不重玩", {"Single Ending": 0.4, "Kinetic Novel": 0.3}, None, None),
            ("最多换个选项试一次", {"Linear Plot": 0.3}, None, None),
            ("看剧情吸引力再说", {"Drama": 0.2}, None, None),
            ("愿意为两三条路线重玩", {"Branching Plot": 0.4, "Multiple Endings": 0.3}, None, None),
            ("会跑遍所有结局", {"Multiple Endings": 0.5, "Branching Plot": 0.4}, None, 2400),
        ],
    ),
    _question(
        "Design",
        3,
        "你偏好的叙事结构是？",
        [
            ("一条线讲到底，别分心", {"Linear Plot": 0.5, "One True End": 0.3}, None, None),
            ("主线清晰，少量支线", {"Linear Plot": 0.3, "Drama": 0.2}, None, None),
            ("都行", {"Drama": 0.2}, None, None),
            ("多分支，但收束到真结局", {"Branching Plot": 0.4, "One True End": 0.3}, None, None),
            ("自由分支，多结局并存", {"Branching Plot": 0.5, "Multiple Endings": 0.5}, None, None),
        ],
    ),
    # ---------------- Discovery ----------------
    _question(
        "Discovery",
        1,
        "面对故事里的谜团，你会主动拼线索吗？",
        [
            ("不想动脑，等剧情揭晓", {"Slice of Life": 0.4, "Comedy": 0.3}, None, None),
            ("有提示才愿意想", {"Slice of Life": 0.2, "Drama": 0.2}, None, None),
            ("随缘留意", {"Drama": 0.2}, None, None),
            ("会主动记下疑点", {"Mystery": 0.4, "Unreliable Narrator": 0.3}, None, None),
            ("会整理时间线和证词", {"Mystery": 0.5, "Detective Work": 0.4}, None, None),
        ],
    ),
    _question(
        "Discovery",
        2,
        "对叙述诡计、不可靠叙述者的兴趣？",
        [
            ("不喜欢被绕，直说就好", {"Linear Plot": 0.4}, None, None),
            ("少量反转可以接受", {"Drama": 0.3}, None, None),
            ("看处理得好不好", {"Mystery": 0.2}, None, None),
            ("喜欢结尾推翻认知", {"Mystery": 0.4, "Unreliable Narrator": 0.4}, None, None),
            ("越绕越想去拆解", {"Metafiction": 0.4, "Unreliable Narrator": 0.5}, None, None),
        ],
    ),
    _question(
        "Discovery",
        3,
        "多周目才会揭开真相的设定，你会？",
        [
            ("一周目没讲完就不耐烦", {"Linear Plot": 0.3, "Comedy": 0.3}, None, None),
            ("不太想重复看相同内容", {"Linear Plot": 0.2, "Slice of Life": 0.2}, None, None),
            ("视情况而定", {"Drama": 0.2}, None, None),
            ("愿意二周目找新线索", {"Time Loop": 0.4, "Mystery": 0.3}, None, None),
            ("专门为多周目设计才过瘾", {"Time Loop": 0.5, "Mystery": 0.4}, None, 1800),
        ],
    ),
    # ---------------- Challenge ----------------
    _question(
        "Challenge",
        1,
        "遇到需要动脑的谜题或机关，你的态度？",
        [
            ("只想轻松看剧情", {"Slice of Life": 0.4, "Comedy": 0.3}, None, None),
            ("卡太久就查攻略", {"Comedy": 0.3}, None, None),
            ("解不开就先放着", {"Drama": 0.2}, None, None),
            ("愿意花时间自己解", {"Puzzle Game": 0.4, "Mystery": 0.3}, None, None),
            ("越难越想啃下来", {"Puzzle Game": 0.5, "Battle of Wits": 0.3}, None, None),
        ],
    ),
    _question(
        "Challenge",
        2,
        "推理、侦探要素对你的吸引力？",
        [
            ("完全不感兴趣", {"Comedy": 0.4, "Slice of Life": 0.3}, None, None),
            ("有一点就好", {"Drama": 0.3}, None, None),
            ("有没有都行", {"Drama": 0.2}, None, None),
            ("喜欢跟着推理", {"Detective Work": 0.4, "Mystery": 0.3}, None, None),
            ("会自己先猜凶手再验证", {"Detective Work": 0.5, "Mystery": 0.4}, None, None),
        ],
    ),
    _question(
        "Challenge",
        3,
        "剧情卡关或逻辑烧脑时，你会坚持吗？",
        [
            ("立刻放弃，换轻松的作品", {"Slice of Life": 0.4, "Comedy": 0.4}, None, None),
            ("烦躁就跳过", {"Comedy": 0.3}, None, None),
            ("看心情", {"Drama": 0.2}, None, None),
            ("会坚持到弄懂为止", {"Mystery": 0.4, "Puzzle Game": 0.3}, None, None),
            ("越烧脑越有成就感", {"Battle of Wits": 0.4, "Mystery": 0.4}, None, None),
        ],
    ),
    # ---------------- Completion ----------------
    _question(
        "Completion",
        1,
        "看到结局列表时，你的第一反应？",
        [
            ("只走一个结局就封盘", {"Single Ending": 0.4, "Kinetic Novel": 0.3}, None, None),
            ("能通关就行", {"Single Ending": 0.3}, None, None),
            ("看心情补几个", {"Drama": 0.2}, None, None),
            ("想把主要结局都看了", {"Multiple Endings": 0.4, "Branching Plot": 0.3}, None, None),
            ("必须 100% 全结局", {"Multiple Endings": 0.5, "100% Completion Bonus": 0.4}, None, 3000),
        ],
    ),
    _question(
        "Completion",
        2,
        "对 CG、成就、支线的收集欲？",
        [
            ("完全不收集", {"Kinetic Novel": 0.3, "Single Ending": 0.3}, None, None),
            ("顺手看到就收", {"Slice of Life": 0.3}, None, None),
            ("只收特别喜欢的", {"Romance": 0.3}, None, None),
            ("会刻意补遗漏的 CG", {"Multiple Endings": 0.3, "100% Completion Bonus": 0.4}, None, None),
            ("成就和支线必须全清", {"100% Completion Bonus": 0.5, "Branching Plot": 0.3}, None, 2600),
        ],
    ),
    _question(
        "Completion",
        3,
        "一条线看完后，你还会去走其他角色线吗？",
        [
            ("不会，故事已经完整", {"Single Ending": 0.4, "Kinetic Novel": 0.3}, None, None),
            ("除非特别喜欢那个角色", {"Romance": 0.3, "Single Ending": 0.2}, None, None),
            ("可能会", {"Drama": 0.2}, None, None),
            ("会走完感兴趣的几条", {"Branching Plot": 0.3, "Romance": 0.3}, None, None),
            ("所有线都要走一遍", {"Multiple Endings": 0.4, "Branching Plot": 0.4}, None, None),
        ],
    ),
    # ---------------- Community ----------------
    _question(
        "Community",
        1,
        "你希望故事里有多少可互动的角色？",
        [
            ("一两个核心人物就够", {"Male Protagonist": 0.3, "Female Protagonist": 0.3}, None, None),
            ("小圈子几个人", {"Slice of Life": 0.3, "Male Protagonist": 0.2}, None, None),
            ("适中", {"Drama": 0.2}, None, None),
            ("热闹的社团或班级群像", {"School": 0.4, "Romance": 0.3}, None, None),
            ("角色越多关系网越复杂越好", {"Harem Ending": 0.4, "Love Triangle": 0.4, "School": 0.3}, None, None),
        ],
    ),
    _question(
        "Community",
        2,
        "对多角恋、后宫式关系展开的接受度？",
        [
            ("只想要一对一纯爱", {"Romance": 0.4, "Female Protagonist": 0.2}, None, None),
            ("轻微三角可以", {"Romance": 0.4, "Love Triangle": 0.2}, None, None),
            ("看写得如何", {"Romance": 0.2}, None, None),
            ("喜欢多条感情线交织", {"Love Triangle": 0.4, "Romance": 0.4}, None, None),
            ("越乱越有戏剧性", {"Harem Ending": 0.4, "Love Triangle": 0.5}, None, None),
        ],
    ),
    _question(
        "Community",
        3,
        "你更愿意跟随单一主角，还是切换群像视角？",
        [
            ("只跟一个主角到底", {"Male Protagonist": 0.4, "Female Protagonist": 0.3}, None, None),
            ("以主角为主，偶尔换视角", {"Male Protagonist": 0.3, "Drama": 0.2}, None, None),
            ("都能接受", {"Drama": 0.2}, None, None),
            ("喜欢多角色视角互补", {"School": 0.3, "Drama": 0.3}, None, None),
            ("群像轮换才看得过瘾", {"Harem Ending": 0.3, "Love Triangle": 0.3, "School": 0.3}, None, None),
        ],
    ),
    # ---------------- Excitement ----------------
    _question(
        "Excitement",
        1,
        "高强度冲突与动作场面，会让你更投入吗？",
        [
            ("反而觉得吵，想安静", {"Slice of Life": 0.5, "Nakige": 0.2}, None, None),
            ("少量就够", {"Slice of Life": 0.3, "Romance": 0.2}, None, None),
            ("适量可以", {"Drama": 0.2}, None, None),
            ("关键时刻要有冲击力", {"Thriller": 0.4, "Action": 0.3}, None, None),
            ("从头到尾都要紧张刺激", {"Action": 0.5, "Thriller": 0.4}, None, None),
        ],
    ),
    _question(
        "Excitement",
        2,
        "恐怖、惊悚、血腥元素的耐受度？",
        [
            ("完全不能接受", {"Slice of Life": 0.4, "Comedy": 0.3}, None, None),
            ("只能接受轻微惊悚", {"Comedy": 0.3, "Suspense": 0.2}, None, None),
            ("看氛围处理", {"Suspense": 0.3}, None, None),
            ("喜欢被吓到或绷紧神经", {"Horror": 0.4, "Suspense": 0.4}, None, None),
            ("越黑暗越血腥越带感", {"Horror": 0.5, "Gore": 0.3, "Thriller": 0.3}, None, None),
        ],
    ),
    _question(
        "Excitement",
        3,
        "你偏好的整体节奏是？",
        [
            ("极慢热，日常细水长流", {"Slice of Life": 0.5, "Nakige": 0.3}, None, 3000),
            ("慢一点，重在氛围", {"Slice of Life": 0.3, "Romance": 0.3}, None, 1800),
            ("张弛有度", {"Drama": 0.3}, None, 900),
            ("节奏紧凑，少废话", {"Thriller": 0.4, "Action": 0.3}, None, 600),
            ("一路高能，停不下来", {"Action": 0.4, "Thriller": 0.4}, None, 300),
        ],
    ),
]

_QUESTION_MAP = {question["id"]: question for question in QUESTIONS}
_OPTION_MAP = {
    (question["id"], option["id"]): option
    for question in QUESTIONS
    for option in question["options"]
}


def filter_answers(answers: dict[str, str] | None) -> dict[str, str]:
    """只保留合法的 question_id -> option_id，其余一律忽略。"""
    if not isinstance(answers, dict):
        return {}
    cleaned: dict[str, str] = {}
    for question_id, option_id in answers.items():
        if not isinstance(question_id, str) or not isinstance(option_id, str):
            continue
        if (question_id, option_id) in _OPTION_MAP:
            cleaned[question_id] = option_id
    return cleaned


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def calculate(answers: dict[str, str]) -> dict:
    """根据答案计算画像；非法答案被忽略，任何输入都不抛异常。"""
    cleaned = filter_answers(answers)
    raw_scores: dict[str, int] = {dimension: 0 for dimension in DIMENSION_ORDER}
    tags: dict[str, float] = {}
    years: list[int] = []
    lengths: list[int] = []

    for question_id, option_id in cleaned.items():
        question = _QUESTION_MAP[question_id]
        option = _OPTION_MAP[(question_id, option_id)]
        dimension = question["dimension"]
        raw_scores[dimension] += int(option["score"])
        for name, weight in (option.get("tags") or {}).items():
            tags[name] = tags.get(name, 0.0) + float(weight)
        if option.get("year") is not None:
            years.append(int(option["year"]))
        if option.get("length") is not None:
            lengths.append(int(option["length"]))

    scores: dict[str, int] = {}
    for dimension in DIMENSION_ORDER:
        raw = raw_scores[dimension]
        scores[dimension] = int(round(_clamp(50 + raw / _MAX_ABS_RAW * 50, 0, 100)))
        strength = raw / _MAX_ABS_RAW  # -1 ~ +1
        if strength > 0:
            for name, base in DIMENSION_TAGS[dimension]["high"]:
                tags[name] = tags.get(name, 0.0) + base * strength * 2
        elif strength < 0:
            for name, base in DIMENSION_TAGS[dimension]["low"]:
                tags[name] = tags.get(name, 0.0) + base * (-strength) * 2

    ranked = sorted(
        DIMENSION_ORDER, key=lambda dim: (-scores[dim], DIMENSION_ORDER.index(dim))
    )
    top_two = ranked[:2]
    labels = [
        DIMENSION_LABELS[dim]["high" if scores[dim] >= 50 else "low"] for dim in top_two
    ]

    positive_tags = {
        name: round(weight, 4) for name, weight in tags.items() if weight > 0
    }
    positive_tags = dict(
        sorted(positive_tags.items(), key=lambda item: (-item[1], item[0]))
    )

    return {
        "code": "·".join(labels),
        "labels": labels,
        "tags": positive_tags,
        "year_center": round(sum(years) / len(years)) if years else None,
        "length_center": round(sum(lengths) / len(lengths)) if lengths else None,
        "completed": len(cleaned) == len(QUESTIONS),
        "scores": scores,
    }
