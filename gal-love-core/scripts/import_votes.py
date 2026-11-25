#!/usr/bin/env python
"""Import a VNDB votes.txt dump into the independent votes database."""

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
from app.recommend.votes import import_votes_dump, votes_db_path  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dump", type=Path, required=True, help="path to VNDB votes.txt")
    parser.add_argument("--db", type=Path, default=settings.db_path, help="main database path")
    parser.add_argument("--votes-db", type=Path, default=None, help="override votes database path")
    parser.add_argument("--min-votes", type=int, default=10, help="minimum voters per work")
    parser.add_argument("--limit", type=int, default=None, help="maximum vote rows to import")
    args = parser.parse_args()

    target = args.votes_db if args.votes_db is not None else votes_db_path(args.db)
    try:
        result = import_votes_dump(
            args.dump, target, min_votes=args.min_votes, limit=args.limit
        )
    except FileNotFoundError as exc:
        parser.error(str(exc))
        return
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
