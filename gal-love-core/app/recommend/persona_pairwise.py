"""作品二选一画像：用真实作品的两两比较建立口味画像。

没有固定题目，改从作品库里挑出标签差异较大的两部作品让用户选择，
再按被选中作品的标签权重累积偏好。画像结果仍写入统一的 provider 存储，
由 ``persona.build_tag_profile`` 转成引擎可用的标签向量。
"""

from __future__ import annotations

import math
import random
import sqlite3
from typing import Any

from ..normalize import now_iso
from ..repository import get_settings, get_work, set_settings
from ..tag_zh import canonical_lookup
from . import persona
from .engine import FeatureIndex

KEY = "pairwise"
TITLE = "作品二选一"
SUBTITLE = "10 轮选择，直接从真实偏好建立画像"
KIND = "pairwise"
GROUP = "quick"
ESTIMATED_MINUTES = 3
QUESTIONS: list[dict[str, Any]] = []
NOTICE = "选择结果只保存在本地。"

TARGET_ROUNDS = 10
RECENT_LIMIT = 20
MAX_PAIRS = 5
POOL_LIMIT = 120
LOSER_PENALTY = 0.25

# 常见标签的中文短词，未命中的标签回退到内置译名或英文原名。
TAG_LABELS_ZH: dict[str, str] = {
    "romance": "恋爱",
    "comedy": "喜剧",
    "school": "校园",
    "fantasy": "奇幻",
    "drama": "剧情",
    "mystery": "悬疑",
    "horror": "恐怖",
    "sci-fi": "科幻",
    "science fiction": "科幻",
    "slice of life": "日常",
    "psychological": "心理",
    "thriller": "惊悚",
    "supernatural": "超自然",
    "magic": "魔法",
    "mecha": "机甲",
    "historical": "历史",
    "war": "战争",
    "sports": "运动",
    "music": "音乐",
    "action": "动作",
    "adventure": "冒险",
    "tragedy": "悲剧",
    "tearjerker": "催泪",
    "multiple endings": "多结局",
    "friendship": "友情",
    "family": "家庭",
    "detective": "侦探",
    "philosophical": "哲学",
    "yuri": "百合",
    "otome": "乙女",
}


