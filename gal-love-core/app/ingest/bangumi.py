"""Bangumi API client and normalized payload parser."""

from __future__ import annotations

import re
import time
from typing import Any, Iterator

import httpx

from ..config import Settings, settings
from ..normalize import parse_date, parse_year, split_infobox_value

AVG_KEYWORDS = (
    "视觉小说",
    "avg",
    "adv",
    "adventure game",
    "文字冒险",
    "文字游戏",
    "galgame",
    "美少女游戏",
    "恋爱冒险",
    "乙女",
    "bl",
    "百合",
    "sound novel",
    "kinetic novel",
)


class BangumiClient:
    def __init__(self, config: Settings | None = None) -> None:
        self.config = config or settings
        self._client = httpx.Client(
            base_url=self.config.bangumi_api_base,
            timeout=self.config.request_timeout,
            headers={
                "User-Agent": self.config.bangumi_user_agent,
                "Accept": "application/json",
            },
        )
        self._last_request = 0.0

    def __enter__(self) -> "BangumiClient":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    def close(self) -> None:
        self._client.close()

    def _throttle(self) -> None:
        elapsed = time.monotonic() - self._last_request
        if elapsed < self.config.bangumi_request_interval:
            time.sleep(self.config.bangumi_request_interval - elapsed)
        self._last_request = time.monotonic()

    def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        last_error: Exception | None = None
        for attempt in range(3):
            self._throttle()
            try:
                response = self._client.request(method, path, **kwargs)
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
        raise RuntimeError(f"Bangumi request failed: {last_error}")

    def fetch_top_pages(self, limit: int = 100) -> Iterator[list[dict[str, Any]]]:
        """Yield game subject pages ordered by Bangumi rank."""
        offset = 0
        remaining = max(1, limit)
        page_size = 50
        while remaining > 0:
            data = self._request(
                "GET",
                "/v0/subjects",
                params={
                    "type": 4,
                    "sort": "rank",
                    "limit": min(page_size, remaining),
                    "offset": offset,
                },
            )
            items = data.get("data") or []
            if not items:
                break
            batch = items[:remaining]
            yield batch
            remaining -= len(batch)
            offset += len(items)
            truncated = len(batch) < len(items)
            if len(items) < page_size or truncated:
                break

    def fetch_top(self, limit: int = 100) -> Iterator[dict[str, Any]]:
        """Yield game subjects ordered by Bangumi rank."""
        for page in self.fetch_top_pages(limit=limit):
            yield from page

    def fetch_subject(self, subject_id: int | str) -> dict[str, Any]:
        return self._request("GET", f"/v0/subjects/{subject_id}")

    def search(self, keyword: str, limit: int = 10) -> list[dict[str, Any]]:
        data = self._request(
            "POST",
            "/v0/search/subjects",
            params={"limit": limit, "offset": 0},
            json={"keyword": keyword, "sort": "rank", "filter": {"type": [4]}},
        )
        return data.get("data") or []


def _infobox_map(subject: dict[str, Any]) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for item in subject.get("infobox") or []:
        key = str(item.get("key") or "").strip()
        if not key:
            continue
        result[key] = split_infobox_value(item.get("value"))
    return result


def _pick_info(info: dict[str, list[str]], keys: tuple[str, ...]) -> list[str]:
    for key in keys:
        if info.get(key):
            return info[key]
    return []


def _parse_length_minutes(value: str) -> int | None:
    text = str(value or "").lower()
    hours = re.search(r"(\d+(?:\.\d+)?)\s*(?:小时|h|hour)", text)
    minutes = re.search(r"(\d+)\s*(?:分钟|min|m)", text)
    if hours:
        return int(float(hours.group(1)) * 60 + (int(minutes.group(1)) if minutes else 0))
    if minutes:
        return int(minutes.group(1))
    return None


