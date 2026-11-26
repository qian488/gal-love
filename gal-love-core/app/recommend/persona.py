"""画像提供者注册表与通用画像构建。

每个画像体系是一个独立模块，暴露 ``KEY`` / ``TITLE`` 与 ``calculate(answers)``；
本模块负责把它们统一成推荐引擎可直接使用的 ``UserProfile``。

新增体系只需要在 ``app/recommend`` 下新建 ``persona_xxx.py``，无需改动
引擎与 API：注册表按模块名自动发现，缺失或导入失败的模块会被跳过。
"""

from __future__ import annotations

import importlib
import logging
import math
import sqlite3
from typing import Any, Iterable

from ..normalize import normalize_text, now_iso
from ..repository import get_settings, set_settings
from ..tag_zh import canonical_lookup_keys
from .engine import FeatureIndex, UserProfile

logger = logging.getLogger(__name__)

# 约定：模块文件名 persona_<key>.py，模块内暴露 KEY 常量。
PROVIDER_MODULES: tuple[str, ...] = (
    "persona_quiz",
    "persona_motivation",
    "persona_enneagram",
    "persona_bigfive",
    "persona_zodiac",
    "persona_pairwise",
    "persona_tarot",
)

# 合并首页画像时的可信度权重。缺少某个来源时，剩余权重会自动归一化。
SOURCE_WEIGHTS: dict[str, float] = {
    "library": 0.45,
    "pairwise": 0.30,
    "quiz": 0.15,
    "motivation": 0.15,
    "enneagram": 0.15,
    "bigfive": 0.15,
    "zodiac": 0.05,
}
DEFAULT_PROVIDER_WEIGHT = 0.10
INCOMPLETE_PENALTY = 0.6

BASE_SOURCES: tuple[str, ...] = ("auto", "library", "all")


def _load_registry() -> dict[str, Any]:
    registry: dict[str, Any] = {}
    for name in PROVIDER_MODULES:
        try:
            module = importlib.import_module(f"{__package__}.{name}")
        except Exception:  # noqa: BLE001 - 单个模块出错不应拖垮整个 API
            logger.warning("persona provider %s unavailable", name, exc_info=True)
            continue
        key = getattr(module, "KEY", None)
        if isinstance(key, str) and key:
            registry[key] = module
    return registry


_REGISTRY: dict[str, Any] = _load_registry()


def reload_registry() -> dict[str, Any]:
    """重新扫描提供者模块，供测试或开发期热加载使用。"""
    global _REGISTRY
    _REGISTRY = _load_registry()
    return _REGISTRY


def provider_keys() -> tuple[str, ...]:
    return tuple(_REGISTRY)


def allowed_sources() -> tuple[str, ...]:
    return BASE_SOURCES + provider_keys()


def source_pattern() -> str:
    return "^(" + "|".join(allowed_sources()) + ")$"


def get_provider(key: str) -> Any:
    module = _REGISTRY.get(key)
    if module is None:
        raise KeyError(key)
    return module


def _meta(module: Any) -> dict[str, Any]:
    questions = getattr(module, "QUESTIONS", None) or []
    return {
        "key": str(getattr(module, "KEY", "")),
        "title": str(getattr(module, "TITLE", getattr(module, "KEY", ""))),
        "subtitle": str(getattr(module, "SUBTITLE", "")),
        "kind": str(getattr(module, "KIND", "questionnaire")),
        "group": str(getattr(module, "GROUP", "other")),
        "estimated_minutes": int(getattr(module, "ESTIMATED_MINUTES", 3) or 3),
        "question_count": len(questions),
        "notice": getattr(module, "NOTICE", None),
    }