def _as_float(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    return number if math.isfinite(number) else 0.0


def _recent(state: dict[str, Any]) -> list[int]:
    values: list[int] = []
    for item in state.get("recent") or []:
        try:
            values.append(int(item))
        except (TypeError, ValueError):
            continue
    return values[-RECENT_LIMIT:]


def _load_state(conn: sqlite3.Connection) -> dict[str, Any]:
    settings = get_settings(conn)
    profiles = settings.get("persona_profiles")
    if not isinstance(profiles, dict):
        return {}
    bucket = profiles.get(KEY)
    if not isinstance(bucket, dict):
        return {}
    answers = bucket.get("answers")
    return dict(answers) if isinstance(answers, dict) else {}


def _remember_recent(conn: sqlite3.Connection, work_ids: list[int]) -> None:
    """把刚展示过的作品追加进 recent，避免下一次抽样立刻重复。"""
    if not work_ids:
        return
    settings = get_settings(conn)
    profiles = settings.get("persona_profiles")
    profiles = dict(profiles) if isinstance(profiles, dict) else {}
    bucket = profiles.get(KEY)
    bucket = dict(bucket) if isinstance(bucket, dict) else {}
    answers = bucket.get("answers")
    answers = dict(answers) if isinstance(answers, dict) else {}
    recent = _recent(answers)
    for work_id in work_ids:
        recent.append(int(work_id))
    answers["recent"] = recent[-RECENT_LIMIT:]
    bucket["answers"] = answers
    profiles[KEY] = bucket
    set_settings(conn, {"persona_profiles": profiles})


def _jaccard(left: set[int], right: set[int]) -> float:
    if not left or not right:
        return 0.0
    union = left | right
    return len(left & right) / len(union) if union else 0.0


def _candidates(
    conn: sqlite3.Connection, index: FeatureIndex, include_nsfw: bool
) -> list[dict[str, Any]]:
    """抽样候选池：封面、标签、投票数与评分决定质量分。"""
    rows = conn.execute(
        """
        SELECT w.id, w.cover_url, w.nsfw, w.vndb_votecount, w.vndb_rating, w.rating
        FROM works w
        WHERE NOT EXISTS (SELECT 1 FROM my_entries e WHERE e.work_id = w.id)
        """
    ).fetchall()

    items: list[dict[str, Any]] = []
    for row in rows:
        work_id = int(row["id"])
        if not include_nsfw and row["nsfw"]:
            continue
        feature = index.works.get(work_id)
        if feature is None or not feature.tag_ids:
            # 没有标签的作品无法计算区分度，也不利于建立画像。
            continue
        score = 1.0
        if row["cover_url"]:
            score += 2.5
        votecount = row["vndb_votecount"] or 0
        if votecount:
            score += min(3.0, math.log10(votecount + 1))
        rating = row["rating"]
        if rating is None and row["vndb_rating"] is not None:
            rating = float(row["vndb_rating"]) / 10.0
        if rating is not None:
            score += max(0.0, min(10.0, float(rating))) / 10.0
        items.append({"id": work_id, "tags": set(feature.tag_ids), "score": score})

    items.sort(key=lambda item: item["score"], reverse=True)
    return items[:POOL_LIMIT]


def _weighted_pick(items: list[dict[str, Any]], rng: random.Random) -> dict[str, Any]:
    total = sum(max(0.001, item["score"]) for item in items)
    target = rng.random() * total
    cumulative = 0.0
    for item in items:
        cumulative += max(0.001, item["score"])
        if cumulative >= target:
            return item
    return items[-1]


def _select_pair(
    pool: list[dict[str, Any]],
    used: set[int],
    recent: set[int],
    rng: random.Random,
) -> tuple[dict[str, Any], dict[str, Any]] | None:
    available = [item for item in pool if item["id"] not in used]
    if len(available) < 2:
        return None
    fresh = [item for item in available if item["id"] not in recent]
    # 新作品不够时回退到最近出现过的作品，避免小作品库无牌可出。
    primary = fresh if len(fresh) >= 2 else available
    left = _weighted_pick(primary, rng)

    rest_fresh = [item for item in fresh if item["id"] != left["id"]]
    rest = rest_fresh or [item for item in available if item["id"] != left["id"]]
    scored = [(_jaccard(left["tags"], item["tags"]), item) for item in rest]
    lowest = min(value for value, _ in scored)
    close = [item for value, item in scored if value <= lowest + 0.05]
    right = _weighted_pick(close, rng)
    return left, right


def next_pairs(
    conn: sqlite3.Connection, *, count: int = 1, include_nsfw: bool = False
) -> list[dict[str, Any]]:
    """返回若干组「左 vs 右」作品；数据不足时返回空列表。"""
    try:
        count = int(count)
    except (TypeError, ValueError):
        count = 1
    count = max(1, min(MAX_PAIRS, count))

    index = FeatureIndex.build(conn)
    pool = _candidates(conn, index, include_nsfw)
    if len(pool) < 2:
        return []

    state = _load_state(conn)
    recent_ids = set(_recent(state))
    rng = random.Random()

    pairs: list[dict[str, Any]] = []
    used: set[int] = set()
    served: list[int] = []
    for _ in range(count):
        chosen = _select_pair(pool, used, recent_ids, rng)
        if chosen is None:
            break
        left, right = chosen
        left_work = get_work(conn, left["id"])
        right_work = get_work(conn, right["id"])
        if not left_work or not right_work:
            used.add(left["id"])
            continue
        pairs.append({"left": left_work, "right": right_work})
        used.update((left["id"], right["id"]))
        served.extend((left["id"], right["id"]))
        # 同一批里的后续组也应避开刚出现的作品。
        recent_ids.update((left["id"], right["id"]))

    _remember_recent(conn, served)
    return pairs


def _weighted_center(values: Any) -> float | None:
    total = 0.0
    weight_sum = 0.0
    for entry in values or []:
        if not isinstance(entry, (list, tuple)) or len(entry) != 2:
            continue
        value, weight = _as_float(entry[0]), _as_float(entry[1])
        if weight <= 0:
            continue
        total += value * weight
        weight_sum += weight
    if weight_sum <= 0:
        return None
    return round(total / weight_sum, 1)


def _label(name: str) -> str:
    key = name.strip().casefold()
    if key in TAG_LABELS_ZH:
        return TAG_LABELS_ZH[key]
    info = canonical_lookup(name)
    if info:
        return info[1]
    return name


def _build_result(state: dict[str, Any], completed: bool, answered: int) -> dict[str, Any]:
    tags = {
        name: round(_as_float(weight), 4)
        for name, weight in (state.get("tags") or {}).items()
        if isinstance(name, str) and _as_float(weight) > 0
    }
    ranked = sorted(tags.items(), key=lambda item: (-item[1], item[0]))
    labels = list(dict.fromkeys(_label(name) for name, _ in ranked[:2]))
    result: dict[str, Any] = {
        "code": ("偏好" + "与".join(labels)) if labels else "探索中的口味",
        "labels": labels,
        "tags": tags,
        "year_center": _weighted_center(state.get("year_values")),
        "length_center": _weighted_center(state.get("length_values")),
        "completed": bool(completed),
        "answered": int(answered),
    }
    negative = {
        name: round(_as_float(weight), 4)
        for name, weight in (state.get("negative_tags") or {}).items()
        if isinstance(name, str) and _as_float(weight) < 0
    }
    if negative:
        result["negative_tags"] = negative
    return result


def calculate(answers: dict[str, Any]) -> dict[str, Any]:
    """二选一没有表单答案，保持 provider 契约的空画像。"""
    return {
        "code": "",
        "labels": [],
        "tags": {},
        "year_center": None,
        "length_center": None,
        "completed": False,
        "answered": 0,
    }


def record_choice(
    conn: sqlite3.Connection,
    *,
    winner_id: int,
    loser_id: int,
    skipped: bool = False,
) -> dict[str, Any]:
    """记录一轮选择并返回最新的增量画像。"""
    state = _load_state(conn)
    choices = list(state.get("choices") or [])
    recent = _recent(state)
    tags = dict(state.get("tags") or {})
    negative = dict(state.get("negative_tags") or {})
    years = [
        [entry[0], entry[1]]
        for entry in state.get("year_values") or []
        if isinstance(entry, (list, tuple)) and len(entry) == 2
    ]
    lengths = [
        [entry[0], entry[1]]
        for entry in state.get("length_values") or []
        if isinstance(entry, (list, tuple)) and len(entry) == 2
    ]

    winner = get_work(conn, int(winner_id))
    loser = get_work(conn, int(loser_id))
    choices.append(
        {
            "winner_id": int(winner_id),
            "loser_id": int(loser_id),
            "skipped": bool(skipped),
            "at": now_iso(),
        }
    )
    recent.extend((int(winner_id), int(loser_id)))

    if not skipped and winner:
        for tag in winner.get("tags") or []:
            name = str(tag.get("name") or "").strip()
            if not name:
                continue
            weight = _as_float(tag.get("weight")) or 1.0
            tags[name] = round(_as_float(tags.get(name)) + weight, 4)
        if winner.get("release_year"):
            years.append([float(winner["release_year"]), 1.0])
        if winner.get("length_minutes"):
            lengths.append([float(winner["length_minutes"]), 1.0])
        if loser:
            for tag in loser.get("tags") or []:
                name = str(tag.get("name") or "").strip()
                if not name:
                    continue
                weight = _as_float(tag.get("weight")) or 1.0
                negative[name] = round(
                    _as_float(negative.get(name)) - LOSER_PENALTY * weight, 4
                )

    answered = sum(1 for choice in choices if not choice.get("skipped"))
    completed = len(choices) >= TARGET_ROUNDS

    state.update(
        {
            "choices": choices,
            "recent": recent[-RECENT_LIMIT:],
            "tags": tags,
            "negative_tags": negative,
            "year_values": years,
            "length_values": lengths,
            "answered": answered,
            "completed": completed,
        }
    )
    result = _build_result(state, completed, answered)
    persona.save_provider_profile(conn, KEY, result, state)
    return result


def reset(conn: sqlite3.Connection) -> None:
    """清空二选一画像，不影响其他 provider 的结果。"""
    settings = get_settings(conn)
    profiles = settings.get("persona_profiles")
    if not isinstance(profiles, dict) or KEY not in profiles:
        return
    remaining = {key: value for key, value in profiles.items() if key != KEY}
    set_settings(conn, {"persona_profiles": remaining})
