"""Scheduled incremental sync for VNDB and Bangumi.

CLI::

    python -m app.scheduler --once
    python -m app.scheduler --interval-hours 24
    python -m app.scheduler --interval-hours 24 --sources vndb,bangumi
"""

from __future__ import annotations

import argparse
import json
import logging
import signal
import sys
import time
from pathlib import Path
from typing import Any

from .config import settings
from .db import db_session, init_db
from .ingest.bangumi import import_bangumi
from .ingest.vndb import import_vndb
from .normalize import now_iso

logger = logging.getLogger("gal_love.scheduler")

DEFAULT_LIMIT = 100
DEFAULT_SOURCES = ("vndb", "bangumi")
_stop_requested = False


def _handle_sigint(signum: int, frame: Any) -> None:
    global _stop_requested
    _stop_requested = True
    logger.info("收到 SIGINT，将在当前同步结束后停止")


def run_once(db_path: str | Path, sources: list[str] | None = None) -> dict[str, Any]:
    """Run one incremental sync round and return per-source results.

    Each source is imported through ``import_vndb`` / ``import_bangumi`` which
    write their own ``sync_runs`` rows.  Exceptions are captured per source so
    one failing source never aborts the others or the caller.
    """
    db_path = Path(db_path)
    init_db(db_path)
    selected = list(sources) if sources is not None else list(DEFAULT_SOURCES)
    result: dict[str, Any] = {
        "started_at": now_iso(),
        "sources": {},
    }
    for source in selected:
        try:
            with db_session(db_path) as conn:
                if source == "vndb":
                    outcome = import_vndb(conn, limit=DEFAULT_LIMIT, incremental=True)
                elif source == "bangumi":
                    outcome = import_bangumi(conn, limit=DEFAULT_LIMIT, incremental=True)
                else:
                    raise ValueError(f"unknown sync source: {source}")
            result["sources"][source] = outcome
            logger.info("同步完成: %s -> %s", source, outcome)
        except Exception as exc:  # noqa: BLE001 - keep the scheduler alive
            logger.exception("同步失败: %s", source)
            result["sources"][source] = {"status": "error", "error": str(exc)}
    result["finished_at"] = now_iso()
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run scheduled incremental imports")
    parser.add_argument("--once", action="store_true", help="run a single sync round and exit")
    parser.add_argument(
        "--interval-hours",
        type=float,
        default=24.0,
        help="hours between sync rounds (default: 24)",
    )
    parser.add_argument("--db", type=Path, default=settings.db_path)
    parser.add_argument(
        "--sources",
        help="comma separated sources, e.g. vndb,bangumi (default: both)",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    signal.signal(signal.SIGINT, _handle_sigint)

    sources: list[str] | None = None
    if args.sources:
        sources = [item.strip() for item in args.sources.split(",") if item.strip()]

    if args.once:
        result = run_once(args.db, sources)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    interval = max(0.01, args.interval_hours) * 3600
    logger.info("调度器启动，间隔 %.2f 小时，数据源 %s", args.interval_hours, sources or DEFAULT_SOURCES)
    while not _stop_requested:
        try:
            result = run_once(args.db, sources)
            logger.info("本轮同步结果: %s", result)
        except Exception:  # noqa: BLE001 - defensive: run_once already catches per-source errors
            logger.exception("本轮同步整体失败，将在下轮重试")
        if _stop_requested:
            break
        deadline = time.monotonic() + interval
        while not _stop_requested and time.monotonic() < deadline:
            time.sleep(min(1.0, deadline - time.monotonic()))
    logger.info("调度器已停止")
    return 0


if __name__ == "__main__":
    sys.exit(main())
