"""口味问答画像：题目定义与问卷结果计算。

题目借鉴 MBTI 的气质，把偏好拆成四个轴：叙事、氛围、节奏、结构。
每个选项都同时给出真实库内英文标签权重、四轴方向和可选的时代/时长线索。
"""

from __future__ import annotations

# 轴 -> 正向/负向的中文短词。正向取值为 >= 0，负向取值为 < 0。
AXIS_LABELS: dict[str, dict[str, str]] = {
    "narrative": {"positive": "剧情向", "negative": "角色向"},
    "atmosphere": {"positive": "轻松", "negative": "悬疑"},
    "pace": {"positive": "快节奏", "negative": "慢热"},
    "structure": {"positive": "多结局", "negative": "单结局"},
}
AXIS_ORDER = ("narrative", "atmosphere", "pace", "structure")

QUESTIONS: list[dict] = [
    {
        "id": "q_story",
        "title": "一部作品最吸引你的是什么？",
        "subtitle": "想想让你熬夜读下去的理由",
        "options": [
            {
                "id": "story_plot",
                "label": "层层展开的主线剧情",
                "tags": {"Drama": 1.2, "Mystery": 0.6},
                "axes": {"narrative": 1.2},
            },
            {
                "id": "story_character",
                "label": "角色的日常与互动",
                "tags": {"Slice of Life": 1.2, "Romance": 0.6},
                "axes": {"narrative": -1.2},
            },
            {
                "id": "story_adventure",
                "label": "不断冒险、探索未知",
                "tags": {"Action": 1.0, "Fantasy": 0.6},
                "axes": {"narrative": 0.4, "pace": 0.6},
            },
            {
                "id": "story_feeling",
                "label": "细腻的感情变化",
                "tags": {"Romance": 1.0, "Drama": 0.5},
                "axes": {"narrative": -0.6, "atmosphere": 0.4},
            },
        ],
    },
    {
        "id": "q_atmosphere",
        "title": "你更想待在哪种氛围里？",
        "options": [
            {
                "id": "atm_bright",
                "label": "阳光轻松的日常",
                "tags": {"Comedy": 1.2, "Slice of Life": 0.8},
                "axes": {"atmosphere": 1.2},
            },
            {
                "id": "atm_mystery",
                "label": "抽丝剥茧的悬疑",
                "tags": {"Mystery": 1.4, "Thriller": 0.6},
                "axes": {"atmosphere": -1.2, "narrative": 0.4},
            },
            {
                "id": "atm_dark",
                "label": "暗黑压抑的恐怖",
                "tags": {"Horror": 1.2, "Thriller": 0.5},
                "axes": {"atmosphere": -1.0, "pace": 0.3},
            },
            {
                "id": "atm_warm",
                "label": "温暖治愈的相处",
                "tags": {"Romance": 1.0, "Comedy": 0.4},
                "axes": {"atmosphere": 0.9},
            },
        ],
    },
    {
        "id": "q_pace",
        "title": "你喜欢怎样的叙事节奏？",
        "options": [
            {
                "id": "pace_fast",
                "label": "冲突密集，一路推进",
                "tags": {"Action": 1.2, "Thriller": 0.5},
                "axes": {"pace": 1.2},
            },
            {
                "id": "pace_slow",
                "label": "慢慢铺垫，细水长流",
                "tags": {"Slice of Life": 1.0, "Drama": 0.6},
                "axes": {"pace": -1.2},
            },
            {
                "id": "pace_epic",
                "label": "长篇大作，彻底沉浸",
                "tags": {"Fantasy": 0.8, "Drama": 0.5},
                "axes": {"pace": -0.4, "narrative": 0.5},
                "length": 2400,
            },
            {
                "id": "pace_short",
                "label": "短小精悍，一气呵成",
                "tags": {"Comedy": 0.8},
                "axes": {"pace": 0.6},
                "length": 180,
            },
        ],
    },
    {
        "id": "q_ending",
        "title": "对故事结局你有什么期待？",
        "subtitle": "结局的形态往往决定通关后的心情",
        "options": [
            {
                "id": "end_branch",
                "label": "多结局与分支路线",
                "tags": {"Multiple Endings": 1.4, "Branching Plot": 1.0},
                "axes": {"structure": 1.2},
            },
            {
                "id": "end_true",
                "label": "一条真结局走到底",
                "tags": {"One True End": 1.2},
                "axes": {"structure": -1.2},
            },
            {
                "id": "end_choice",
                "label": "每次选择都改变关系",
                "tags": {"Branching Plot": 1.0, "Romance": 0.6},
                "axes": {"structure": 0.8, "narrative": -0.3},
            },
            {
                "id": "end_single",
                "label": "简单收束，不留悬念",
                "tags": {"Single Ending": 0.8},
                "axes": {"structure": -0.6},
            },
        ],
    },
    {
        "id": "q_world",
        "title": "哪一类舞台最容易让你代入？",
        "options": [
            {
                "id": "world_school",
                "label": "现代校园与青春",
                "tags": {"School": 1.2, "Romance": 0.5},
                "axes": {"atmosphere": 0.5},
                "year": 2018,
            },
            {
                "id": "world_fantasy",
                "label": "剑与魔法的异世界",
                "tags": {"Fantasy": 1.2, "Action": 0.4},
                "axes": {"narrative": 0.6},
                "year": 2014,
            },
            {
                "id": "world_scifi",
                "label": "科幻与近未来",
                "tags": {"Science Fiction": 1.2, "Thriller": 0.4},
                "axes": {"atmosphere": -0.4, "narrative": 0.4},
                "year": 2021,
            },
            {
                "id": "world_real",
                "label": "贴近现实的普通人生活",
                "tags": {"Drama": 1.0, "Slice of Life": 0.6},
                "axes": {"pace": -0.4},
                "year": 2016,
            },
        ],
    },
    {
        "id": "q_protagonist",
        "title": "你更在意主角是哪一种？",
        "options": [
            {
                "id": "hero_male",
                "label": "男性主角的第一视角",
                "tags": {"Male Protagonist": 1.2},
                "axes": {"narrative": 0.3},
            },
            {
                "id": "hero_female",
                "label": "女性主角的第一视角",
                "tags": {"Female Protagonist": 1.2},
                "axes": {"narrative": 0.3},
            },
            {
                "id": "hero_face",
                "label": "有立绘、有面孔的主角",
                "tags": {"Protagonist with a Face": 1.0},
                "axes": {"atmosphere": 0.3},
            },
            {
                "id": "hero_story",
                "label": "主角是谁不重要，故事才重要",
                "tags": {"Drama": 0.4},
                "axes": {"structure": 0.3},
            },
        ],
    },
    {
        "id": "q_content",
        "title": "对亲密描写的接受度是？",
        "options": [
            {
                "id": "content_none",
                "label": "纯剧情，完全不要亲密戏",
                "tags": {"No Sexual Content": 1.4},
                "axes": {"narrative": 0.4},
            },
            {
                "id": "content_light",
                "label": "点到为止，重在感情",
                "tags": {"Romance": 0.8, "No Sexual Content": 0.4},
                "axes": {"atmosphere": 0.4},
            },
            {
                "id": "content_rich",
                "label": "亲密戏是情感表达的一部分",
                "tags": {"High Sexual Content": 1.2, "Romance": 0.5},
                "axes": {"atmosphere": -0.2},
            },
            {
                "id": "content_mature",
                "label": "更偏好成熟沉重的主题",
                "tags": {"Drama": 0.8, "Thriller": 0.4},
                "axes": {"atmosphere": -0.6, "narrative": 0.4},
            },
        ],
    },
    {
        "id": "q_time",
        "title": "你愿意为一部作品投入多少时间？",
        "options": [
            {
                "id": "time_long",
                "label": "几十小时的长篇大作",
                "tags": {"Fantasy": 0.5, "Drama": 0.5},
                "axes": {"pace": -0.6},
                "length": 3600,
            },
            {
                "id": "time_medium",
                "label": "十小时左右刚刚好",
                "tags": {"Romance": 0.5},
                "axes": {},
                "length": 600,
            },
            {
                "id": "time_short",
                "label": "两三小时读完一部",
                "tags": {"Comedy": 0.5},
                "axes": {"pace": 0.4},
                "length": 150,
            },
            {
                "id": "time_classic",
                "label": "年代久远也无所谓",
                "tags": {"Drama": 0.4},
                "axes": {"pace": -0.2},
                "year": 2008,
            },
        ],
    },
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


def calculate_profile(answers: dict[str, str]) -> dict:
    """根据答案计算画像；非法答案被忽略，不抛异常。"""
    cleaned = filter_answers(answers)
    tags: dict[str, float] = {}
    axes: dict[str, float] = {axis: 0.0 for axis in AXIS_ORDER}
    years: list[int] = []
    lengths: list[int] = []

    for question_id, option_id in cleaned.items():
        option = _OPTION_MAP[(question_id, option_id)]
        for name, weight in (option.get("tags") or {}).items():
            tags[name] = tags.get(name, 0.0) + float(weight)
        for axis, direction in (option.get("axes") or {}).items():
            if axis in axes:
                axes[axis] += float(direction)
        if option.get("year") is not None:
            years.append(int(option["year"]))
        if option.get("length") is not None:
            lengths.append(int(option["length"]))

    labels = [
        AXIS_LABELS[axis]["positive" if axes[axis] >= 0 else "negative"] for axis in AXIS_ORDER
    ]
    return {
        "code": "·".join(labels),
        "labels": labels,
        "tags": {name: round(weight, 4) for name, weight in sorted(tags.items(), key=lambda item: (-item[1], item[0]))},
        "year_center": round(sum(years) / len(years)) if years else None,
        "length_center": round(sum(lengths) / len(lengths)) if lengths else None,
        "completed": len(cleaned) == len(QUESTIONS),
    }
