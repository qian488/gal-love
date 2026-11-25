"""Sparse item-item collaborative filtering over VNDB votes.

Similarity uses adjusted cosine: each user's vote is centered on that user's
mean before accumulating dot products. Only the strongest ``top_k`` neighbors
per work are kept, so memory stays proportional to the number of voted works
rather than to the square of the catalog.
"""

from __future__ import annotations

import heapq
import math
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

MIN_CO_VOTES = 2
TOP_K = 30
SHRINKAGE = 5.0
MAX_ITEMS_PER_USER = 300
CF_SATURATION = 1.0

# One-entry cache keyed by the votes database mtime, so repeated recommend()
# calls do not rebuild the model from scratch.
_SIM_CACHE: dict[str, Any] = {}


@dataclass
class _Pair:
    dot: float = 0.0
    norm_self: float = 0.0
    norm_other: float = 0.0
    co: int = 0


def _similarity(pair: _Pair, min_co_votes: int) -> float:
    if pair.co < min_co_votes:
        return 0.0
    denominator = math.sqrt(pair.norm_self * pair.norm_other)
    if denominator <= 1e-9:
        return 0.0
    raw = pair.dot / denominator
    shrink = pair.co / (pair.co + SHRINKAGE)
    return max(0.0, min(1.0, raw * shrink))


def load_votes(votes_db: Path | str) -> dict[int, dict[int, float]]:
    """Read ``votes`` as ``{user_id: {vndb_id: normalized_score}}``."""
    path = Path(votes_db).expanduser()
    if not path.is_file():
        return {}
    connection = sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        result: dict[int, dict[int, float]] = {}
        for row in connection.execute("SELECT user_id, vndb_id, score FROM votes"):
            result.setdefault(int(row["user_id"]), {})[int(row["vndb_id"])] = float(row["score"])
        return result
    except sqlite3.Error:
        return {}
    finally:
        connection.close()


def _prune(
    adjacency: dict[int, dict[int, _Pair]],
    item: int,
    capacity: int,
    min_co_votes: int,
) -> None:
    row = adjacency.get(item)
    if not row or len(row) <= capacity:
        return
    ranked = heapq.nlargest(
        capacity,
        ((_similarity(pair, min_co_votes), other) for other, pair in row.items()),
    )
    keep = {other for _, other in ranked}
    for other in list(row):
        if other in keep:
            continue
        del row[other]
        reverse = adjacency.get(other)
        if reverse is not None:
            reverse.pop(item, None)


def build_item_similarity(
    votes: dict[int, dict[int, float]],
    *,
    min_co_votes: int = MIN_CO_VOTES,
    top_k: int = TOP_K,
) -> dict[int, dict[int, float]]:
    """Build ``{vndb_id: {neighbor_vndb_id: similarity}}`` from user votes."""
    if top_k <= 0:
        return {}
    threshold = max(1, int(min_co_votes))
    capacity = max(top_k * 2, top_k + 10)
    adjacency: dict[int, dict[int, _Pair]] = {}

    for user_scores in votes.values():
        items = sorted(user_scores.items(), key=lambda item: (-item[1], item[0]))[:MAX_ITEMS_PER_USER]
        if len(items) < threshold + 1:
            continue
        mean = sum(score for _, score in items) / len(items)
        centered = [(item_id, score - mean) for item_id, score in items]
        touched: set[int] = set()
        for index, (item_id, centered_score) in enumerate(centered):
            if centered_score == 0.0:
                continue
            row = adjacency.setdefault(item_id, {})
            touched.add(item_id)
            for other_id, other_score in centered[index + 1 :]:
                if other_score == 0.0:
                    continue
                forward = row.get(other_id)
                if forward is None:
                    forward = _Pair()
                    row[other_id] = forward
                backward = adjacency.setdefault(other_id, {}).get(item_id)
                if backward is None:
                    backward = _Pair()
                    adjacency[other_id][item_id] = backward
                forward.dot += centered_score * other_score
                forward.norm_self += centered_score * centered_score
                forward.norm_other += other_score * other_score
                forward.co += 1
                backward.dot += other_score * centered_score
                backward.norm_self += other_score * other_score
                backward.norm_other += centered_score * centered_score
                backward.co += 1
        for item_id in touched:
            _prune(adjacency, item_id, capacity, threshold)

    result: dict[int, dict[int, float]] = {}
    for item_id, row in adjacency.items():
        ranked = sorted(
            (
                (score, other_id)
                for other_id, pair in row.items()
                if (score := _similarity(pair, threshold)) > 0.0
            ),
            key=lambda entry: (-entry[0], entry[1]),
        )
        if ranked:
            result[item_id] = {other_id: score for score, other_id in ranked[:top_k]}
    return result


