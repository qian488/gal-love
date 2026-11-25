#!/usr/bin/env python
"""Generate recommendations from the local database."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.config import settings  # noqa: E402
from app.db import connect, init_db  # noqa: E402
from app.recommend.engine import recommend  # noqa: E402
from app.repository import upsert_entry  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--include-nsfw", action="store_true")
    parser.add_argument("--db", type=Path, default=settings.db_path)
    parser.add_argument(
        "--algorithm", choices=["content", "hybrid", "auto"], default="auto",
        help="recommendation algorithm (auto uses hybrid when votes are available)",
    )
    parser.add_argument("--votes-db", type=Path, default=None, help="override votes database path")
    parser.add_argument(
        "--rate",
        action="append",
        default=[],
        metavar="WORK_ID=RATING",
        help="set a personal rating before recommending, e.g. --rate 12=9",
    )
    args = parser.parse_args()

    init_db(args.db)
    conn = connect(args.db)
    try:
        for item in args.rate:
            work_id, rating = item.split("=", 1)
            upsert_entry(conn, int(work_id), {"status": "finished", "rating": float(rating)})
        items = recommend(
            conn,
            limit=args.limit,
            include_nsfw=args.include_nsfw,
            algorithm=args.algorithm,
            votes_db=args.votes_db,
        )
        print(json.dumps(items, ensure_ascii=False, indent=2))
    finally:
        conn.close()


if __name__ == "__main__":
    main()
