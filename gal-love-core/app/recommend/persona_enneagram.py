"""九型人格画像：18 题问卷与主型/侧翼计算。

每个类型对应两道题，共 18 题；每题给出 4 个分属不同类型的选项。
统计各型被选中的次数得到主型，再在主型相邻的两型中取高分者作为侧翼，
最后把主型与侧翼映射成真实库内英文标签，交给推荐引擎使用。

题目与标签只描述偏好，不构成任何心理诊断。
"""

from __future__ import annotations

KEY = "enneagram"
TITLE = "九型人格"
SUBTITLE = "18 题，找到你的核心动机与侧翼"
KIND = "questionnaire"
GROUP = "fun"
ESTIMATED_MINUTES = 4
NOTICE = "娱乐向自我探索，不作为心理诊断。"

TYPES: tuple[int, ...] = (1, 2, 3, 4, 5, 6, 7, 8, 9)

TYPE_NAMES: dict[int, str] = {
    1: "完美型",
    2: "助人型",
    3: "成就型",
    4: "自我型",
    5: "观察型",
    6: "忠诚型",
    7: "活跃型",
    8: "领袖型",
    9: "和平型",
}

# 三中心：腹中心（愤怒）、心中心（羞耻）、脑中心（恐惧）。
CENTER_BY_TYPE: dict[int, str] = {
    1: "腹中心",
    2: "心中心",
    3: "心中心",
    4: "心中心",
    5: "脑中心",
    6: "脑中心",
    7: "脑中心",
    8: "腹中心",
    9: "腹中心",
}

# 侧翼只能在相邻的两型中产生；1 与 9 首尾相连。
NEIGHBORS: dict[int, tuple[int, int]] = {
    1: (9, 2),
    2: (1, 3),
    3: (2, 4),
    4: (3, 5),
    5: (4, 6),
    6: (5, 7),
    7: (6, 8),
    8: (7, 9),
    9: (8, 1),
}

# 主型 -> 标签权重，全部为库内真实存在的 VNDB 标签。
TYPE_TAGS: dict[int, dict[str, float]] = {
    1: {"Drama": 1.2, "Mystery": 1.0, "Philosophy": 0.8},
    2: {"Romance": 1.3, "Slice of Life": 1.1, "Nakige": 0.9},
    3: {"Multiple Endings": 1.2, "Branching Plot": 1.1, "School": 0.9},
    4: {"Drama": 1.3, "Utsuge": 1.1, "Psychological Trauma": 0.9},
    5: {"Mystery": 1.3, "Science Fiction": 1.1, "Puzzle Game": 0.9},
    6: {"Thriller": 1.3, "Mystery": 1.0, "Suspense": 0.9},
    7: {"Comedy": 1.3, "Action": 1.1, "Fantasy": 0.9},
    8: {"Action": 1.3, "War": 1.1, "Revenge": 0.9},
    9: {"Slice of Life": 1.3, "Comedy": 1.1, "Slice of Life Comedy": 0.9},
}

# 侧翼微调：0.4 为该侧翼的标志性标签，0.3 为与主型共享或相近的标签。
WING_TAGS: dict[int, dict[str, float]] = {
    1: {"Philosophy": 0.4, "Drama": 0.3},
    2: {"Nakige": 0.4, "Romance": 0.3},
    3: {"School": 0.4, "Branching Plot": 0.3},
    4: {"Utsuge": 0.4, "Drama": 0.3},
    5: {"Mystery": 0.4, "Science Fiction": 0.3},
    6: {"Suspense": 0.4, "Thriller": 0.3},
    7: {"Fantasy": 0.4, "Comedy": 0.3},
    8: {"Revenge": 0.4, "War": 0.3},
    9: {"Slice of Life Comedy": 0.4, "Slice of Life": 0.3},
}

# 选项自带的标签倾向（同为主型标签的子集，权重更轻，只用于展示与聚合）。
OPTION_TAGS: dict[int, dict[str, float]] = {
    1: {"Drama": 0.8, "Philosophy": 0.5},
    2: {"Romance": 0.8, "Nakige": 0.5},
    3: {"Multiple Endings": 0.8, "School": 0.5},
    4: {"Utsuge": 0.8, "Drama": 0.5},
    5: {"Mystery": 0.8, "Puzzle Game": 0.5},
    6: {"Thriller": 0.8, "Suspense": 0.5},
    7: {"Comedy": 0.8, "Fantasy": 0.5},
    8: {"Action": 0.8, "Revenge": 0.5},
    9: {"Slice of Life": 0.8, "Slice of Life Comedy": 0.5},
}

