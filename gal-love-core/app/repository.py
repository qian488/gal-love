"""Persistence helpers for the personal Gal Love database."""

from __future__ import annotations

import sqlite3
import uuid
from collections import defaultdict
from typing import Any, Iterable

from .normalize import json_dumps, json_loads, normalize_text, now_iso, parse_year, unique_preserving_order
from .tag_zh import canonical_lookup, canonical_lookup_keys

ENTRY_STATUSES = {"want", "playing", "finished", "dropped"}
FEEDBACK_KINDS = {"not_interested", "like", "dislike", "seen"}


def _work_row(row: sqlite3.Row) -> dict[str, Any]:
    item = dict(row)
    item["platforms"] = json_loads(item.get("platforms"), [])
    item["languages"] = json_loads(item.get("languages"), [])
    item["nsfw"] = bool(item.get("nsfw"))
    item.pop("normalized_title", None)
    return item


def _attach_tags(conn: sqlite3.Connection, works: list[dict[str, Any]], limit: int = 12) -> None:
    if not works:
        return
    ids = [work["id"] for work in works]
    placeholders = ",".join("?" for _ in ids)
    rows = conn.execute(
        f"""
        SELECT wt.work_id, t.name, t.category, wt.weight, wt.spoiler, wt.source
        FROM work_tags wt
        JOIN tags t ON t.id = wt.tag_id
        WHERE wt.work_id IN ({placeholders})
        ORDER BY wt.weight DESC, t.name ASC
        """,
        ids,
    ).fetchall()
    grouped: dict[int, list[dict[str, Any]]] = {work_id: [] for work_id in ids}
    for row in rows:
        bucket = grouped[row["work_id"]]
        if len(bucket) >= limit:
            continue
        bucket.append(
            {
                "name": row["name"],
                "category": row["category"],
                "weight": row["weight"],
                "spoiler": row["spoiler"],
                "source": row["source"],
            }
        )
    for work in works:
        work["tags"] = grouped.get(work["id"], [])


def _attach_companies(conn: sqlite3.Connection, works: list[dict[str, Any]]) -> None:
    if not works:
        return
    ids = [work["id"] for work in works]
    placeholders = ",".join("?" for _ in ids)
    rows = conn.execute(
        f"""
        SELECT wc.work_id, c.name, wc.role
        FROM work_companies wc
        JOIN companies c ON c.id = wc.company_id
        WHERE wc.work_id IN ({placeholders})
        ORDER BY CASE wc.role WHEN 'developer' THEN 0 ELSE 1 END, c.name ASC
        """,
        ids,
    ).fetchall()
    grouped: dict[int, list[str]] = {work_id: [] for work_id in ids}
    for row in rows:
        if row["name"] not in grouped[row["work_id"]]:
            grouped[row["work_id"]].append(row["name"])
    for work in works:
        work["companies"] = grouped.get(work["id"], [])


def _recompute_display_rating(conn: sqlite3.Connection, work_id: int) -> None:
    row = conn.execute(
        "SELECT vndb_rating, vndb_votecount, bangumi_rating, bangumi_votecount FROM works WHERE id = ?",
        (work_id,),
    ).fetchone()
    if not row:
        return
    if row["vndb_rating"] is not None:
        rating = round(float(row["vndb_rating"]) / 10.0, 2)
        count = row["vndb_votecount"] or 0
    elif row["bangumi_rating"] is not None:
        rating = round(float(row["bangumi_rating"]), 2)
        count = row["bangumi_votecount"] or 0
    else:
        return
    conn.execute(
        "UPDATE works SET rating = ?, rating_count = ? WHERE id = ?",
        (rating, count, work_id),
    )


def find_work_by_external_ref(
    conn: sqlite3.Connection, source: str, external_id: str
) -> int | None:
    row = conn.execute(
        "SELECT work_id FROM external_refs WHERE source = ? AND external_id = ?",
        (source, external_id),
    ).fetchone()
    return int(row["work_id"]) if row else None


def find_work_by_titles(conn: sqlite3.Connection, titles: Iterable[str]) -> int | None:
    norms = {normalize_text(title) for title in titles if normalize_text(title)}
    if not norms:
        return None
    placeholders = ",".join("?" for _ in norms)
    rows = conn.execute(
        f"""
        SELECT work_id, COUNT(*) AS matches
        FROM titles
        WHERE normalized_title IN ({placeholders})
        GROUP BY work_id
        ORDER BY matches DESC
        """,
        list(norms),
    ).fetchall()
    if rows:
        if len(rows) == 1 or rows[0]["matches"] > rows[1]["matches"]:
            return int(rows[0]["work_id"])
        return None
    rows = conn.execute(
        f"SELECT id FROM works WHERE normalized_title IN ({placeholders}) LIMIT 2",
        list(norms),
    ).fetchall()
    if len(rows) == 1:
        return int(rows[0]["id"])
    return None


