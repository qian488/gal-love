"""Content-based recommendation engine (v1).

The first version is intentionally explainable: tag TF-IDF similarity, developer
affinity, era/length closeness and external quality. A later version will add
collaborative filtering from the VNDB votes dump.
"""

from __future__ import annotations

import math
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from ..normalize import json_loads, normalize_text
from ..repository import get_feedback_work_ids, get_settings, get_work
from ..tag_zh import canonical_lookup_keys
from . import cf
from .votes import has_votes, votes_db_path

ALGORITHM_VERSION = "content-v1"
HYBRID_ALGORITHM_VERSION = "hybrid-v1+votes"

# Hybrid ranking weights (sum = 1.0). Tune these without touching callers.
HYBRID_CONTENT_WEIGHT = 0.55
HYBRID_CF_WEIGHT = 0.35
HYBRID_QUALITY_WEIGHT = 0.06
HYBRID_NOVELTY_WEIGHT = 0.04
SIMILAR_CF_WEIGHT = 0.35
CF_MIN_CO_VOTES = 2
CF_TOP_K = 30
CF_REASON_THRESHOLD = 0.05


def _resolve_votes_db(
    conn: sqlite3.Connection, votes_db: Path | str | None = None
) -> Path | None:
    """Locate the votes database for a main-library connection."""
    if votes_db is not None:
        return Path(votes_db).expanduser()
    try:
        row = conn.execute("PRAGMA database_list").fetchone()
        main_file = row["file"] if row else None
    except sqlite3.Error:
        main_file = None
    if not main_file:
        return None
    return votes_db_path(Path(main_file))


def algorithm_version(
    conn: sqlite3.Connection, votes_db: Path | str | None = None
) -> str:
    """Return the algorithm version implied by the available votes data."""
    path = _resolve_votes_db(conn, votes_db)
    if path is not None and has_votes(path):
        return HYBRID_ALGORITHM_VERSION
    return ALGORITHM_VERSION


def _resolve_algorithm(algorithm: str | None) -> str:
    mode = "auto" if algorithm is None else str(algorithm).strip().casefold()
    if mode not in {"auto", "content", "hybrid"}:
        raise ValueError(f"unknown algorithm: {algorithm!r} (expected content/hybrid/auto)")
    return mode


@dataclass
class WorkFeature:
    id: int
    title: str
    vector: dict[int, float] = field(default_factory=dict)
    tag_ids: set[int] = field(default_factory=set)
    company_ids: set[int] = field(default_factory=set)
    platforms: set[str] = field(default_factory=set)
    languages: set[str] = field(default_factory=set)
    year: int | None = None
    length_minutes: int | None = None
    rating: float | None = None
    rating_count: int | None = None
    nsfw: bool = False


@dataclass
class FeatureIndex:
    works: dict[int, WorkFeature]
    tag_names: dict[int, str]
    company_names: dict[int, str]

    @classmethod
    def build(cls, conn: sqlite3.Connection) -> "FeatureIndex":
        works: dict[int, WorkFeature] = {}
        for row in conn.execute(
            "SELECT id, title, release_year, length_minutes, rating, rating_count, nsfw, platforms, languages FROM works"
        ).fetchall():
            works[int(row["id"])] = WorkFeature(
                id=int(row["id"]),
                title=row["title"],
                year=row["release_year"],
                length_minutes=row["length_minutes"],
                rating=row["rating"],
                rating_count=row["rating_count"],
                nsfw=bool(row["nsfw"]),
                platforms={str(item).casefold() for item in json_loads(row["platforms"], [])},
                languages={str(item).casefold() for item in json_loads(row["languages"], [])},
            )

        tag_rows = conn.execute(
            """
            SELECT wt.work_id, wt.tag_id, wt.weight, wt.spoiler, t.name
            FROM work_tags wt JOIN tags t ON t.id = wt.tag_id
            """
        ).fetchall()
        tag_names: dict[int, str] = {}
        doc_freq: dict[int, int] = {}
        raw: dict[int, dict[int, float]] = {work_id: {} for work_id in works}
        for row in tag_rows:
            work_id = int(row["work_id"])
            tag_id = int(row["tag_id"])
            if work_id not in works:
                continue
            tag_names[tag_id] = row["name"]
            weight = max(0.1, float(row["weight"] or 1.0))
            if int(row["spoiler"] or 0) >= 2:
                weight *= 0.6
            current = raw[work_id].get(tag_id, 0.0)
            if weight > current:
                raw[work_id][tag_id] = weight
                if current == 0.0:
                    doc_freq[tag_id] = doc_freq.get(tag_id, 0) + 1

        total_docs = max(1, len(works))
        idf = {tag_id: math.log((total_docs + 1) / (freq + 1)) + 1.0 for tag_id, freq in doc_freq.items()}
        for work_id, vector in raw.items():
            weighted = {tag_id: weight * idf.get(tag_id, 1.0) for tag_id, weight in vector.items()}
            norm = math.sqrt(sum(value * value for value in weighted.values()))
            if norm > 0:
                weighted = {tag_id: value / norm for tag_id, value in weighted.items()}
            works[work_id].vector = weighted
            works[work_id].tag_ids = set(weighted)

        company_names: dict[int, str] = {}
        for row in conn.execute(
            """
            SELECT wc.work_id, wc.company_id, c.name
            FROM work_companies wc JOIN companies c ON c.id = wc.company_id
            """
        ).fetchall():
            work_id = int(row["work_id"])
            company_id = int(row["company_id"])
            company_names[company_id] = row["name"]
            if work_id in works:
                works[work_id].company_ids.add(company_id)

        return cls(works=works, tag_names=tag_names, company_names=company_names)


