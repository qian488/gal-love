"""Persistence helpers for the personal Gal Love database.

This package re-exports the historical ``app.repository`` surface so existing
``from .repository import name`` / ``from app.repository import name`` imports
keep working unchanged.
"""

from __future__ import annotations

from ..normalize import (
    json_dumps,
    json_loads,
    normalize_text,
    now_iso,
    parse_year,
    unique_preserving_order,
)
from ..nsfw import normalize_policy, sql_clause
from ..tag_zh import canonical_lookup, canonical_lookup_keys
from ._entries import (
    ENTRY_STATUSES,
    FEEDBACK_KINDS,
    add_feedback,
    delete_entry,
    get_entries,
    get_feedback_work_ids,
    upsert_entry,
)
from ._settings import get_settings, set_settings
from ._sync import (
    finish_sync_run,
    get_stats,
    get_sync_runs,
    prune_recommendations,
    save_recommendations,
    start_sync_run,
)
from ._works import (
    _attach_companies,
    _attach_tags,
    _get_or_create_company,
    _get_or_create_tag,
    _recompute_display_rating,
    _resolve_tag_ids,
    _title_records,
    _work_row,
    create_manual_work,
    find_duplicate_candidates,
    find_work_by_external_ref,
    find_work_by_titles,
    get_work,
    list_tags,
    merge_works,
    save_work_payload,
    search_works,
)

__all__ = [
    "ENTRY_STATUSES",
    "FEEDBACK_KINDS",
    "add_feedback",
    "create_manual_work",
    "delete_entry",
    "find_duplicate_candidates",
    "find_work_by_external_ref",
    "find_work_by_titles",
    "finish_sync_run",
    "get_entries",
    "get_feedback_work_ids",
    "get_settings",
    "get_stats",
    "get_sync_runs",
    "get_work",
    "list_tags",
    "merge_works",
    "prune_recommendations",
    "save_recommendations",
    "save_work_payload",
    "search_works",
    "set_settings",
    "start_sync_run",
    "upsert_entry",
    "canonical_lookup",
    "canonical_lookup_keys",
    "json_dumps",
    "json_loads",
    "normalize_policy",
    "normalize_text",
    "now_iso",
    "parse_year",
    "sql_clause",
    "unique_preserving_order",
    "_attach_companies",
    "_attach_tags",
    "_get_or_create_company",
    "_get_or_create_tag",
    "_recompute_display_rating",
    "_resolve_tag_ids",
    "_title_records",
    "_work_row",
]