def _get_or_create_tag(
    conn: sqlite3.Connection, name: str, category: str | None, source: str
) -> int | None:
    """Return a tag id, collapsing built-in aliases and Chinese names together."""
    raw = str(name or "").strip()
    normalized = normalize_text(raw)
    if not normalized:
        return None

    info = canonical_lookup(raw)
    if info:
        canonical, name_zh, aliases = info
        tag_norm = normalize_text(canonical)
    else:
        name_zh, aliases, tag_norm = None, [], normalized

    # 1) An explicitly registered alias always wins.
    row = conn.execute(
        "SELECT tag_id FROM tag_aliases WHERE alias_normalized = ?", (normalized,)
    ).fetchone()
    tag_id = int(row["tag_id"]) if row else None

    # 2) Otherwise resolve through the canonical normalized name.
    existing = None
    if tag_id is None:
        existing = conn.execute(
            "SELECT id, name_zh, aliases FROM tags WHERE normalized_name = ?", (tag_norm,)
        ).fetchone()
        if existing is not None:
            tag_id = int(existing["id"])

    if tag_id is None:
        cur = conn.execute(
            """
            INSERT INTO tags(name, normalized_name, category, source, name_zh, aliases)
            VALUES(?, ?, ?, ?, ?, ?)
            """,
            (raw, tag_norm, category, source, name_zh, json_dumps(aliases) if aliases else None),
        )
        tag_id = int(cur.lastrowid)
    else:
        if existing is None:
            existing = conn.execute(
                "SELECT name_zh, aliases FROM tags WHERE id = ?", (tag_id,)
            ).fetchone()
        current_aliases = json_loads(existing["aliases"], []) if existing else []
        merged = unique_preserving_order(
            [*(current_aliases or []), *(aliases or []), name_zh or ""]
        )
        conn.execute(
            "UPDATE tags SET name_zh = COALESCE(name_zh, ?), aliases = ? WHERE id = ?",
            (name_zh, json_dumps(merged) if merged else None, tag_id),
        )

    # Register this spelling (and the built-in Chinese name) as searchable aliases.
    zh_norm = normalize_text(name_zh) if name_zh else ""
    alias_rows = [(normalized, "", source)]
    if zh_norm:
        alias_rows.append((zh_norm, "zh", "builtin"))
    for alias_norm, lang, alias_source in alias_rows:
        if not alias_norm or alias_norm == tag_norm:
            continue
        conn.execute(
            """
            INSERT OR IGNORE INTO tag_aliases(alias_normalized, tag_id, lang, source)
            VALUES(?, ?, ?, ?)
            """,
            (alias_norm, tag_id, lang, alias_source),
        )
    return tag_id


def _resolve_tag_ids(conn: sqlite3.Connection, name: str) -> list[int]:
    """Find tag ids matching a name, canonical translation or registered alias."""
    raw = str(name or "").strip()
    norm = normalize_text(raw)
    if not norm:
        return []
    candidates = canonical_lookup_keys(raw) or {norm}
    candidates.add(norm)
    values = [value for value in candidates if value]
    if not values:
        return []
    placeholders = ",".join("?" for _ in values)
    rows = conn.execute(
        f"""
        SELECT DISTINCT t.id FROM tags t
        LEFT JOIN tag_aliases ta ON ta.tag_id = t.id
        WHERE t.normalized_name IN ({placeholders})
           OR ta.alias_normalized IN ({placeholders})
           OR t.name_zh LIKE ?
        """,
        [*values, *values, f"%{raw}%"],
    ).fetchall()
    return [int(row["id"]) for row in rows]


def _get_or_create_company(conn: sqlite3.Connection, name: str) -> int | None:
    normalized = normalize_text(name)
    if not normalized:
        return None
    conn.execute(
        """
        INSERT INTO companies(name, normalized_name) VALUES(?, ?)
        ON CONFLICT(normalized_name) DO UPDATE SET name = companies.name
        """,
        (name.strip(), normalized),
    )
    row = conn.execute("SELECT id FROM companies WHERE normalized_name = ?", (normalized,)).fetchone()
    return int(row["id"]) if row else None


def _title_records(payload: dict[str, Any]) -> list[dict[str, Any]]:
    source = payload["source"]
    records: list[dict[str, Any]] = []

    def add(title: str | None, lang: str = "", latin: str | None = None, main: bool = False) -> None:
        if not title or not str(title).strip():
            return
        title = str(title).strip()
        records.append(
            {
                "title": title,
                "normalized_title": normalize_text(title),
                "lang": lang or "",
                "latin": latin,
                "official": 1 if main or lang else 0,
                "is_main": 1 if main else 0,
                "source": source,
            }
        )

    for item in payload.get("titles") or []:
        add(item.get("title"), item.get("lang") or "", item.get("latin"), bool(item.get("main")))
    add(payload.get("title"), "zh" if payload.get("title_zh") else "", None, True)
    add(payload.get("title_zh"), "zh", None, False)
    add(payload.get("original_title"), "ja", None, False)
    add(payload.get("romanized_title"), "en", None, False)
    for alias in payload.get("aliases") or []:
        add(alias, "", None, False)

    seen: set[tuple[str, str]] = set()
    result: list[dict[str, Any]] = []
    for record in records:
        key = (record["lang"], record["normalized_title"])
        if not record["normalized_title"] or key in seen:
            continue
        seen.add(key)
        result.append(record)
    return result


