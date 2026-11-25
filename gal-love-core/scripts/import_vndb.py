#!/usr/bin/env python
"""Import popular visual novels from VNDB into the local database."""

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
from app.ingest.vndb import import_vndb  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=100, help="number of VNs to import")
    parser.add_argument("--min-votes", type=int, default=0, help="minimum VNDB vote count")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--incremental", dest="incremental", action="store_true", default=True,
        help="only import new/updated entries (default)",
    )
    mode.add_argument(
        "--full", dest="incremental", action="store_false",
        help="ignore cursors and re-import every fetched entry",
    )
    parser.add_argument("--db", type=Path, default=settings.db_path)
    args = parser.parse_args()

    init_db(args.db)
    conn = connect(args.db)
    try:
        result = import_vndb(
            conn,
            limit=args.limit,
            min_votes=args.min_votes,
            incremental=args.incremental,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
    finally:
        conn.close()


if __name__ == "__main__":
    main()
