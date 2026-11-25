"""VNDB API client and normalized payload parser."""

from __future__ import annotations

import time
from typing import Any, Iterator

import httpx

from ..config import Settings, settings
from ..normalize import parse_date, parse_year

VNDB_VN_FIELDS = ",".join(
    [
        "title",
        "alttitle",
        "titles{lang,title,latin,official,main}",
        "aliases",
        "olang",
        "released",
        "languages",
        "platforms",
        "image.url",
        "image.sexual",
        "length",
        "length_minutes",
        "description",
        "rating",
        "average",
        "votecount",
        "tags{id,name,rating,spoiler,category}",
        "developers{id,name}",
    ]
)


class VndbClient:
    def __init__(self, config: Settings | None = None) -> None:
        self.config = config or settings
        self._client = httpx.Client(
            base_url=self.config.vndb_api_base,
            timeout=self.config.request_timeout,
            headers={
                "User-Agent": "gal-love-personal/0.1 (personal recommendation project)",
                "Content-Type": "application/json",
            },
        )
        self._last_request = 0.0

    def __enter__(self) -> "VndbClient":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    def close(self) -> None:
        self._client.close()

    def _throttle(self) -> None:
        elapsed = time.monotonic() - self._last_request
        if elapsed < self.config.vndb_request_interval:
            time.sleep(self.config.vndb_request_interval - elapsed)
        self._last_request = time.monotonic()

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        last_error: Exception | None = None
        for attempt in range(3):
            self._throttle()
            try:
                response = self._client.post(path, json=payload)
                if response.status_code == 429:
                    retry_after = float(response.headers.get("Retry-After", "5"))
                    time.sleep(retry_after)
                    continue
                response.raise_for_status()
                return response.json()
            except (httpx.HTTPError, ValueError) as exc:
                last_error = exc
                if attempt < 2:
                    time.sleep(2 ** attempt)
        raise RuntimeError(f"VNDB request failed: {last_error}")

    def fetch_top_pages(
        self, limit: int = 100, min_votes: int = 0
    ) -> Iterator[list[dict[str, Any]]]:
        """Yield raw VN objects page by page (ordered by vote count)."""
        remaining = max(1, limit)
        page = 1
        while remaining > 0:
            filters: list[Any] = ["devstatus", "=", 0]
            if min_votes > 0:
                filters = ["and", filters, ["votecount", ">=", min_votes]]
            result = self._post(
                "/vn",
                {
                    "filters": filters,
                    "fields": VNDB_VN_FIELDS,
                    "sort": "votecount",
                    "reverse": True,
                    "results": min(100, remaining),
                    "page": page,
                },
            )
            results = result.get("results") or []
            if not results:
                break
            batch = results[:remaining]
            yield batch
            remaining -= len(batch)
            truncated = len(batch) < len(results)
            if not result.get("more") or truncated:
                break
            page += 1

    def fetch_top(self, limit: int = 100, min_votes: int = 0) -> Iterator[dict[str, Any]]:
        """Yield raw VN objects ordered by vote count."""
        for page in self.fetch_top_pages(limit=limit, min_votes=min_votes):
            yield from page

    def fetch_by_id(self, vn_id: str) -> dict[str, Any]:
        result = self._post(
            "/vn",
            {
                "filters": ["id", "=", vn_id],
                "fields": VNDB_VN_FIELDS,
                "results": 1,
            },
        )
        results = result.get("results") or []
        if not results:
            raise ValueError(f"VNDB entry not found: {vn_id}")
        return results[0]


def parse_vn(vn: dict[str, Any]) -> dict[str, Any]:
    vn_id = str(vn.get("id") or "")
    titles = vn.get("titles") or []
    title_zh = None
    for title in titles:
        lang = str(title.get("lang") or "").lower()
        if lang.startswith("zh") and title.get("title"):
            title_zh = title["title"]
            break

    tags = []
    for tag in vn.get("tags") or []:
        name = tag.get("name")
        if not name:
            continue
        rating = float(tag.get("rating") or 0)
        tags.append(
            {
                "name": name,
                "weight": max(0.1, rating),
                "spoiler": int(tag.get("spoiler") or 0),
                "category": tag.get("category"),
                "external_id": tag.get("id"),
            }
        )
    tags.sort(key=lambda item: item["weight"], reverse=True)

    nsfw = any(
        tag.get("category") == "ero" and float(tag.get("rating") or 0) >= 1.0
        for tag in vn.get("tags") or []
    )
    image = vn.get("image") or {}
    if not nsfw and float(image.get("sexual") or 0) >= 1.5:
        nsfw = True

    developers = [
        {"name": developer.get("name"), "role": "developer"}
        for developer in vn.get("developers") or []
        if developer.get("name")
    ]

    title = str(vn.get("title") or "").strip()
    original_title = str(vn.get("alttitle") or "").strip() or None
    return {
        "source": "vndb",
        "external_id": vn_id,
        "url": f"https://vndb.org/{vn_id}" if vn_id else None,
        "title": title_zh or title,
        "title_zh": title_zh,
        "title_lang": "zh" if title_zh else "en",
        "original_title": original_title,
        "romanized_title": title if title_zh else None,
        "description": vn.get("description"),
        "cover_url": image.get("url"),
        "release_date": parse_date(vn.get("released")),
        "release_year": parse_year(vn.get("released")),
        "length_minutes": vn.get("length_minutes"),
        "length_label": vn.get("length"),
        "platforms": vn.get("platforms") or [],
        "languages": vn.get("languages") or [],
        "vndb_rating": vn.get("rating"),
        "vndb_votecount": vn.get("votecount"),
        "nsfw": nsfw,
        "titles": [
            {
                "lang": item.get("lang"),
                "title": item.get("title"),
                "latin": item.get("latin"),
                "official": bool(item.get("official")),
                "main": bool(item.get("main")),
            }
            for item in titles
            if item.get("title")
        ],
        "aliases": vn.get("aliases") or [],
        "tags": tags,
        "companies": developers,
        "raw": vn,
    }