def save_work_payload(conn: sqlite3.Connection, payload: dict[str, Any]) -> int:
    """Insert or merge a normalized work payload.

    Payloads are produced by the VNDB/Bangumi importers or by manual entry.
    Manual data is never overwritten by an external source.
    """
    source = payload.get("source") or "manual"
    external_id = payload.get("external_id")
    timestamp = now_iso()
    title = str(payload.get("title") or "").strip() or "Untitled"
    title_zh = (payload.get("title_zh") or "").strip() or None
    titles_for_match = [
        title,
        title_zh or "",
        payload.get("original_title") or "",
        payload.get("romanized_title") or "",
        *[item.get("title", "") for item in payload.get("titles") or []],
        *(payload.get("aliases") or []),
    ]

    work_id = find_work_by_external_ref(conn, source, external_id) if external_id else None
    if work_id is None:
        work_id = find_work_by_titles(conn, titles_for_match)

    existing = None
    if work_id is not None:
        existing = conn.execute("SELECT * FROM works WHERE id = ?", (work_id,)).fetchone()
        if existing is None:
            work_id = None

    release_date = payload.get("release_date")
    release_year = payload.get("release_year") or parse_year(release_date)
    platforms = unique_preserving_order(payload.get("platforms") or [])
    languages = unique_preserving_order(payload.get("languages") or [])

    if work_id is None:
        cur = conn.execute(
            """
            INSERT INTO works(
                title, normalized_title, original_title, romanized_title, description,
                cover_url, release_date, release_year, length_minutes, length_label,
                platforms, languages, vndb_rating, vndb_votecount, bangumi_rating,
                bangumi_votecount, rating, rating_count, nsfw, source, created_at, updated_at
            ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                title_zh or title,
                normalize_text(title_zh or title),
                payload.get("original_title"),
                payload.get("romanized_title"),
                payload.get("description"),
                payload.get("cover_url"),
                release_date,
                release_year,
                payload.get("length_minutes"),
                payload.get("length_label"),
                json_dumps(platforms),
                json_dumps(languages),
                payload.get("vndb_rating"),
                payload.get("vndb_votecount"),
                payload.get("bangumi_rating"),
                payload.get("bangumi_votecount"),
                payload.get("manual_rating") or payload.get("rating"),
                0,
                1 if payload.get("nsfw") else 0,
                source,
                timestamp,
                timestamp,
            ),
        )
        work_id = int(cur.lastrowid)
    else:
        row = existing
        manual_existing = row["source"] == "manual"
        same_source = row["source"] == source
        overwrite = (not manual_existing) and (same_source or source == "manual")

        updates: dict[str, Any] = {}
        if not manual_existing:
            # Prefer a Chinese display title when Bangumi supplies one.
            if title_zh and (same_source or not any("\u4e00" <= c <= "\u9fff" for c in row["title"])):
                updates["title"] = title_zh
                updates["normalized_title"] = normalize_text(title_zh)
            elif overwrite and title and not row["title"]:
                updates["title"] = title
                updates["normalized_title"] = normalize_text(title)

        for field in ("original_title", "romanized_title", "description", "cover_url"):
            if payload.get(field) and (overwrite or not row[field]):
                updates[field] = payload[field]
        if release_date and (overwrite or not row["release_date"]):
            updates["release_date"] = release_date
            updates["release_year"] = release_year
        if payload.get("length_minutes") and (overwrite or not row["length_minutes"]):
            updates["length_minutes"] = payload["length_minutes"]
        if payload.get("length_label") and (overwrite or not row["length_label"]):
            updates["length_label"] = payload["length_label"]
        if platforms:
            updates["platforms"] = json_dumps(unique_preserving_order(json_loads(row["platforms"], []) + platforms))
        if languages:
            updates["languages"] = json_dumps(unique_preserving_order(json_loads(row["languages"], []) + languages))
        if payload.get("nsfw"):
            updates["nsfw"] = 1
        if payload.get("vndb_rating") is not None:
            updates["vndb_rating"] = payload["vndb_rating"]
            updates["vndb_votecount"] = payload.get("vndb_votecount")
        if payload.get("bangumi_rating") is not None:
            updates["bangumi_rating"] = payload["bangumi_rating"]
            updates["bangumi_votecount"] = payload.get("bangumi_votecount")
        if source == "manual" and payload.get("manual_rating") is not None:
            updates["rating"] = payload["manual_rating"]
            updates["rating_count"] = 0
        if updates:
            updates["updated_at"] = timestamp
            assignments = ", ".join(f"{key} = ?" for key in updates)
            conn.execute(
                f"UPDATE works SET {assignments} WHERE id = ?",
                [*updates.values(), work_id],
            )

    # External reference
    if external_id:
        conn.execute(
            """
            INSERT INTO external_refs(work_id, source, external_id, url, raw_json, fetched_at)
            VALUES(?, ?, ?, ?, ?, ?)
            ON CONFLICT(source, external_id) DO UPDATE SET
                work_id = excluded.work_id,
                url = excluded.url,
                raw_json = excluded.raw_json,
                fetched_at = excluded.fetched_at
            """,
            (
                work_id,
                source,
                external_id,
                payload.get("url"),
                json_dumps(payload.get("raw")) if payload.get("raw") is not None else None,
                timestamp,
            ),
        )

    # Titles
    conn.execute("DELETE FROM titles WHERE work_id = ? AND source = ?", (work_id, source))
    for record in _title_records(payload):
        conn.execute(
            """
            INSERT OR IGNORE INTO titles(
                work_id, lang, title, normalized_title, latin, official, is_main, source
            ) VALUES(?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                work_id,
                record["lang"],
                record["title"],
                record["normalized_title"],
                record["latin"],
                record["official"],
                record["is_main"],
                record["source"],
            ),
        )

    # Tags
    conn.execute("DELETE FROM work_tags WHERE work_id = ? AND source = ?", (work_id, source))
    for tag in payload.get("tags") or []:
        tag_id = _get_or_create_tag(conn, tag.get("name", ""), tag.get("category"), source)
        if tag_id is None:
            continue
        weight = float(tag.get("weight") or 1.0)
        conn.execute(
            """
            INSERT INTO work_tags(work_id, tag_id, weight, spoiler, source)
            VALUES(?, ?, ?, ?, ?)
            ON CONFLICT(work_id, tag_id, source) DO UPDATE SET
                weight = excluded.weight,
                spoiler = excluded.spoiler
            """,
            (work_id, tag_id, max(0.1, weight), int(tag.get("spoiler") or 0), source),
        )

    # Companies
    conn.execute("DELETE FROM work_companies WHERE work_id = ? AND source = ?", (work_id, source))
    for company in payload.get("companies") or []:
        company_id = _get_or_create_company(conn, company.get("name", ""))
        if company_id is None:
            continue
        conn.execute(
            """
            INSERT OR IGNORE INTO work_companies(work_id, company_id, role, source)
            VALUES(?, ?, ?, ?)
            """,
            (work_id, company_id, company.get("role") or "developer", source),
        )

    _recompute_display_rating(conn, work_id)
    conn.commit()
    return work_id


