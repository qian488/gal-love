"""Small normalization helpers shared by importers, repositories and recommenders."""

from __future__ import annotations

import json
import re
import unicodedata
from datetime import datetime, timezone
from typing import Any, Iterable


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


# Common simplified -> traditional characters.  Traditional is used as the
# canonical form so that existing data (e.g. 物語) keeps its normalized value.
_SIMPLIFIED_TO_TRADITIONAL: dict[str, str] = {
    "恋": "戀", "爱": "愛", "学": "學", "园": "園", "剧": "劇", "谜": "謎",
    "惊": "驚", "话": "話", "说": "說", "书": "書", "画": "畫", "声": "聲",
    "优": "優", "丽": "麗", "华": "華", "东": "東", "时": "時", "间": "間",
    "长": "長", "门": "門", "开": "開", "关": "關", "后": "後", "台": "臺",
    "万": "萬", "与": "與", "风": "風", "云": "雲", "电": "電", "视": "視",
    "觉": "覺", "场": "場", "头": "頭", "体": "體", "现": "現", "实": "實",
    "个": "個", "们": "們", "来": "來", "动": "動", "类": "類", "计": "計",
    "划": "劃", "设": "設", "备": "備", "处": "處", "应": "應", "该": "該",
    "数": "數", "据": "據", "库": "庫", "页": "頁", "网": "網", "络": "絡",
    "软": "軟", "盘": "盤", "显": "顯", "机": "機", "扫": "掃", "语": "語",
    "义": "義", "龙": "龍", "马": "馬", "鸟": "鳥", "鱼": "魚", "车": "車",
    "军": "軍", "农": "農", "医": "醫", "邮": "郵", "铁": "鐵", "钟": "鐘",
    "汉": "漢", "节": "節", "岁": "歲", "观": "觀", "证": "證", "评": "評",
    "识": "識", "亲": "親",
}
_SIMPLIFIED_TRANSLATION = {ord(key): value for key, value in _SIMPLIFIED_TO_TRADITIONAL.items()}


def normalize_text(value: str | None) -> str:
    """Normalize titles/tags for fuzzy matching.

    Applies NFKC (full-width -> half-width), casefolding, common simplified ->
    traditional character folding, and strips whitespace and punctuation.
    """
    if not value:
        return ""
    text = unicodedata.normalize("NFKC", str(value)).casefold()
    text = text.translate(_SIMPLIFIED_TRANSLATION)
    text = re.sub(
        r"[\s\-_—–·・:：,，.。!！?？'\"“”‘’()（）\[\]【】{}<>《》/\\|~～+&;；、％%]+",
        "",
        text,
    )
    return text.strip()


def parse_year(value: str | None) -> int | None:
    if not value:
        return None
    match = re.search(r"(19|20)\d{2}", str(value))
    return int(match.group(0)) if match else None


def parse_date(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=timezone.utc).date().isoformat()
    text = str(value).strip()
    if not text or text.lower() in {"tba", "unknown", "null", "none"}:
        return None
    return text


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def json_loads(value: str | None, default: Any = None) -> Any:
    if not value:
        return default
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return default


def unique_preserving_order(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        key = normalize_text(value)
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(value.strip())
    return result


def split_infobox_value(value: Any) -> list[str]:
    """Bangumi infobox values can be strings or lists of {k, v} objects."""
    if value is None:
        return []
    if isinstance(value, str):
        parts = re.split(r"[,，、/|]", value)
        return [part.strip() for part in parts if part.strip()]
    if isinstance(value, list):
        result: list[str] = []
        for item in value:
            if isinstance(item, str):
                result.append(item.strip())
            elif isinstance(item, dict):
                raw = item.get("v") or item.get("value")
                if raw:
                    result.append(str(raw).strip())
        return [item for item in result if item]
    return [str(value).strip()]