def _persona_buckets(settings: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """读取画像存储，并把旧的 quiz_answers / quiz_profile 迁移成新结构。"""
    stored = settings.get("persona_profiles")
    buckets: dict[str, dict[str, Any]] = (
        {key: value for key, value in stored.items() if isinstance(value, dict)}
        if isinstance(stored, dict)
        else {}
    )
    if "quiz" not in buckets:
        answers = settings.get("quiz_answers")
        profile = settings.get("quiz_profile")
        if answers or profile:
            buckets["quiz"] = {"answers": answers or {}, "profile": profile}
    return buckets


def list_providers(settings: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    buckets = _persona_buckets(settings or {})
    items: list[dict[str, Any]] = []
    for key, module in _REGISTRY.items():
        bucket = buckets.get(key) or {}
        result = bucket.get("profile") or {}
        item = _meta(module)
        item["completed"] = bool(isinstance(result, dict) and result.get("completed"))
        item["code"] = result.get("code") if isinstance(result, dict) else None
        item["labels"] = list(result.get("labels") or []) if isinstance(result, dict) else []
        items.append(item)
    order = {"quick": 0, "play": 1, "fun": 2, "serious": 3}
    items.sort(key=lambda item: (order.get(item.get("group"), 9), item["title"]))
    return items


def provider_payload(conn: sqlite3.Connection, key: str) -> dict[str, Any]:
    module = get_provider(key)
    settings = get_settings(conn)
    bucket = _persona_buckets(settings).get(key) or {}
    result = bucket.get("profile")
    if not isinstance(result, dict) or not result:
        result = module.calculate({})
    payload = _meta(module)
    payload.update(
        {
            "questions": getattr(module, "QUESTIONS", None) or [],
            "answers": bucket.get("answers") or {},
            "result": result,
            "updated_at": bucket.get("updated_at"),
            "extra": getattr(module, "EXTRA", None),
        }
    )
    return payload


def _clean_answers(module: Any, answers: dict[str, str] | None) -> dict[str, str]:
    if not isinstance(answers, dict):
        return {}
    cleaner = getattr(module, "filter_answers", None)
    if callable(cleaner):
        return cleaner(answers)
    return {str(key): str(value) for key, value in answers.items()}


def save_provider(
    conn: sqlite3.Connection, key: str, answers: dict[str, str] | None
) -> dict[str, Any]:
    module = get_provider(key)
    cleaned = _clean_answers(module, answers)
    result = module.calculate(cleaned)
    buckets = _persona_buckets(get_settings(conn))
    buckets[key] = {"answers": cleaned, "profile": result, "updated_at": now_iso()}
    values: dict[str, Any] = {"persona_profiles": buckets}
    if key == "quiz":
        # 兼容旧字段，避免回滚或旧前端读到空画像。
        values["quiz_answers"] = cleaned
        values["quiz_profile"] = result
    set_settings(conn, values)
    return provider_payload(conn, key)


def save_provider_profile(
    conn: sqlite3.Connection, key: str, result: dict[str, Any], answers: dict[str, Any] | None = None
) -> dict[str, Any]:
    """直接写入已算好的画像，供二选一这类增量场景使用。"""
    get_provider(key)
    buckets = _persona_buckets(get_settings(conn))
    buckets[key] = {
        "answers": answers or {},
        "profile": result,
        "updated_at": now_iso(),
    }
    values: dict[str, Any] = {"persona_profiles": buckets}
    if key == "quiz":
        values["quiz_answers"] = answers or {}
        values["quiz_profile"] = result
    set_settings(conn, values)
    return result


def _normalize(vector: dict[int, float]) -> dict[int, float]:
    norm = math.sqrt(sum(value * value for value in vector.values()))
    if norm <= 0:
        return {}
    return {key: value / norm for key, value in vector.items()}


def _center_value(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _tag_keys(name: str) -> set[str]:
    keys = {normalize_text(name)}
    keys.update(canonical_lookup_keys(name))
    return {key for key in keys if key}


def build_tag_profile(
    result: dict[str, Any], index: FeatureIndex, source: str
) -> UserProfile:
    """把 {tags: {标签名: 权重}} 形式的画像转成标签 id 向量。"""
    lookup: dict[str, list[int]] = {}
    for tag_id, name in index.tag_names.items():
        for key in _tag_keys(name):
            lookup.setdefault(key, []).append(tag_id)

    positive: dict[int, float] = {}
    for name, raw_weight in (result.get("tags") or {}).items():
        if not isinstance(name, str):
            continue
        try:
            weight = float(raw_weight)
        except (TypeError, ValueError):
            continue
        if weight <= 0:
            continue
        matched: list[int] = []
        for key in _tag_keys(name):
            matched = lookup.get(key) or []
            if matched:
                break
        for tag_id in matched:
            positive[tag_id] = positive.get(tag_id, 0.0) + weight

    labels = [str(label) for label in (result.get("labels") or []) if isinstance(label, str)]
    return UserProfile(
        vector=_normalize(positive),
        negative_vector={},
        company_weights={},
        liked_work_ids=[],
        disliked_work_ids=set(),
        year_center=_center_value(result.get("year_center")),
        length_center=_center_value(result.get("length_center")),
        has_profile=bool(positive),
        source=source,
        quiz_labels=labels,
    )


def _weighted_average(values: Iterable[tuple[float, float]]) -> float | None:
    total = 0.0
    total_weight = 0.0
    for value, weight in values:
        if weight <= 0:
            continue
        total += value * weight
        total_weight += weight
    return total / total_weight if total_weight > 0 else None


def merge_profiles_weighted(
    items: Iterable[tuple[UserProfile, float]]
) -> UserProfile | None:
    """按权重合并多份画像；权重会自动归一，向量过小则回退到最强来源。"""
    usable = [
        (profile, float(weight))
        for profile, weight in items
        if weight > 0 and profile.has_profile
    ]
    if not usable:
        return None

    vector: dict[int, float] = {}
    negative: dict[int, float] = {}
    companies: dict[int, float] = {}
    years: list[tuple[float, float]] = []
    lengths: list[tuple[float, float]] = []
    labels: list[str] = []
    for profile, weight in usable:
        for tag_id, value in profile.vector.items():
            vector[tag_id] = vector.get(tag_id, 0.0) + value * weight
        for tag_id, value in profile.negative_vector.items():
            negative[tag_id] = negative.get(tag_id, 0.0) + value * weight
        for company_id, value in profile.company_weights.items():
            companies[company_id] = companies.get(company_id, 0.0) + value * weight
        if profile.year_center is not None:
            years.append((profile.year_center, weight))
        if profile.length_center is not None:
            lengths.append((profile.length_center, weight))
        labels.extend(profile.quiz_labels)

    merged = UserProfile(
        vector=_normalize(vector),
        negative_vector=_normalize(negative),
        company_weights=companies,
        liked_work_ids=sorted(
            {work_id: weight for profile, _ in usable for work_id, weight in profile.liked_work_ids}.items(),
            key=lambda item: item[1],
            reverse=True,
        ),
        disliked_work_ids={work_id for profile, _ in usable for work_id in profile.disliked_work_ids},
        year_center=_weighted_average(years),
        length_center=_weighted_average(lengths),
        has_profile=bool(vector),
        source="all",
        quiz_labels=list(dict.fromkeys(labels)),
    )
    if not merged.has_profile:
        best = max(usable, key=lambda item: item[1])
        return best[0]
    return merged


def _stored_profile(
    buckets: dict[str, dict[str, Any]], key: str, index: FeatureIndex
) -> UserProfile | None:
    bucket = buckets.get(key) or {}
    result = bucket.get("profile")
    if not isinstance(result, dict) or not result:
        return None
    profile = build_tag_profile(result, index, key)
    if not profile.has_profile:
        return None
    return profile


def _available_sources(settings: dict[str, Any], buckets: dict[str, dict[str, Any]]) -> list[str]:
    selected = settings.get("home_profile_sources")
    if isinstance(selected, list) and selected:
        return [str(source) for source in selected]
    return ["library"] + [key for key in buckets if key != "tarot"]


def _source_weight(key: str, bucket: dict[str, Any]) -> float:
    base = SOURCE_WEIGHTS.get(key, DEFAULT_PROVIDER_WEIGHT)
    result = bucket.get("profile") or {}
    if isinstance(result, dict) and not result.get("completed"):
        base *= INCOMPLETE_PENALTY
    return base


def has_any_profile(settings: dict[str, Any]) -> bool:
    """是否存在任何可用问卷/星座结果（不关心首页来源选择）。"""
    buckets = _persona_buckets(settings)
    for key, bucket in buckets.items():
        if key == "tarot" or key not in _REGISTRY:
            continue
        result = bucket.get("profile") or {}
        if isinstance(result, dict) and result.get("tags"):
            return True
    return False


def has_mergeable_profile(settings: dict[str, Any]) -> bool:
    """首页「综合画像」是否真的有内容可合并（尊重 home_profile_sources）。"""
    buckets = _persona_buckets(settings)
    for key in _available_sources(settings, buckets):
        if key == "library" or key == "tarot" or key not in _REGISTRY:
            continue
        result = (buckets.get(key) or {}).get("profile") or {}
        if isinstance(result, dict) and result.get("tags"):
            return True
    return False


def resolve_profile(
    conn: sqlite3.Connection,
    index: FeatureIndex,
    source: str,
    library_profile: UserProfile,
    settings: dict[str, Any] | None = None,
) -> UserProfile:
    """按 source 取出（或合并出）实际用于推荐的画像。"""
    settings = settings or get_settings(conn)
    buckets = _persona_buckets(settings)

    if source == "library":
        return library_profile

    if source == "all":
        selected = _available_sources(settings, buckets)
        items: list[tuple[UserProfile, float]] = []
        if "library" in selected:
            items.append((library_profile, SOURCE_WEIGHTS["library"]))
        for key in selected:
            if key == "library" or key not in _REGISTRY:
                continue
            profile = _stored_profile(buckets, key, index)
            if profile is not None:
                items.append((profile, _source_weight(key, buckets.get(key) or {})))
        if len(items) <= 1 and items and items[0][0] is library_profile:
            # 只勾选了游戏库时不要把来源标成 all。
            return library_profile
        return merge_profiles_weighted(items) or library_profile

    profile = _stored_profile(buckets, source, index)
    return profile or UserProfile(
        vector={},
        negative_vector={},
        company_weights={},
        liked_work_ids=[],
        disliked_work_ids=set(),
        year_center=None,
        length_center=None,
        has_profile=False,
        source=source,
    )