def create_manual_work(conn: sqlite3.Connection, data: dict[str, Any]) -> int:
    tags = [{"name": tag, "weight": 1.0, "source": "manual"} for tag in data.get("tags") or []]
    companies = [
        {"name": company, "role": "developer"} for company in data.get("companies") or []
    ]
    payload = {
        "source": "manual",
        "title": data["title"],
        "title_zh": data.get("title_zh"),
        "original_title": data.get("original_title"),
        "description": data.get("description"),
        "cover_url": data.get("cover_url"),
        "release_date": data.get("release_date"),
        "length_minutes": data.get("length_minutes"),
        "length_label": data.get("length_label"),
        "platforms": data.get("platforms") or [],
        "languages": data.get("languages") or [],
        "manual_rating": data.get("rating"),
        "nsfw": data.get("nsfw", False),
        "tags": tags,
        "companies": companies,
        "titles": data.get("titles") or [],
    }
    return save_work_payload(conn, payload)


def get_work(conn: sqlite3.Connection, work_id: int) -> dict[str, Any] | None:
    row = conn.execute("SELECT * FROM works WHERE id = ?", (work_id,)).fetchone()
    if not row:
        return None
    work = _work_row(row)
    _attach_tags(conn, [work], limit=50)
    _attach_companies(conn, [work])
    work["titles"] = [
        dict(title)
        for title in conn.execute(
            "SELECT lang, title, latin, official, is_main, source FROM titles WHERE work_id = ? ORDER BY is_main DESC, lang",
            (work_id,),
        ).fetchall()
    ]
    work["external_refs"] = [
        {
            "source": ref["source"],
            "external_id": ref["external_id"],
            "url": ref["url"],
            "fetched_at": ref["fetched_at"],
        }
        for ref in conn.execute(
            "SELECT source, external_id, url, fetched_at FROM external_refs WHERE work_id = ?",
            (work_id,),
        ).fetchall()
    ]
    entry = conn.execute("SELECT * FROM my_entries WHERE work_id = ?", (work_id,)).fetchone()
    work["entry"] = dict(entry) if entry else None
    if work["entry"]:
        work["entry"]["favorite"] = bool(work["entry"]["favorite"])
    return work


