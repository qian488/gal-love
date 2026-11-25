from __future__ import annotations

import sqlite3
from typing import Any

from app.repository import save_work_payload


def add_work(
    conn: sqlite3.Connection,
    *,
    title: str,
    tags: list[str] | None = None,
    rating: float | None = 8.0,
    year: int = 2020,
    companies: list[str] | None = None,
    nsfw: bool = False,
    source: str = "manual",
    external_id: str | None = None,
) -> int:
    payload: dict[str, Any] = {
        "source": source,
        "external_id": external_id,
        "title": title,
        "description": f"{title} description",
        "release_date": f"{year}-01-01",
        "manual_rating": rating if source == "manual" else None,
        "vndb_rating": rating * 10 if source == "vndb" and rating is not None else None,
        "vndb_votecount": 100 if source == "vndb" else None,
        "bangumi_rating": rating if source == "bangumi" else None,
        "bangumi_votecount": 100 if source == "bangumi" else None,
        "nsfw": nsfw,
        "tags": [
            {"name": tag, "weight": 2.0, "spoiler": 0, "category": "cont"} for tag in tags or []
        ],
        "companies": [
            {"name": company, "role": "developer"} for company in companies or []
        ],
        "titles": [],
    }
    return save_work_payload(conn, payload)