def _as_int(value: Any) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def import_vndb(
    conn,
    *,
    limit: int = 100,
    min_votes: int = 0,
    client: VndbClient | None = None,
    run_id: int | None = None,
    incremental: bool = True,
) -> dict[str, Any]:
    """Import VNDB entries, optionally skipping entries that did not change.

    ``incremental=True`` (the default) loads cursors from ``app_meta``, compares
    each fetched raw payload with ``external_refs.raw_json`` and stops early once
    a whole page is unchanged.  ``incremental=False`` performs a full sweep.
    """
    from ..repository import finish_sync_run, save_work_payload, start_sync_run
    from .state import classify_entry, cursor_time, load_cursor, save_cursor

    own_client = client is None
    client = client or VndbClient()
    if run_id is None:
        run_id = start_sync_run(conn, "vndb")
    old_cursor = load_cursor(conn, "vndb") if incremental else {}
    stats: dict[str, Any] = {
        "requested": limit,
        "fetched": 0,
        "imported": 0,
        "failed": 0,
        "errors": [],
        "new": 0,
        "updated": 0,
        "unchanged": 0,
        "cursor": dict(old_cursor),
        "incremental": incremental,
        "early_stopped": False,
    }
    last_fetch_at = old_cursor.get("last_fetch_at")
    prev_max_votes = _as_int(old_cursor.get("last_max_votecount"))
    max_votes = prev_max_votes

    def _pages() -> Any:
        fetch_pages = getattr(client, "fetch_top_pages", None)
        if callable(fetch_pages):
            return fetch_pages(limit=limit, min_votes=min_votes)
        batch = list(client.fetch_top(limit=limit, min_votes=min_votes))
        return [batch] if batch else []

    try:
        for page in _pages():
            if not page:
                break
            page_changed = 0
            page_stale_refs = 0
            page_max_votes: int | None = None
            for raw in page:
                stats["fetched"] += 1
                votes = _as_int(raw.get("votecount"))
                if votes is not None:
                    max_votes = votes if max_votes is None else max(max_votes, votes)
                    page_max_votes = votes if page_max_votes is None else max(page_max_votes, votes)
                try:
                    status, prior_fetched = classify_entry(conn, "vndb", raw.get("id"), raw)
                    if status == "unchanged" and incremental:
                        stats["unchanged"] += 1
                        # fetched_at 早于游标说明是上次同步窗口之前的引用，
                        # 阻止本页提前停止，让旧数据再刷新一遍。
                        if last_fetch_at is not None and (
                            not prior_fetched or str(prior_fetched) < str(last_fetch_at)
                        ):
                            page_stale_refs += 1
                        continue
                    if status == "new":
                        stats["new"] += 1
                    else:
                        stats["updated"] += 1
                    page_changed += 1
                    work_id = save_work_payload(conn, parse_vn(raw))
                    if work_id:
                        stats["imported"] += 1
                except Exception as exc:  # noqa: BLE001 - keep importing other entries
                    stats["failed"] += 1
                    if len(stats["errors"]) < 10:
                        stats["errors"].append(f"{raw.get('id')}: {exc}")
            if (
                incremental
                and page_changed == 0
                and page_stale_refs == 0
                and stats["failed"] == 0
                and (
                    page_max_votes is None
                    or prev_max_votes is None
                    or page_max_votes <= prev_max_votes
                )
            ):
                stats["early_stopped"] = True
                break

        new_cursor = dict(old_cursor)
        new_cursor["last_fetch_at"] = cursor_time()
        if max_votes is not None:
            new_cursor["last_max_votecount"] = max_votes
        save_cursor(conn, "vndb", new_cursor)
        stats["cursor"] = new_cursor
        finish_sync_run(conn, run_id, "success", stats)
        return {"run_id": run_id, **stats}
    except Exception as exc:
        finish_sync_run(conn, run_id, "failed", stats, str(exc))
        raise
    finally:
        if own_client:
            client.close()