def find_duplicate_candidates(
    conn: sqlite3.Connection, *, min_score: float = 0.75, limit: int = 50
) -> list[dict[str, Any]]:
    """Return likely duplicate pairs with a score and human-readable reasons.

    Signals: identical external refs, identical normalized titles or heavy
    title/alias overlap.  Same company plus release year is only a weak
    corroborating signal and never qualifies a pair on its own.  Works already
    used as a merge source are excluded.
    """
    merged_sources = {
        int(row["source_id"])
        for row in conn.execute("SELECT source_id FROM merge_log").fetchall()
    }
    works = [
        row
        for row in conn.execute("SELECT id, normalized_title, release_year FROM works").fetchall()
        if int(row["id"]) not in merged_sources
    ]
    if len(works) < 2:
        return []

    titles: dict[int, set[str]] = defaultdict(set)
    for row in conn.execute("SELECT work_id, normalized_title FROM titles").fetchall():
        if row["normalized_title"]:
            titles[int(row["work_id"])].add(row["normalized_title"])
    for row in works:
        if row["normalized_title"]:
            titles[int(row["id"])].add(row["normalized_title"])

    refs: dict[int, set[tuple[str, str]]] = defaultdict(set)
    for row in conn.execute("SELECT work_id, source, external_id FROM external_refs").fetchall():
        refs[int(row["work_id"])].add((row["source"], row["external_id"]))

    companies: dict[int, set[str]] = defaultdict(set)
    for row in conn.execute(
        "SELECT wc.work_id, c.normalized_name FROM work_companies wc "
        "JOIN companies c ON c.id = wc.company_id"
    ).fetchall():
        companies[int(row["work_id"])].add(row["normalized_name"])

    candidates: list[dict[str, Any]] = []
    for index, left in enumerate(works):
        left_id = int(left["id"])
        left_titles = titles[left_id]
        for right in works[index + 1 :]:
            right_id = int(right["id"])
            signals: list[tuple[float, str]] = []

            shared_refs = refs[left_id] & refs[right_id]
            if shared_refs:
                sample = sorted(shared_refs)[0]
                signals.append((1.0, f"外部引用相同: {sample[0]}:{sample[1]}"))

            if left["normalized_title"] and left["normalized_title"] == right["normalized_title"]:
                signals.append((0.98, "规范化标题完全相同"))

            right_titles = titles[right_id]
            if left_titles and right_titles:
                shared = left_titles & right_titles
                if shared:
                    ratio = len(shared) / min(len(left_titles), len(right_titles))
                    if ratio >= 0.5:
                        signals.append(
                            (0.75 + 0.2 * min(ratio, 1.0), f"标题/别名高度重叠: {len(shared)} 项")
                        )

            year = left["release_year"]
            if (
                year is not None
                and year == right["release_year"]
                and (companies[left_id] & companies[right_id])
            ):
                # 同公司同年只能作为佐证，不能单独判定为重复：同一开发商同一年
                # 常有多部完全不同的作品。
                signals.append((0.35, "公司与发行年份一致"))

            if not signals:
                continue
            if not any(strength >= 0.7 for strength, _ in signals):
                continue
            score = max(signal[0] for signal in signals)
            if len(signals) > 1:
                score = min(1.0, score + 0.03 * (len(signals) - 1))
            if score < min_score:
                continue
            candidates.append(
                {
                    "work_id": left_id,
                    "other_id": right_id,
                    "score": round(score, 4),
                    "reasons": [signal[1] for signal in signals],
                }
            )

    candidates.sort(key=lambda item: (-item["score"], item["work_id"], item["other_id"]))
    return candidates[: max(0, limit)]