# (题干, 副标题, [(类型, 选项文案), ...])
_QUESTION_SPECS: list[tuple[str, str | None, list[tuple[int, str]]]] = [
    (
        "打开一部新作品时，你最先在意什么？",
        "想想是什么让你决定继续读下去",
        [
            (1, "设定是否严谨、逻辑有没有漏洞"),
            (2, "角色之间会不会产生温暖的羁绊"),
            (3, "有没有多条路线和可以收集的结局"),
            (4, "故事有没有独特的气质和作者表达"),
        ],
    ),
    (
        "开始一部新游戏前，你通常会？",
        None,
        [
            (5, "先查资料、看评测，把系统摸清楚再动手"),
            (6, "先确认口碑和结局走向，避免踩到雷"),
            (7, "凭第一眼心动直接开玩，边玩边发现"),
            (8, "直接选最高难度，正面硬刚"),
        ],
    ),
    (
        "在朋友群里，你更像哪一种人？",
        None,
        [
            (9, "顺着大家的节奏走，气氛舒服就好"),
            (1, "把行程和规则安排得妥妥当当"),
            (2, "主动照顾落单的人，记得每个人的喜好"),
            (3, "负责推进度，把事情真正做成"),
        ],
    ),
    (
        "深夜一个人时，你最想读哪种故事？",
        None,
        [
            (4, "关于孤独、失去与自我认同的故事"),
            (5, "层层设谜、需要动脑拼合的故事"),
            (6, "随时可能反转、让人提心吊胆的故事"),
            (7, "热闹轻快、读完心情会变好的故事"),
        ],
    ),
    (
        "看到有人在公共场合被为难，你会？",
        None,
        [
            (8, "直接站出来，把场面压下去"),
            (9, "先缓和气氛，别让冲突继续升级"),
            (1, "指出哪里不对，把道理讲清楚"),
            (2, "事后私下安慰对方，问他需不需要帮忙"),
        ],
    ),
    (
        "你最想解开哪一种谜？",
        None,
        [
            (3, "怎样用最优解通关，拿到全部成就"),
            (4, "一个人为什么会变成现在这个样子"),
            (5, "封闭空间里那起不可能犯罪"),
            (6, "身边谁在说谎、下一个受害者是谁"),
        ],
    ),
    (
        "理想的周末是？",
        None,
        [
            (7, "临时起意出门，把没去过的地方逛一遍"),
            (8, "打一场硬仗，赢下排位或通关高难"),
            (9, "待在家里煮点东西，看看日常向作品"),
            (1, "把拖了很久的计划清单逐条划掉"),
        ],
    ),
    (
        "你更希望在作品里获得什么？",
        None,
        [
            (2, "被人需要、也被人温柔对待的感觉"),
            (3, "一步步变强、被认可的成就感"),
            (4, "被准确说中内心、有人懂我的共鸣"),
            (5, "看懂全局、把碎片拼成真相的快感"),
        ],
    ),
    (
        "紧张刺激的场面，你偏好哪一种？",
        None,
        [
            (6, "敌暗我明，随时可能出事的悬疑"),
            (7, "节奏飞快的追逐与意外不断的冒险"),
            (8, "正面对决，靠实力碾压对手"),
            (9, "其实更想看冲突之后大家和好的日常"),
        ],
    ),
    (
        "通关一部作品后，你最先想到的是？",
        None,
        [
            (1, "哪里还不够完美，有没有漏掉的细节"),
            (2, "想推荐给朋友，和他聊聊里面的角色"),
            (3, "还差几个结局，去把收集度刷满"),
            (4, "心里空了一块，需要缓几天才走得出来"),
        ],
    ),
    (
        "卡关或读到不喜欢的段落时，你会？",
        None,
        [
            (5, "停下来分析机制，找出卡住的真正原因"),
            (6, "先查攻略确认没有坑，再继续推进"),
            (7, "跳过这段，换条路线找新的乐子"),
            (8, "硬啃过去，越难越要证明自己能行"),
        ],
    ),
    (
        "别人最常怎么形容你？",
        None,
        [
            (9, "好说话、没什么脾气，跟谁都能相处"),
            (1, "认真、有原则，对细节很挑剔"),
            (2, "体贴、会照顾人，总先想着别人"),
            (3, "目标明确、效率高，事情交给你放心"),
        ],
    ),
    (
        "最容易打动你的角色是？",
        None,
        [
            (4, "带着伤口仍然坚持自我的人"),
            (5, "沉默寡言、却在关键时刻看穿一切的人"),
            (6, "明知危险仍选择守住承诺的人"),
            (7, "走到哪都能把气氛点亮的人"),
        ],
    ),
    (
        "团队意见僵持不下时，你会？",
        None,
        [
            (8, "拍板定方向，责任由我来担"),
            (9, "先让大家冷静，找一个都能接受的折中"),
            (1, "回到规则和标准，按最合理的方案来"),
            (2, "先听每个人怎么想，别让谁被忽略"),
        ],
    ),
    (
        "做重要决定时，你更依赖？",
        None,
        [
            (3, "目标和结果：哪条路能最快达成"),
            (4, "直觉和感受：哪个选择更像真正的我"),
            (5, "信息和推演：把可能性都算一遍"),
            (6, "风险评估：先想清楚最坏会怎样"),
        ],
    ),
    (
        "如果有一周假期，你会？",
        None,
        [
            (7, "说走就走，去没计划过的地方"),
            (8, "挑战一项有难度的目标，比如登山或比赛"),
            (9, "找个安静的地方慢慢待着，不安排行程"),
            (1, "提前做好详细攻略，把时间用在刀刃上"),
        ],
    ),
    (
        "你希望别人记住你的哪一面？",
        None,
        [
            (2, "在他们需要的时候，我一直在"),
            (3, "我做成过什么，留下了什么成果"),
            (4, "我是独一无二的，有自己的表达"),
            (5, "我看得比一般人更深、更清楚"),
        ],
    ),
    (
        "压力突然压过来时，你的第一反应是？",
        None,
        [
            (6, "先预演最坏情况，准备好应对方案"),
            (7, "找点新鲜事转移注意力，别被困住"),
            (8, "顶回去，压力越大我越来劲"),
            (9, "先放一放，等情绪平复了再说"),
        ],
    ),
]