@dataclass
class UserProfile:
    vector: dict[int, float]
    negative_vector: dict[int, float]
    company_weights: dict[int, float]
    liked_work_ids: list[tuple[int, float]]
    disliked_work_ids: set[int]
    year_center: float | None
    length_center: float | None
    has_profile: bool
    source: str = "library"
    quiz_labels: list[str] = field(default_factory=list)


def _cosine(left: dict[int, float], right: dict[int, float]) -> float:
    if not left or not right:
        return 0.0
    if len(left) > len(right):
        left, right = right, left
    return sum(value * right.get(key, 0.0) for key, value in left.items())


def _normalize(vector: dict[int, float]) -> dict[int, float]:
    norm = math.sqrt(sum(value * value for value in vector.values()))
    if norm <= 0:
        return {}
    return {key: value / norm for key, value in vector.items()}


def _weighted_average(values: Iterable[tuple[float, float]]) -> float | None:
    total_weight = 0.0
    total = 0.0
    for value, weight in values:
        if weight <= 0:
            continue
        total += value * weight
        total_weight += weight
    return total / total_weight if total_weight > 0 else None


def build_profile(conn: sqlite3.Connection, index: FeatureIndex) -> UserProfile:
    positive: dict[int, float] = {}
    negative: dict[int, float] = {}
    company_weights: dict[int, float] = {}
    liked: list[tuple[int, float]] = []
    disliked: set[int] = set()
    year_values: list[tuple[float, float]] = []
    length_values: list[tuple[float, float]] = []

    rows = conn.execute(
        "SELECT work_id, status, rating, favorite FROM my_entries"
    ).fetchall()
    for row in rows:
        work_id = int(row["work_id"])
        feature = index.works.get(work_id)
        if not feature:
            continue
        rating = row["rating"]
        status = row["status"]
        weight = 0.0
        if rating is not None:
            weight = (float(rating) - 5.5) / 4.5
        if weight == 0.0:
            weight = {"finished": 0.55, "playing": 0.35, "want": 0.25, "dropped": -0.5}.get(status, 0.0)
        if row["favorite"]:
            weight += 0.35

        if weight > 0:
            liked.append((work_id, weight))
            for tag_id, value in feature.vector.items():
                positive[tag_id] = positive.get(tag_id, 0.0) + value * weight
            for company_id in feature.company_ids:
                company_weights[company_id] = company_weights.get(company_id, 0.0) + weight
            if feature.year:
                year_values.append((float(feature.year), weight))
            if feature.length_minutes:
                length_values.append((float(feature.length_minutes), weight))
        elif weight < 0:
            disliked.add(work_id)
            for tag_id, value in feature.vector.items():
                negative[tag_id] = negative.get(tag_id, 0.0) + value * abs(weight)

    return UserProfile(
        vector=_normalize(positive),
        negative_vector=_normalize(negative),
        company_weights=company_weights,
        liked_work_ids=sorted(liked, key=lambda item: item[1], reverse=True),
        disliked_work_ids=disliked,
        year_center=_weighted_average(year_values),
        length_center=_weighted_average(length_values),
        has_profile=bool(positive),
    )