def merge_works(conn: sqlite3.Connection, source_id: int, target_id: int) -> dict[str, Any]:
    """Merge one work into another, keeping the target work and manual fields."""
    if source_id == target_id:
        raise ValueError("来源作品与目标作品不能是同一部")
    source = conn.execute("SELECT * FROM works WHERE id = ?", (source_id,)).fetchone()
    target = conn.execute("SELECT * FROM works WHERE id = ?", (target_id,)).fetchone()
    if source is None:
        raise ValueError(f"来源作品 {source_id} 不存在")
    if target is None:
        raise ValueError(f"目标作品 {target_id} 不存在")

    child_tables = (
        "external_refs",
        "titles",
        "work_tags",
        "work_companies",
        "my_entries",
        "feedback",
        "recommendations",
    )
    snapshot: dict[str, Any] = {"work": dict(source)}
    for table in child_tables:
        snapshot[table] = [
            dict(row)
            for row in conn.execute(
                f"SELECT * FROM {table} WHERE work_id = ?", (source_id,)
            ).fetchall()
        ]

    moved: dict[str, int] = {}
    try:
        with conn:
            for table in (
                "external_refs",
                "titles",
                "work_tags",
                "work_companies",
                "feedback",
                "recommendations",
            ):
                cur = conn.execute(
                    f"UPDATE OR IGNORE {table} SET work_id = ? WHERE work_id = ?",
                    (target_id, source_id),
                )
                moved[table] = max(0, cur.rowcount)

            src_entry = conn.execute(
                "SELECT * FROM my_entries WHERE work_id = ?", (source_id,)
            ).fetchone()
            tgt_entry = conn.execute(
                "SELECT * FROM my_entries WHERE work_id = ?", (target_id,)
            ).fetchone()
            if src_entry is not None:
                if tgt_entry is None:
                    conn.execute(
                        "UPDATE my_entries SET work_id = ? WHERE work_id = ?",
                        (target_id, source_id),
                    )
                else:
                    # Target data wins; only fill in what the target lacks.
                    conn.execute(
                        """
                        UPDATE my_entries SET
                            status = ?,
                            rating = COALESCE(?, rating),
                            favorite = CASE WHEN favorite = 1 OR ? = 1 THEN 1 ELSE 0 END,
                            notes = COALESCE(NULLIF(?, ''), notes),
                            started_at = COALESCE(?, started_at),
                            finished_at = COALESCE(?, finished_at),
                            updated_at = ?
                        WHERE work_id = ?
                        """,
                        (
                            tgt_entry["status"] or src_entry["status"],
                            (
                                tgt_entry["rating"]
                                if tgt_entry["rating"] is not None
                                else src_entry["rating"]
                            ),
                            src_entry["favorite"],
                            tgt_entry["notes"],
                            tgt_entry["started_at"],
                            tgt_entry["finished_at"],
                            now_iso(),
                            target_id,
                        ),
                    )
                    conn.execute("DELETE FROM my_entries WHERE work_id = ?", (source_id,))
                moved["my_entries"] = 1
            else:
                moved["my_entries"] = 0

            conn.execute(
                "INSERT INTO merge_log(source_id, target_id, created_at, snapshot_json) "
                "VALUES(?, ?, ?, ?)",
                (source_id, target_id, now_iso(), json_dumps(snapshot)),
            )
            conn.execute("DELETE FROM works WHERE id = ?", (source_id,))
    except ValueError:
        raise
    except Exception as exc:  # noqa: BLE001 - 统一转换为中文 ValueError
        raise ValueError(f"合并作品失败：{exc}") from exc

    return {"ok": True, "source_id": source_id, "target_id": target_id, "moved": moved}


def search_works(
    conn: sqlite3.Connection,
    *,
    query: str | None = None,
    tag: str | None = None,
    status: str | None = None,
    include_nsfw: bool = False,
    min_rating: float | None = None,
    platform: str | None = None,
    language: str | None = None,
    min_year: int | None = None,
    max_length_minutes: int | None = None,
    sort: str = "rating",
    page: int = 1,
    limit: int = 20,
) -> dict[str, Any]:
    page = max(1, page)
    limit = max(1, min(100, limit))
    where: list[str] = []
    params: list[Any] = []

    raw_query = str(query or "").strip()
    normalized = normalize_text(raw_query)
    if raw_query:
        like = f"%{raw_query}%"
        norm_like = f"%{normalized}%" if normalized else like
        where.append(
            "(w.title LIKE ? OR w.original_title LIKE ? OR w.romanized_title LIKE ? "
            "OR w.description LIKE ? OR w.normalized_title LIKE ? "
            "OR EXISTS (SELECT 1 FROM titles t WHERE t.work_id = w.id "
            "AND (t.title LIKE ? OR t.normalized_title LIKE ?)) "
            "OR EXISTS (SELECT 1 FROM work_tags wt JOIN tags tg ON tg.id = wt.tag_id "
            "WHERE wt.work_id = w.id AND (tg.name LIKE ? OR tg.name_zh LIKE ? OR tg.aliases LIKE ? "
            "OR EXISTS (SELECT 1 FROM tag_aliases ta "
            "WHERE ta.tag_id = tg.id AND ta.alias_normalized LIKE ?))))"
        )
        params.extend(
            [like, like, like, like, norm_like, like, norm_like, like, like, like, norm_like]
        )

    if tag:
        tag_ids = _resolve_tag_ids(conn, tag)
        if not tag_ids:
            where.append("0 = 1")
        else:
            placeholders = ",".join("?" for _ in tag_ids)
            where.append(
                f"EXISTS (SELECT 1 FROM work_tags wt "
                f"WHERE wt.work_id = w.id AND wt.tag_id IN ({placeholders}))"
            )
            params.extend(tag_ids)

    if status == "none":
        where.append("NOT EXISTS (SELECT 1 FROM my_entries e WHERE e.work_id = w.id)")
    elif status:
        where.append("EXISTS (SELECT 1 FROM my_entries e WHERE e.work_id = w.id AND e.status = ?)")
        params.append(status)
    if not include_nsfw:
        where.append("w.nsfw = 0")
    if min_rating is not None:
        where.append("w.rating IS NOT NULL AND w.rating >= ?")
        params.append(min_rating)
    if platform:
        where.append("w.platforms LIKE ?")
        params.append(f"%{json_dumps(str(platform))}%")
    if language:
        where.append("w.languages LIKE ?")
        params.append(f"%{json_dumps(str(language))}%")
    if min_year is not None:
        where.append("w.release_year IS NOT NULL AND w.release_year >= ?")
        params.append(int(min_year))
    if max_length_minutes is not None:
        where.append("w.length_minutes IS NOT NULL AND w.length_minutes <= ?")
        params.append(int(max_length_minutes))

    where_sql = ("WHERE " + " AND ".join(where)) if where else ""
    total = conn.execute(f"SELECT COUNT(*) AS c FROM works w {where_sql}", params).fetchone()["c"]

    order_map = {
        "rating": "w.rating IS NULL, w.rating DESC, w.rating_count DESC",
        "votes": "w.rating_count IS NULL, w.rating_count DESC",
        "release": "w.release_date IS NULL, w.release_date DESC",
        "title": "w.title ASC",
        "random": "RANDOM()",
    }
    order_sql = order_map.get(sort, order_map["rating"])

    # Relevance: exact normalized title > prefix > contains > alias title > other fields.
    relevance_sql = ""
    relevance_params: list[Any] = []
    if normalized:
        relevance_sql = (
            "CASE "
            "WHEN w.normalized_title = ? THEN 0 "
            "WHEN w.normalized_title LIKE ? THEN 1 "
            "WHEN w.normalized_title LIKE ? THEN 2 "
            "WHEN EXISTS (SELECT 1 FROM titles t WHERE t.work_id = w.id AND t.normalized_title = ?) THEN 3 "
            "WHEN EXISTS (SELECT 1 FROM titles t WHERE t.work_id = w.id AND t.normalized_title LIKE ?) THEN 4 "
            "ELSE 5 END ASC, "
        )
        relevance_params = [
            normalized,
            f"{normalized}%",
            f"%{normalized}%",
            normalized,
            f"{normalized}%",
        ]

    rows = conn.execute(
        f"SELECT w.* FROM works w {where_sql} "
        f"ORDER BY {relevance_sql}{order_sql} LIMIT ? OFFSET ?",
        [*params, *relevance_params, limit, (page - 1) * limit],
    ).fetchall()
    items = [_work_row(row) for row in rows]
    _attach_tags(conn, items)
    _attach_companies(conn, items)
    return {"items": items, "total": total, "page": page, "limit": limit}