def _build_questions() -> list[dict]:
    questions: list[dict] = []
    for index, (title, subtitle, options) in enumerate(_QUESTION_SPECS, start=1):
        question: dict = {"id": f"q{index:02d}", "title": title}
        if subtitle:
            question["subtitle"] = subtitle
        question["options"] = [
            {
                "id": f"q{index:02d}_t{type_no}",
                "label": label,
                "type": type_no,
                "tags": dict(OPTION_TAGS[type_no]),
            }
            for type_no, label in options
        ]
        questions.append(question)
    return questions


QUESTIONS: list[dict] = _build_questions()

_OPTION_TYPE: dict[tuple[str, str], int] = {
    (question["id"], option["id"]): option["type"]
    for question in QUESTIONS
    for option in question["options"]
}

# 每个类型在整份问卷中出现的题数，用于把原始计数归一化到 0-100。
TYPE_SLOTS: dict[int, int] = {
    type_no: sum(
        1
        for question in QUESTIONS
        if any(option["type"] == type_no for option in question["options"])
    )
    for type_no in TYPES
}


def filter_answers(answers: dict[str, str] | None) -> dict[str, str]:
    """只保留合法的 question_id -> option_id，其余一律忽略。"""
    if not isinstance(answers, dict):
        return {}
    cleaned: dict[str, str] = {}
    for question_id, option_id in answers.items():
        if not isinstance(question_id, str) or not isinstance(option_id, str):
            continue
        if (question_id, option_id) in _OPTION_TYPE:
            cleaned[question_id] = option_id
    return cleaned


def _empty_result() -> dict:
    return {
        "code": "",
        "labels": [],
        "tags": {},
        "year_center": None,
        "length_center": None,
        "completed": False,
        "scores": {str(type_no): 0 for type_no in TYPES},
        "wing": None,
        "center": None,
    }


def _tags_for(main: int, wing: int) -> dict[str, float]:
    merged: dict[str, float] = dict(TYPE_TAGS[main])
    for name, weight in WING_TAGS[wing].items():
        merged[name] = merged.get(name, 0.0) + weight
    ordered = sorted(merged.items(), key=lambda item: (-item[1], item[0]))
    return {name: round(weight, 2) for name, weight in ordered}


def calculate(answers: dict[str, str] | None) -> dict:
    """统计各型次数得到主型与侧翼；非法答案忽略，空答案不抛异常。"""
    cleaned = filter_answers(answers)
    if not cleaned:
        return _empty_result()

    counts: dict[int, int] = {type_no: 0 for type_no in TYPES}
    for question_id, option_id in cleaned.items():
        counts[_OPTION_TYPE[(question_id, option_id)]] += 1

    total = sum(counts.values())
    scores = {
        str(type_no): (
            int(round(100 * counts[type_no] / TYPE_SLOTS[type_no]))
            if TYPE_SLOTS[type_no]
            else 0
        )
        for type_no in TYPES
    }

    # 主型同分时取编号较大者，保证结果唯一。
    main = max(TYPES, key=lambda type_no: (counts[type_no], type_no))
    left, right = NEIGHBORS[main]
    # 侧翼同分时同样取编号较大者，code 中直接体现实际选择。
    wing = max((left, right), key=lambda type_no: (counts[type_no], type_no))

    main_name = TYPE_NAMES[main]
    wing_name = TYPE_NAMES[wing]
    center = CENTER_BY_TYPE[main]

    return {
        "code": f"{main}w{wing} {main_name}·{wing_name}侧翼",
        "labels": [main_name, f"{wing_name}侧翼", center],
        "tags": _tags_for(main, wing),
        "year_center": None,
        "length_center": None,
        "completed": total == len(QUESTIONS),
        "scores": scores,
        "wing": wing,
        "center": center,
    }
