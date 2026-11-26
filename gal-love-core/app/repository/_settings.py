"""Settings persistence helpers."""

from __future__ import annotations

import sqlite3
from typing import Any

from ..normalize import json_dumps, json_loads
from ..nsfw import normalize_policy


def get_settings(conn: sqlite3.Connection) -> dict[str, Any]:
    defaults: dict[str, Any] = {
        "nsfw_policy": "off",
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

    # ``nsfw_policy`` is the single source of truth; ``include_nsfw`` stays as a
    # derived read-only field for older clients.
    policy = normalize_policy(defaults.get("nsfw_policy", defaults.get("include_nsfw")))
    defaults["nsfw_policy"] = policy
    defaults["include_nsfw"] = policy == "all"

    # Same for the home profile switch: ``home_profile_sources`` wins and
    # ``quiz_merge_home`` is derived, so the two can never disagree.
    sources = defaults.get("home_profile_sources")
    if not isinstance(sources, list) or not sources:
        sources = None if defaults.get("quiz_merge_home", True) else ["library"]
    defaults["home_profile_sources"] = sources
    defaults["quiz_merge_home"] = sources != ["library"]
    return defaults


def set_settings(conn: sqlite3.Connection, values: dict[str, Any]) -> dict[str, Any]:
    payload = dict(values)
    if "nsfw_policy" in payload:
        payload.pop("include_nsfw", None)
        payload["nsfw_policy"] = normalize_policy(payload["nsfw_policy"])
    elif "include_nsfw" in payload:
        payload["nsfw_policy"] = normalize_policy(payload.pop("include_nsfw"))

    if "home_profile_sources" in payload or "quiz_merge_home" in payload:
        if "home_profile_sources" in payload:
            sources = payload["home_profile_sources"] or None
            payload["home_profile_sources"] = sources
            payload["quiz_merge_home"] = sources != ["library"]
        else:
            payload["home_profile_sources"] = None if payload["quiz_merge_home"] else ["library"]

    for key, value in payload.items():
        conn.execute(
            "INSERT INTO settings(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, json_dumps(value)),
        )
    conn.commit()
    return get_settings(conn)

