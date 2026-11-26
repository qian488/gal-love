"""NSFW visibility policy shared by search and recommendation.

Three levels keep the catalogue usable without silently hiding content:

``off``    only all-ages works (the historical default)
``story``  all-ages works plus adult works that are not tagged ``Nukige``
``all``    everything

``story`` exists because the VNDB catalogue is dominated by adult titles; the
plain boolean flag used to drop story-driven 18+ works together with nukige.
"""

from __future__ import annotations

from typing import Any

POLICIES = ("off", "story", "all")
NUKIGE_TAG = "Nukige"

_TRUE_WORDS = {"all", "on", "true", "1", "yes", "include"}
_STORY_WORDS = {"story", "story_only", "non_nukige", "non-nukige"}


def normalize_policy(value: Any) -> str:
    """Coerce any stored/legacy value into one of :data:`POLICIES`."""
    if isinstance(value, bool):
        return "all" if value else "off"
    text = str(value or "").strip().casefold()
    if text in _TRUE_WORDS:
        return "all"
    if text in _STORY_WORDS:
        return "story"
    return "off"


def sql_clause(policy: str, *, work_alias: str = "w") -> str | None:
    """Return a WHERE fragment for the policy, or ``None`` when unrestricted."""
    level = normalize_policy(policy)
    if level == "all":
        return None
    if level == "off":
        return f"{work_alias}.nsfw = 0"
    return (
        f"({work_alias}.nsfw = 0 OR NOT EXISTS ("
        f"SELECT 1 FROM work_tags nwt JOIN tags ntg ON ntg.id = nwt.tag_id "
        f"WHERE nwt.work_id = {work_alias}.id AND LOWER(ntg.name) = '{NUKIGE_TAG.casefold()}'))"
    )


def allows(policy: str, *, nsfw: bool, is_nukige: bool = False) -> bool:
    """Whether a single work passes the policy."""
    level = normalize_policy(policy)
    if level == "all":
        return True
    if not nsfw:
        return True
    return level == "story" and not is_nukige
