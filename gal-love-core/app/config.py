"""Application configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = BASE_DIR / "data" / "gallove.db"


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    db_path: Path
    vndb_api_base: str = "https://api.vndb.org/kana"
    bangumi_api_base: str = "https://api.bgm.tv"
    bangumi_user_agent: str = os.getenv(
        "GAL_LOVE_BANGUMI_UA",
        "gal-love-personal/0.1 (local personal project)",
    )
    request_timeout: float = 30.0
    vndb_request_interval: float = 1.6
    bangumi_request_interval: float = 0.8
    default_page_size: int = _env_int("GAL_LOVE_PAGE_SIZE", 20)

    @classmethod
    def from_env(cls) -> "Settings":
        db_path = Path(os.getenv("GAL_LOVE_DB", str(DEFAULT_DB_PATH))).expanduser()
        return cls(db_path=db_path)


settings = Settings.from_env()
