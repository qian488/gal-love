#!/usr/bin/env python
"""Offline evaluation of recommender algorithms using held-out personal ratings.

20% of rated ``my_entries`` are held out with a fixed random seed; the
recommender runs on a copy of the database with those entries removed. Metrics:
Recall@20, NDCG@20, tag diversity and catalog coverage.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import sqlite3
import sys
from pathlib import Path
from typing import Any, Iterable

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.config import settings  # noqa: E402
from app.db import connect, init_db  # noqa: E402
from app.recommend.engine import (  # noqa: E402
    ALGORITHM_VERSION,
    HYBRID_ALGORITHM_VERSION,
    _resolve_votes_db,
    recommend,
)
from app.recommend.votes import has_votes  # noqa: E402
from app.repository import get_settings  # noqa: E402

MIN_RATED_ENTRIES = 6
HOLDOUT_RATIO = 0.2
DEFAULT_SEED = 42
DEFAULT_K = 20


def rated_entries(conn: sqlite3.Connection) -> list[tuple[int, float]]:
    rows = conn.execute(
        "SELECT work_id, rating FROM my_entries WHERE rating IS NOT NULL ORDER BY work_id"
    ).fetchall()
    return [(int(row["work_id"]), float(row["rating"])) for row in rows]


def split_holdout(
    rated: Iterable[tuple[int, float]], *, seed: int = DEFAULT_SEED, ratio: float = HOLDOUT_RATIO
) -> tuple[list[tuple[int, float]], list[tuple[int, float]]]:
    """Split rated items into training and holdout sets (deterministic)."""
    items = list(rated)
    random.Random(seed).shuffle(items)
    count = max(1, round(len(items) * ratio)) if items else 0
    if not count:
        return items, []
    return items[:-count], items[-count:]


def recall_at_k(recommended: Iterable[int], holdout: Iterable[int], k: int = DEFAULT_K) -> float:
    relevant = {int(item) for item in holdout}
    if not relevant:
        return 0.0
    hits = {int(item) for item in list(recommended)[:k]} & relevant
    return len(hits) / len(relevant)


def ndcg_at_k(recommended: Iterable[int], holdout: Iterable[int], k: int = DEFAULT_K) -> float:
    relevant = {int(item) for item in holdout}
    if not relevant:
        return 0.0
    dcg = sum(
        1.0 / math.log2(position + 2)
        for position, item in enumerate(list(recommended)[:k])
        if int(item) in relevant
    )
    ideal = sum(1.0 / math.log2(position + 2) for position in range(min(len(relevant), k)))
    return dcg / ideal if ideal else 0.0


def tag_diversity(works: Iterable[dict[str, Any]]) -> float:
    """1 minus the average pairwise Jaccard overlap of recommended tags."""
    tag_sets = [
        {str(tag.get("name") or "") for tag in work.get("tags") or [] if tag.get("name")}
        for work in works
    ]
    tag_sets = [tags for tags in tag_sets if tags]
    if len(tag_sets) < 2:
        return 1.0 if tag_sets else 0.0
    total = 0.0
    pairs = 0
    for index, left in enumerate(tag_sets):
        for right in tag_sets[index + 1 :]:
            union = left | right
            total += len(left & right) / len(union) if union else 0.0
            pairs += 1
    return 1.0 - (total / pairs if pairs else 0.0)


def _eligible_catalog_size(conn: sqlite3.Connection, include_nsfw: bool) -> int:
    row = conn.execute(
        """
        SELECT COUNT(*) AS c FROM works w
        WHERE (? OR w.nsfw = 0)
          AND NOT EXISTS (SELECT 1 FROM my_entries e WHERE e.work_id = w.id)
          AND NOT EXISTS (
              SELECT 1 FROM feedback f WHERE f.work_id = w.id AND f.kind = 'not_interested'
          )
        """,
        (1 if include_nsfw else 0,),
    ).fetchone()
    return int(row["c"])


def evaluate(
    conn: sqlite3.Connection,
    *,
    algorithm: str | None = None,
    k: int = DEFAULT_K,
    seed: int = DEFAULT_SEED,
    votes_db: str | Path | None = None,
) -> dict[str, Any]:
    """Run the holdout evaluation and return a JSON-serializable summary."""
    mode = "auto" if algorithm is None else str(algorithm).strip().casefold()
    if mode not in {"auto", "content", "hybrid"}:
        raise ValueError(f"unknown algorithm: {algorithm!r} (expected content/hybrid/auto)")

    rated = rated_entries(conn)
    if len(rated) < MIN_RATED_ENTRIES:
        return {
            "evaluated": False,
            "message": (
                f"评分条目不足 {MIN_RATED_ENTRIES} 条（当前 {len(rated)} 条），跳过离线评估；"
                "请先为至少 6 部作品评分"
            ),
            "algorithm": mode,
            "seed": seed,
            "rated_entries": len(rated),
        }

    train, holdout = split_holdout(rated, seed=seed)
    holdout_ids = [work_id for work_id, _ in holdout]

    memory = sqlite3.connect(":memory:")
    memory.row_factory = sqlite3.Row
    try:
        conn.backup(memory)
        memory.execute("PRAGMA foreign_keys = ON")
        memory.executemany(
            "DELETE FROM my_entries WHERE work_id = ?", [(work_id,) for work_id in holdout_ids]
        )
        memory.commit()
        settings_map = get_settings(memory)
        include_nsfw = bool(settings_map.get("include_nsfw", False))
        items = recommend(
            memory, limit=k, algorithm=mode, votes_db=votes_db if votes_db is not None else _resolve_votes_db(conn)
        )
        recommended_ids = [int(item["id"]) for item in items]
        catalog_size = _eligible_catalog_size(memory, include_nsfw)
        version = items[0]["algorithm_version"] if items else (
            HYBRID_ALGORITHM_VERSION
            if mode != "content"
            and _resolve_votes_db(conn, votes_db) is not None
            and has_votes(_resolve_votes_db(conn, votes_db))
            else ALGORITHM_VERSION
        )
        summary: dict[str, Any] = {
            "evaluated": True,
            "algorithm": mode,
            "algorithm_version": version,
            "seed": seed,
            "k": k,
            "rated_entries": len(rated),
            "train_entries": len(train),
            "holdout_size": len(holdout_ids),
            "recommended_count": len(recommended_ids),
            "hits": sorted(
                {int(item) for item in recommended_ids[:k]} & set(holdout_ids)
            ),
            f"recall_at_{k}": round(recall_at_k(recommended_ids, holdout_ids, k), 4),
            f"ndcg_at_{k}": round(ndcg_at_k(recommended_ids, holdout_ids, k), 4),
            "tag_diversity": round(tag_diversity(items), 4),
            "catalog_coverage": round(len(set(recommended_ids)) / catalog_size, 4)
            if catalog_size
            else 0.0,
            "catalog_size": catalog_size,
        }
        return summary
    finally:
        memory.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=settings.db_path, help="main database path")
    parser.add_argument("--votes-db", type=Path, default=None, help="override votes database path")
    parser.add_argument(
        "--algorithm", choices=["content", "hybrid", "auto"], default="auto"
    )
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--limit", "--k", dest="k", type=int, default=DEFAULT_K)
    parser.add_argument("--output", type=Path, default=None, help="write JSON summary to a file")
    args = parser.parse_args()

    init_db(args.db)
    conn = connect(args.db)
    try:
        summary = evaluate(
            conn, algorithm=args.algorithm, k=args.k, seed=args.seed, votes_db=args.votes_db
        )
    finally:
        conn.close()
    text = json.dumps(summary, ensure_ascii=False, indent=2)
    print(text)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