def _profile_source_name(profile_source: str | None, settings: dict[str, Any]) -> str:
    from . import persona

    mode = "auto" if profile_source is None else str(profile_source).strip().casefold()
    if mode not in persona.allowed_sources():
        raise ValueError(f"unknown profile source: {profile_source!r}")
    if mode == "auto":
        if settings.get("quiz_merge_home", True) and persona.has_mergeable_profile(settings):
            return "all"
        return "library"
    return mode


def resolve_profile_source(conn: sqlite3.Connection, profile_source: str | None = None) -> str:
    """Return the profile source that a recommendation request would actually use."""
    return _profile_source_name(profile_source, get_settings(conn))


def _tag_name_keys(name: str) -> set[str]:
    keys = {normalize_text(name)}
    keys.update(canonical_lookup_keys(name))
    return {key for key in keys if key}


def _center_value(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def build_quiz_profile(conn: sqlite3.Connection, index: FeatureIndex) -> UserProfile:
    """Turn the stored quiz result into a UserProfile compatible with the engine.

    Quiz tag names are matched against ``index.tag_names`` by normalized name
    and known aliases, so ``Romance`` also matches a tag stored as ``romance``.
    A user without a quiz simply gets an empty quiz profile (cold start).
    """
    quiz = get_settings(conn).get("quiz_profile")
    quiz = quiz if isinstance(quiz, dict) else {}
    labels = [str(label) for label in (quiz.get("labels") or []) if isinstance(label, str)]

    lookup: dict[str, list[int]] = {}
    for tag_id, name in index.tag_names.items():
        for key in _tag_name_keys(name):
            lookup.setdefault(key, []).append(tag_id)

    positive: dict[int, float] = {}
    for name, raw_weight in (quiz.get("tags") or {}).items():
        if not isinstance(name, str):
            continue
        try:
            weight = float(raw_weight)
        except (TypeError, ValueError):
            continue
        if weight <= 0:
            continue
        matched: list[int] = []
        for key in _tag_name_keys(name):
            matched = lookup.get(key, [])
            if matched:
                break
        for tag_id in matched:
            positive[tag_id] = positive.get(tag_id, 0.0) + weight

    return UserProfile(
        vector=_normalize(positive),
        negative_vector={},
        company_weights={},
        liked_work_ids=[],
        disliked_work_ids=set(),
        year_center=_center_value(quiz.get("year_center")),
        length_center=_center_value(quiz.get("length_center")),
        has_profile=bool(positive),
        source="quiz",
        quiz_labels=labels,
    )


def _blend_vectors(left: dict[int, float], right: dict[int, float]) -> dict[int, float]:
    merged: dict[int, float] = {}
    for vector in (left, right):
        for key, value in vector.items():
            merged[key] = merged.get(key, 0.0) + float(value) * 0.5
    return merged


def merge_profiles(library: UserProfile, quiz: UserProfile) -> UserProfile:
    """Combine library and quiz preferences into a single profile."""
    liked = dict(library.liked_work_ids)
    liked.update(dict(quiz.liked_work_ids))
    centers = [
        (value, 1.0)
        for value in (library.year_center, quiz.year_center)
        if value is not None
    ]
    lengths = [
        (value, 1.0)
        for value in (library.length_center, quiz.length_center)
        if value is not None
    ]
    vector = _normalize(_blend_vectors(library.vector, quiz.vector))
    return UserProfile(
        vector=vector,
        negative_vector=_normalize(_blend_vectors(library.negative_vector, quiz.negative_vector)),
        company_weights=_blend_vectors(library.company_weights, quiz.company_weights),
        liked_work_ids=sorted(liked.items(), key=lambda item: item[1], reverse=True),
        disliked_work_ids=library.disliked_work_ids | quiz.disliked_work_ids,
        year_center=_weighted_average(centers),
        length_center=_weighted_average(lengths),
        has_profile=bool(vector),
        source="all",
        quiz_labels=list(quiz.quiz_labels),
    )


def _quality(feature: WorkFeature) -> float:
    if feature.rating is None:
        return 0.45
    return max(0.0, min(1.0, feature.rating / 10.0))


def _novelty(feature: WorkFeature) -> float:
    if not feature.rating_count:
        return 0.5
    return 1.0 - min(1.0, math.log10(feature.rating_count + 1) / 5.0)


def _year_similarity(feature: WorkFeature, center: float | None) -> float:
    if not feature.year or center is None:
        return 0.5
    return math.exp(-abs(feature.year - center) / 12.0)


def _length_similarity(feature: WorkFeature, center: float | None) -> float:
    if not feature.length_minutes or not center:
        return 0.5
    return math.exp(-abs(math.log1p(feature.length_minutes) - math.log1p(center)) / 1.5)


def _company_similarity(feature: WorkFeature, weights: dict[int, float]) -> float:
    if not feature.company_ids or not weights:
        return 0.0
    total = sum(weights.values())
    if total <= 0:
        return 0.0
    score = sum(weights.get(company_id, 0.0) for company_id in feature.company_ids)
    return min(1.0, score / total)


def _jaccard(left: set[int], right: set[int]) -> float:
    if not left or not right:
        return 0.0
    union = left | right
    return len(left & right) / len(union) if union else 0.0


def _shared_tags(
    candidate: WorkFeature,
    liked_work_ids: list[tuple[int, float]],
    index: FeatureIndex,
    limit: int = 3,
) -> tuple[int | None, list[str]]:
    best_work = None
    best_score = 0.0
    best_tags: list[str] = []
    candidate_tags = candidate.tag_ids
    for work_id, weight in liked_work_ids[:80]:
        liked = index.works.get(work_id)
        if not liked:
            continue
        shared = candidate_tags & liked.tag_ids
        if not shared:
            continue
        score = len(shared) * weight
        if score > best_score:
            best_score = score
            best_work = work_id
            best_tags = [
                index.tag_names[tag_id]
                for tag_id in sorted(shared, key=lambda tag_id: candidate.vector.get(tag_id, 0.0), reverse=True)[:limit]
                if tag_id in index.tag_names
            ]
    return best_work, best_tags


def _reason(
    candidate: WorkFeature,
    profile: UserProfile,
    index: FeatureIndex,
) -> tuple[str, list[str]]:
    if profile.source in {"quiz", "all"} and profile.quiz_labels and not profile.liked_work_ids:
        labels = "".join(f"「{label}」" for label in profile.quiz_labels[:3])
        return f"符合你的口味测试偏好：{labels}", []
    if profile.has_profile:
        liked_id, tags = _shared_tags(candidate, profile.liked_work_ids, index)
        if liked_id:
            liked_title = index.works[liked_id].title
            tag_text = "」「".join(tags) if tags else "相似题材"
            reason = f"因为你喜欢《{liked_title}》，你们都带有「{tag_text}」标签"
            company = next(
                (index.company_names[cid] for cid in candidate.company_ids if cid in profile.company_weights),
                None,
            )
            if company:
                reason += f"，并且同属 {company}"
            if candidate.rating is not None:
                reason += f"；外部评分 {candidate.rating:.1f}"
            return reason, tags
        company = next(
            (index.company_names[cid] for cid in candidate.company_ids if cid in profile.company_weights),
            None,
        )
        if company:
            return f"与你喜欢的作品同属 {company}；外部评分 {candidate.rating:.1f}" if candidate.rating else f"与你喜欢的作品同属 {company}", []

    if candidate.rating is not None and candidate.rating >= 8.0:
        votes = candidate.rating_count or 0
        if votes:
            return f"高口碑入门推荐：{candidate.rating:.1f} 分，{votes} 人评价", []
        return f"高口碑入门推荐：{candidate.rating:.1f} 分", []
    return "值得探索的作品，适合扩展你的口味边界", []


def _entry_map(conn: sqlite3.Connection) -> dict[int, dict[str, Any]]:
    return {
        int(row["work_id"]): dict(row)
        for row in conn.execute("SELECT * FROM my_entries").fetchall()
    }


def recommend(
    conn: sqlite3.Connection,
    *,
    limit: int = 20,
    include_nsfw: bool | None = None,
    min_year: int | None = None,
    max_length_minutes: int | None = None,
    platform: str | None = None,
    language: str | None = None,
    diversity: float | None = None,
    algorithm: str | None = None,
    profile_source: str | None = None,
    votes_db: Path | str | None = None,
    profile_override: UserProfile | None = None,
) -> list[dict[str, Any]]:
    """Recommend works, optionally blending collaborative filtering.

    ``algorithm=None`` / ``"auto"`` uses hybrid ranking when a usable votes
    database exists and falls back to content ranking otherwise. Explicit
    ``"content"`` or ``"hybrid"`` override the choice; an unavailable votes
    database always degrades gracefully to content ranking.
    """
    settings = get_settings(conn)
    if include_nsfw is None:
        include_nsfw = bool(settings.get("include_nsfw", False))
    if min_year is None:
        min_year = settings.get("min_year")
    if max_length_minutes is None:
        max_length_minutes = settings.get("max_length_minutes")
    if platform is None:
        platform = settings.get("platform")
    if language is None:
        language = settings.get("language")
    if diversity is None:
        diversity = float(settings.get("diversity", 0.15))

    mode = _resolve_algorithm(algorithm)
    votes_path = _resolve_votes_db(conn, votes_db)
    votes_ready = votes_path is not None and has_votes(votes_path)
    use_hybrid = votes_ready and mode in {"auto", "hybrid"}
    version = HYBRID_ALGORITHM_VERSION if use_hybrid else ALGORITHM_VERSION

    source = _profile_source_name(profile_source, settings)
    index = FeatureIndex.build(conn)
    if profile_override is not None:
        # 塔罗这类一次性玩法直接注入临时画像，不读取也不写入持久设置。
        profile = profile_override
    else:
        library_profile = build_profile(conn, index)
        from . import persona

        profile = persona.resolve_profile(conn, index, source, library_profile, settings)
    entries = _entry_map(conn)
    excluded = set(entries) | get_feedback_work_ids(conn, "not_interested")
    platform_key = platform.casefold() if platform else None
    language_key = language.casefold() if language else None

    work_similarity: dict[int, dict[int, float]] = {}
    seed_weights: dict[int, float] = {}
    if use_hybrid and votes_path is not None:
        work_similarity = cf.get_work_similarity(
            conn, votes_path, min_co_votes=CF_MIN_CO_VOTES, top_k=CF_TOP_K
        )
        seed_weights = {
            work_id: weight for work_id, weight in profile.liked_work_ids if weight > 0
        }
    cf_info: dict[int, tuple[float, int | None, int]] = {}

    candidates: list[tuple[float, WorkFeature]] = []
    for feature in index.works.values():
        if feature.id in excluded:
            continue
        if not include_nsfw and feature.nsfw:
            continue
        if min_year and feature.year and feature.year < min_year:
            continue
        if max_length_minutes and feature.length_minutes and feature.length_minutes > max_length_minutes:
            continue
        if platform_key and feature.platforms and platform_key not in feature.platforms:
            continue
        if language_key and feature.languages and language_key not in feature.languages:
            continue

        content = _cosine(profile.vector, feature.vector)
        negative = _cosine(profile.negative_vector, feature.vector)
        company = _company_similarity(feature, profile.company_weights)
        quality = _quality(feature)
        novelty = _novelty(feature)
        year_sim = _year_similarity(feature, profile.year_center)
        length_sim = _length_similarity(feature, profile.length_center)

        if profile.has_profile:
            content_score = (
                0.55 * content
                + 0.15 * company
                + 0.08 * year_sim
                + 0.04 * length_sim
                + 0.15 * quality
                + 0.03 * novelty
                - 0.35 * negative
            )
        else:
            content_score = 0.75 * quality + 0.15 * novelty + 0.10 * year_sim
        content_score = max(0.0, min(1.0, content_score))

        cf_value = 0.0
        if use_hybrid and work_similarity and seed_weights:
            cf_value, cf_seed, cf_matches = cf.candidate_cf_score(
                feature.id, seed_weights, work_similarity
            )
            cf_info[feature.id] = (cf_value, cf_seed, cf_matches)
        if use_hybrid:
            score = (
                HYBRID_CONTENT_WEIGHT * content_score
                + HYBRID_CF_WEIGHT * cf_value
                + HYBRID_QUALITY_WEIGHT * quality
                + HYBRID_NOVELTY_WEIGHT * novelty
            )
        else:
            score = content_score
        candidates.append((max(0.0, min(1.0, score)), feature))

    candidates.sort(key=lambda item: item[0], reverse=True)
    pool = candidates[: max(limit * 8, 100)]
    selected: list[tuple[float, WorkFeature]] = []
    while pool and len(selected) < limit:
        best_index = 0
        best_adjusted = -1.0
        for i, (score, feature) in enumerate(pool):
            max_sim = max((_jaccard(feature.tag_ids, chosen.tag_ids) for _, chosen in selected), default=0.0)
            adjusted = score - diversity * max_sim
            if adjusted > best_adjusted:
                best_adjusted = adjusted
                best_index = i
        selected.append(pool.pop(best_index))

    results: list[dict[str, Any]] = []
    for score, feature in selected:
        work = get_work(conn, feature.id)
        if not work:
            continue
        reason, tags = _reason(feature, profile, index)
        cf_value, cf_seed, cf_matches = cf_info.get(feature.id, (0.0, None, 0))
        if cf_seed is not None and cf_value >= CF_REASON_THRESHOLD:
            seed_title = index.works[cf_seed].title if cf_seed in index.works else "你喜欢的作品"
            reason = f"投票口味相近的玩家也喜欢《{seed_title}》"
            if cf_matches > 1:
                reason += f"等 {cf_matches} 部你喜欢的作品"
            if tags:
                reason += f"；共同标签「{'」「'.join(tags)}」"
            elif feature.rating is not None:
                reason += f"；外部评分 {feature.rating:.1f}"
        work["score"] = round(score, 4)
        work["reason"] = reason
        work["shared_tags"] = tags
        work["algorithm_version"] = version
        work["profile_source"] = source
        results.append(work)
    return results


def similar_works(
    conn: sqlite3.Connection,
    work_id: int,
    limit: int = 10,
    *,
    algorithm: str | None = None,
    votes_db: Path | str | None = None,
) -> list[dict[str, Any]]:
    """Similar works, with CF neighbors blended in when votes are available."""
    index = FeatureIndex.build(conn)
    target = index.works.get(work_id)
    if not target:
        return []
    mode = _resolve_algorithm(algorithm)
    votes_path = _resolve_votes_db(conn, votes_db)
    votes_ready = votes_path is not None and has_votes(votes_path)
    use_hybrid = votes_ready and mode in {"auto", "hybrid"}
    version = HYBRID_ALGORITHM_VERSION if use_hybrid else ALGORITHM_VERSION
    work_similarity: dict[int, dict[int, float]] = {}
    if use_hybrid and votes_path is not None:
        work_similarity = cf.get_work_similarity(
            conn, votes_path, min_co_votes=CF_MIN_CO_VOTES, top_k=CF_TOP_K
        )

    scored: list[tuple[float, WorkFeature]] = []
    for feature in index.works.values():
        if feature.id == work_id:
            continue
        content = _cosine(target.vector, feature.vector)
        company = 1.0 if target.company_ids & feature.company_ids else 0.0
        year_sim = _year_similarity(feature, float(target.year) if target.year else None)
        length_sim = _length_similarity(feature, float(target.length_minutes) if target.length_minutes else None)
        quality = _quality(feature)
        score = 0.7 * content + 0.12 * company + 0.08 * year_sim + 0.05 * length_sim + 0.05 * quality
        cf_similarity = work_similarity.get(work_id, {}).get(feature.id, 0.0)
        score += SIMILAR_CF_WEIGHT * cf_similarity
        if score > 0.02:
            scored.append((score, feature))
    scored.sort(key=lambda item: item[0], reverse=True)
    results: list[dict[str, Any]] = []
    for score, feature in scored[:limit]:
        work = get_work(conn, feature.id)
        if not work:
            continue
        shared = sorted(target.tag_ids & feature.tag_ids, key=lambda tag_id: target.vector.get(tag_id, 0.0), reverse=True)
        tags = [index.tag_names[tag_id] for tag_id in shared[:3] if tag_id in index.tag_names]
        cf_similarity = work_similarity.get(work_id, {}).get(feature.id, 0.0)
        reason = (
            f"与《{target.title}》共享「{'」「'.join(tags)}」标签" if tags else "与该作品氛围相近"
        )
        if cf_similarity >= CF_REASON_THRESHOLD:
            reason += f"；投票口味相近的玩家也把它们一起投过票（相似度 {cf_similarity:.2f}）"
        work["score"] = round(score, 4)
        work["shared_tags"] = tags
        work["reason"] = reason
        work["algorithm_version"] = version
        results.append(work)
    return results