def parse_subject(subject: dict[str, Any]) -> dict[str, Any]:
    subject_id = str(subject.get("id") or "")
    name = str(subject.get("name") or "").strip()
    name_cn = str(subject.get("name_cn") or "").strip() or None
    info = _infobox_map(subject)

    aliases = _pick_info(info, ("别名", "中文名", "英文名", "日文名"))
    aliases = [alias for alias in aliases if alias and alias not in {name, name_cn}]

    tags = []
    for tag in subject.get("tags") or []:
        tag_name = tag.get("name")
        if not tag_name:
            continue
        count = int(tag.get("count") or 0)
        tags.append(
            {
                "name": str(tag_name),
                "weight": 1.0 + min(count, 100) / 50.0,
                "spoiler": 0,
                "category": "bangumi",
            }
        )
    tags.sort(key=lambda item: item["weight"], reverse=True)

    companies: list[dict[str, str]] = []
    for key in ("开发", "开发商", "制作", "制作公司", "发行", "发行商", "品牌"):
        for value in info.get(key, []):
            companies.append({"name": value, "role": "developer" if key in {"开发", "开发商", "制作", "制作公司", "品牌"} else "publisher"})

    platforms = _pick_info(info, ("平台", "游戏平台"))
    if not platforms and subject.get("platform"):
        platforms = [subject["platform"]]
    languages = _pick_info(info, ("语言", "游戏语言"))
    length_minutes = None
    for key in ("游戏时间", "时长", "游戏时长"):
        if info.get(key):
            length_minutes = _parse_length_minutes(info[key][0])
            if length_minutes:
                break

    rating_obj = subject.get("rating") or {}
    score = None
    count = None
    if isinstance(rating_obj, dict):
        score = rating_obj.get("score")
        count = rating_obj.get("total")
    if score is None:
        score = subject.get("score")
    if count is None:
        count = subject.get("collection_total")

    images = subject.get("images") or {}
    cover_url = images.get("large") or images.get("common") or images.get("medium")
    summary = subject.get("summary") or subject.get("short_summary")

    tag_names = {str(tag["name"]).casefold() for tag in tags}
    text_for_avg = " ".join([summary or "", *tag_names]).casefold()
    nsfw = bool(subject.get("nsfw")) or any(
        keyword in tag_names for keyword in {"r18", "18禁", "成人", "拔作", "エロ"}
    )

    return {
        "source": "bangumi",
        "external_id": subject_id,
        "url": f"https://bgm.tv/subject/{subject_id}" if subject_id else None,
        "title": name_cn or name,
        "title_zh": name_cn,
        "title_lang": "zh" if name_cn else "ja",
        "original_title": name,
        "romanized_title": None,
        "description": summary,
        "cover_url": cover_url,
        "release_date": parse_date(subject.get("date")),
        "release_year": parse_year(subject.get("date")),
        "length_minutes": length_minutes,
        "length_label": None,
        "platforms": platforms,
        "languages": languages,
        "bangumi_rating": float(score) if score is not None else None,
        "bangumi_votecount": int(count) if count is not None else None,
        "nsfw": nsfw,
        "titles": [
            item
            for item in [
                {"lang": "ja", "title": name, "main": not bool(name_cn)},
                {"lang": "zh", "title": name_cn, "main": bool(name_cn)},
            ]
            if item.get("title")
        ],
        "aliases": aliases,
        "tags": tags,
        "companies": companies,
        "raw": subject,
        "_avg_text": text_for_avg,
    }


def looks_like_avg(subject: dict[str, Any]) -> bool:
    parsed = parse_subject(subject)
    text = parsed.pop("_avg_text", "")
    if any(keyword in text for keyword in AVG_KEYWORDS):
        return True
    # Bangumi game entries without tags are common in lists; keep them rather than silently losing data.
    return not subject.get("tags")


def _as_int(value: Any) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _raw_votecount(raw: dict[str, Any]) -> int | None:
    rating = raw.get("rating")
    if isinstance(rating, dict):
        value = _as_int(rating.get("total"))
        if value is not None:
            return value
    return _as_int(raw.get("collection_total"))


def import_bangumi(
    conn,
    *,
    limit: int = 100,
    client: BangumiClient | None = None,
    avg_only: bool = True,
    run_id: int | None = None,
    incremental: bool = True,
) -> dict[str, Any]:
    """Import Bangumi entries, skipping unchanged ones when incremental."""
    from ..repository import finish_sync_run, save_work_payload, start_sync_run
    from .state import classify_entry, cursor_time, load_cursor, save_cursor

    own_client = client is None
    client = client or BangumiClient()
    if run_id is None:
        run_id = start_sync_run(conn, "bangumi")
    old_cursor = load_cursor(conn, "bangumi") if incremental else {}
    stats: dict[str, Any] = {
        "requested": limit,
        "fetched": 0,
        "imported": 0,
        "skipped": 0,
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
            return fetch_pages(limit=limit)
        batch = list(client.fetch_top(limit=limit))
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
                votes = _raw_votecount(raw)
                if votes is not None:
                    max_votes = votes if max_votes is None else max(max_votes, votes)
                    page_max_votes = votes if page_max_votes is None else max(page_max_votes, votes)
                if avg_only and not looks_like_avg(raw):
                    stats["skipped"] += 1
                    continue
                try:
                    status, prior_fetched = classify_entry(conn, "bangumi", raw.get("id"), raw)
                    if status == "unchanged" and incremental:
                        stats["unchanged"] += 1
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
                    payload = parse_subject(raw)
                    payload.pop("_avg_text", None)
                    work_id = save_work_payload(conn, payload)
                    if work_id:
                        stats["imported"] += 1
                except Exception as exc:  # noqa: BLE001
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
        save_cursor(conn, "bangumi", new_cursor)
        stats["cursor"] = new_cursor
        finish_sync_run(conn, run_id, "success", stats)
        return {"run_id": run_id, **stats}
    except Exception as exc:
        finish_sync_run(conn, run_id, "failed", stats, str(exc))
        raise
    finally:
        if own_client:
            client.close()