def list_tags(conn: sqlite3.Connection, query: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
    limit = max(1, min(500, limit))
    params: list[Any] = []
    where = ""
    if query:
        raw = str(query).strip()
        normalized = normalize_text(raw)
        norm_needle = f"%{normalized}%" if normalized else f"%{raw}%"
        where = (
            "WHERE (t.name LIKE ? OR t.name_zh LIKE ? OR t.aliases LIKE ? "
            "OR EXISTS (SELECT 1 FROM tag_aliases ta WHERE ta.tag_id = t.id "
            "AND (ta.alias_normalized LIKE ? OR ta.alias_normalized LIKE ?)))"
        )
        params = [f"%{raw}%", f"%{raw}%", f"%{raw}%", f"%{raw}%", norm_needle]
    rows = conn.execute(
        f"""
        SELECT t.id, t.name, t.name_zh, t.aliases, t.category, COUNT(wt.work_id) AS work_count
        FROM tags t
        LEFT JOIN work_tags wt ON wt.tag_id = t.id
        {where}
        GROUP BY t.id
        ORDER BY work_count DESC, t.name ASC
        LIMIT ?
        """,
        [*params, limit],
    ).fetchall()
    result: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        item["aliases"] = json_loads(item.get("aliases"), []) or []
        result.append(item)
    return result


def get_entries(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT work_id, status, rating, favorite, notes, started_at, finished_at, updated_at "
        "FROM my_entries ORDER BY updated_at DESC"
    ).fetchall()
    result: list[dict[str, Any]] = []
    for row in rows:
        work = get_work(conn, int(row["work_id"]))
        if not work:
            continue
        work["entry"] = {
            "status": row["status"],
            "rating": row["rating"],
            "favorite": bool(row["favorite"]),
            "notes": row["notes"],
            "started_at": row["started_at"],
            "finished_at": row["finished_at"],
            "updated_at": row["updated_at"],
        }
        result.append(work)
    return result


def upsert_entry(conn: sqlite3.Connection, work_id: int, data: dict[str, Any]) -> dict[str, Any] | None:
    existing = conn.execute("SELECT * FROM my_entries WHERE work_id = ?", (work_id,)).fetchone()
    status = data.get("status") or (existing["status"] if existing else "want")
    if status not in ENTRY_STATUSES:
        raise ValueError(f"invalid status: {status}")
    rating = data.get("rating", existing["rating"] if existing else None)
    if rating is not None:
        rating = float(rating)
        if rating < 0 or rating > 10:
            raise ValueError("rating must be between 0 and 10")
    favorite = data.get("favorite")
    if favorite is None:
        favorite = bool(existing["favorite"]) if existing else False
    notes = data.get("notes", existing["notes"] if existing else None)
    timestamp = now_iso()
    conn.execute(
        """
        INSERT INTO my_entries(work_id, status, rating, favorite, notes, started_at, finished_at, updated_at)
        VALUES(?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(work_id) DO UPDATE SET
            status = excluded.status,
            rating = excluded.rating,
            favorite = excluded.favorite,
            notes = excluded.notes,
            updated_at = excluded.updated_at
        """,
        (
            work_id,
            status,
            rating,
            1 if favorite else 0,
            notes,
            data.get("started_at", existing["started_at"] if existing else None),
            data.get("finished_at", existing["finished_at"] if existing else None),
            timestamp,
        ),
    )
    conn.commit()
    return get_work(conn, work_id)


def delete_entry(conn: sqlite3.Connection, work_id: int) -> None:
    conn.execute("DELETE FROM my_entries WHERE work_id = ?", (work_id,))
    conn.commit()


def add_feedback(conn: sqlite3.Connection, work_id: int, kind: str, note: str | None = None) -> None:
    if kind not in FEEDBACK_KINDS:
        raise ValueError(f"invalid feedback kind: {kind}")
    conn.execute(
        """
        INSERT INTO feedback(work_id, kind, note, created_at)
        VALUES(?, ?, ?, ?)
        ON CONFLICT(work_id, kind) DO UPDATE SET note = excluded.note, created_at = excluded.created_at
        """,
        (work_id, kind, note, now_iso()),
    )
    conn.commit()


def get_feedback_work_ids(conn: sqlite3.Connection, kind: str = "not_interested") -> set[int]:
    return {
        int(row["work_id"])
        for row in conn.execute("SELECT work_id FROM feedback WHERE kind = ?", (kind,)).fetchall()
    }


def get_settings(conn: sqlite3.Connection) -> dict[str, Any]:
    defaults: dict[str, Any] = {
        "include_nsfw": False,
        "min_year": None,
        "max_length_minutes": None,
        "platform": None,
        "language": None,
        "diversity": 0.15,
        "quiz_answers": {},
        "quiz_profile": None,
        "quiz_merge_home": True,
        "persona_profiles": {},
        "home_profile_sources": None,
    }
    for row in conn.execute("SELECT key, value FROM settings").fetchall():
        defaults[row["key"]] = json_loads(row["value"], row["value"])
    return defaults


def set_settings(conn: sqlite3.Connection, values: dict[str, Any]) -> dict[str, Any]:
    for key, value in values.items():
        conn.execute(
            "INSERT INTO settings(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, json_dumps(value)),
        )
    conn.commit()
    return get_settings(conn)


def start_sync_run(conn: sqlite3.Connection, source: str) -> int:
    cur = conn.execute(
        "INSERT INTO sync_runs(source, status, started_at) VALUES(?, 'running', ?)",
        (source, now_iso()),
    )
    conn.commit()
    return int(cur.lastrowid)


def finish_sync_run(
    conn: sqlite3.Connection,
    run_id: int,
    status: str,
    stats: dict[str, Any] | None = None,
    error: str | None = None,
) -> None:
    conn.execute(
        "UPDATE sync_runs SET status = ?, finished_at = ?, stats_json = ?, error = ? WHERE id = ?",
        (status, now_iso(), json_dumps(stats or {}), error, run_id),
    )
    conn.commit()


def get_sync_runs(conn: sqlite3.Connection, limit: int = 20) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT * FROM sync_runs ORDER BY id DESC LIMIT ?", (max(1, min(100, limit)),)
    ).fetchall()
    result = []
    for row in rows:
        item = dict(row)
        item["stats"] = json_loads(item.pop("stats_json"), {})
        result.append(item)
    return result


def save_recommendations(
    conn: sqlite3.Connection,
    items: list[dict[str, Any]],
    algorithm_version: str = "content-v1",
) -> str:
    batch_id = uuid.uuid4().hex
    timestamp = now_iso()
    conn.executemany(
        """
        INSERT INTO recommendations(batch_id, work_id, score, reason, algorithm_version, created_at)
        VALUES(?, ?, ?, ?, ?, ?)
        """,
        [
            (batch_id, item["id"], item["score"], item.get("reason"), algorithm_version, timestamp)
            for item in items
        ],
    )
    conn.commit()
    return batch_id


def get_stats(conn: sqlite3.Connection) -> dict[str, Any]:
    def count(table: str) -> int:
        return int(conn.execute(f"SELECT COUNT(*) AS c FROM {table}").fetchone()["c"])

    return {
        "works": count("works"),
        "tags": count("tags"),
        "companies": count("companies"),
        "entries": count("my_entries"),
        "feedback": count("feedback"),
        "recommendations": count("recommendations"),
        "sync_runs": count("sync_runs"),
    }
