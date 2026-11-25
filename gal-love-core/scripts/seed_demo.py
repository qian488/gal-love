#!/usr/bin/env python
"""Insert a small, clearly-labeled demo catalog for offline UI development."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.config import settings  # noqa: E402
from app.db import connect, init_db  # noqa: E402
from app.repository import save_work_payload  # noqa: E402

WORKS = [
    {
        "title": "星海回响",
        "description": "科幻题材的视觉小说示例：在星际航行的舞台上，少年与失忆少女相遇。",
        "release_date": "2024-06-01",
        "rating": 8.7,
        "tags": [("科幻", 2.8), ("恋爱", 2.5), ("剧情", 2.4), ("太空", 2.0)],
        "companies": ["Demo Studio A"],
    },
    {
        "title": "樱花坂的夏天",
        "description": "校园恋爱示例：夏日、社团与青梅竹马的重逢。",
        "release_date": "2023-07-15",
        "rating": 8.2,
        "tags": [("校园", 2.9), ("恋爱", 2.6), ("日常", 2.2), ("青梅竹马", 1.8)],
        "companies": ["Demo Studio B"],
    },
    {
        "title": "雾都侦探事件簿",
        "description": "悬疑推理示例：雾气笼罩的城市里，侦探与助手追查连环失踪案。",
        "release_date": "2022-10-20",
        "rating": 8.9,
        "tags": [("悬疑", 2.9), ("推理", 2.7), ("剧情", 2.1), ("黑暗", 1.7)],
        "companies": ["Demo Studio C"],
    },
    {
        "title": "月下咖啡馆",
        "description": "治愈日常示例：一间只在夜晚营业的咖啡馆，收集客人们的烦恼。",
        "release_date": "2024-02-14",
        "rating": 8.0,
        "tags": [("治愈", 2.8), ("日常", 2.4), ("恋爱", 1.6), ("奇幻", 1.4)],
        "companies": ["Demo Studio B"],
    },
    {
        "title": "深红之诗",
        "description": "黑暗奇幻示例：被诅咒的王国与寻找真相的旅人。",
        "release_date": "2021-12-03",
        "rating": 8.4,
        "tags": [("奇幻", 2.8), ("黑暗", 2.5), ("剧情", 2.2), ("战斗", 1.5)],
        "companies": ["Demo Studio A"],
    },
    {
        "title": "夏日回声",
        "description": "青春群像示例：海边小镇的最后一个暑假。",
        "release_date": "2020-08-08",
        "rating": 7.9,
        "tags": [("校园", 2.5), ("青春", 2.4), ("日常", 2.0), ("治愈", 1.8)],
        "companies": ["Demo Studio D"],
    },
    {
        "title": "机械心跳",
        "description": "赛博朋克示例：仿生人少女与维修师之间的故事。",
        "release_date": "2023-03-18",
        "rating": 8.3,
        "tags": [("科幻", 2.7), ("赛博朋克", 2.4), ("恋爱", 1.9), ("剧情", 1.7)],
        "companies": ["Demo Studio C"],
    },
    {
        "title": "雪国来信",
        "description": "文学气质示例：一封迟到十年的信，把两个人带回雪国。",
        "release_date": "2019-01-11",
        "rating": 8.6,
        "tags": [("剧情", 2.8), ("恋爱", 2.2), ("治愈", 2.0), ("文学", 1.8)],
        "companies": ["Demo Studio A"],
    },
    {
        "title": "午夜列车",
        "description": "悬疑短篇示例：一列没有终点站的列车，乘客们各怀秘密。",
        "release_date": "2024-10-31",
        "rating": 7.8,
        "tags": [("悬疑", 2.6), ("短篇", 2.2), ("黑暗", 2.0), ("剧情", 1.5)],
        "companies": ["Demo Studio D"],
    },
    {
        "title": "魔法学院的新生",
        "description": "奇幻校园示例：不会魔法的少年进入了魔法学院。",
        "release_date": "2022-04-01",
        "rating": 7.6,
        "tags": [("奇幻", 2.5), ("校园", 2.3), ("恋爱", 1.8), ("喜剧", 1.6)],
        "companies": ["Demo Studio B"],
    },
]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=settings.db_path)
    args = parser.parse_args()

    init_db(args.db)
    conn = connect(args.db)
    try:
        for index, work in enumerate(WORKS, start=1):
            payload = {
                "source": "manual",
                "title": work["title"],
                "description": work["description"],
                "release_date": work["release_date"],
                "manual_rating": work["rating"],
                "tags": [
                    {"name": name, "weight": weight, "source": "manual"}
                    for name, weight in work["tags"]
                ],
                "companies": [
                    {"name": company, "role": "developer"} for company in work["companies"]
                ],
                "raw": {"demo": True, "index": index},
            }
            save_work_payload(conn, payload)
        print(f"Seeded {len(WORKS)} demo works into {args.db}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