def vndb_work_map(conn: sqlite3.Connection) -> dict[int, int]:
    """Map VNDB ids to local work ids via ``external_refs(source='vndb')``."""
    mapping: dict[int, int] = {}
    rows = conn.execute(
        "SELECT work_id, external_id FROM external_refs WHERE LOWER(source) = 'vndb'"
    ).fetchall()
    for row in rows:
        try:
            vndb_id = int(str(row["external_id"]).strip())
        except (TypeError, ValueError):
            continue
        work_id = int(row["work_id"])
        if vndb_id not in mapping or work_id < mapping[vndb_id]:
            mapping[vndb_id] = work_id
    return mapping


def work_vndb_map(conn: sqlite3.Connection) -> dict[int, list[int]]:
    """Reverse mapping of :func:`vndb_work_map`, used to find CF seeds."""
    result: dict[int, list[int]] = {}
    for vndb_id, work_id in vndb_work_map(conn).items():
        result.setdefault(work_id, []).append(vndb_id)
    return result


def _to_work_similarity(
    item_similarity: dict[int, dict[int, float]],
    mapping: dict[int, int],
    top_k: int,
) -> dict[int, dict[int, float]]:
    result: dict[int, dict[int, float]] = {}
    for vndb_id, neighbors in item_similarity.items():
        work_id = mapping.get(vndb_id)
        if work_id is None:
            continue
        bucket = result.setdefault(work_id, {})
        for neighbor_id, score in neighbors.items():
            neighbor_work = mapping.get(neighbor_id)
            if neighbor_work is None or neighbor_work == work_id:
                continue
            bucket[neighbor_work] = max(bucket.get(neighbor_work, 0.0), score)
    for work_id, bucket in result.items():
        ranked = sorted(bucket.items(), key=lambda entry: (-entry[1], entry[0]))[:top_k]
        result[work_id] = dict(ranked)
    return result


def get_work_similarity(
    conn: sqlite3.Connection,
    votes_db: Path | str,
    *,
    min_co_votes: int = MIN_CO_VOTES,
    top_k: int = TOP_K,
) -> dict[int, dict[int, float]]:
    """Return work-level CF neighbors, rebuilding only when votes change."""
    path = Path(votes_db).expanduser()
    if not path.is_file():
        return {}
    key = (str(path.resolve()), path.stat().st_mtime_ns, int(min_co_votes), int(top_k))
    cached = _SIM_CACHE.get("key")
    if cached == key:
        return _SIM_CACHE["value"]
    item_similarity = build_item_similarity(
        load_votes(path), min_co_votes=min_co_votes, top_k=top_k
    )
    value = _to_work_similarity(item_similarity, vndb_work_map(conn), top_k)
    _SIM_CACHE.clear()
    _SIM_CACHE["key"] = key
    _SIM_CACHE["value"] = value
    return value


def candidate_cf_score(
    candidate_work_id: int,
    seed_weights: dict[int, float],
    work_similarity: dict[int, dict[int, float]],
) -> tuple[float, int | None, int]:
    """Score a candidate from the user's liked works.

    Returns ``(score, best_seed_work_id, matching_seed_count)``.
    """
    total = 0.0
    best_seed: int | None = None
    best_contribution = 0.0
    matches = 0
    for seed_id, weight in seed_weights.items():
        similarity = work_similarity.get(seed_id, {}).get(candidate_work_id, 0.0)
        if similarity <= 0.0:
            continue
        contribution = similarity * max(0.0, min(2.0, float(weight)))
        if contribution <= 0.0:
            continue
        total += contribution
        matches += 1
        if contribution > best_contribution:
            best_contribution = contribution
            best_seed = seed_id
    score = total / (total + CF_SATURATION) if total > 0 else 0.0
    return score, best_seed, matches
