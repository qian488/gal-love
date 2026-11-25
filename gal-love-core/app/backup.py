"""Consistent SQLite backups using the online backup API.

Backups live in a ``backups`` directory next to the database.  Restoring is
restricted to files inside that directory and always takes a safety backup of
the current database first.
"""

from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .normalize import now_iso

_SQLITE_HEADER = b"SQLite format 3\x00"


def backup_dir(db_path: Path) -> Path:
    """Return the ``data/backups`` directory for a database file."""
    return Path(db_path).resolve().parent / "backups"


def _is_sqlite_file(path: Path) -> bool:
    try:
        if not path.is_file() or path.stat().st_size < 16:
            return False
        with path.open("rb") as handle:
            return handle.read(16) == _SQLITE_HEADER
    except OSError:
        return False


def create_backup(db_path: Path, output_dir: Path | None = None) -> dict:
    """Create a timestamped, transaction-consistent backup of ``db_path``."""
    source = Path(db_path)
    if not source.is_file():
        raise ValueError(f"数据库文件不存在: {source}")
    target_dir = Path(output_dir) if output_dir is not None else backup_dir(source)
    target_dir.mkdir(parents=True, exist_ok=True)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    filename = f"{source.stem}_{stamp}_{uuid.uuid4().hex[:6]}.db"
    target = target_dir / filename
    created_at = now_iso()

    src = sqlite3.connect(str(source))
    try:
        dst = sqlite3.connect(str(target))
        try:
            src.backup(dst)
        finally:
            dst.close()
    except sqlite3.Error as exc:
        target.unlink(missing_ok=True)
        raise ValueError(f"创建备份失败: {exc}") from exc
    finally:
        src.close()

    return {
        "filename": filename,
        "path": str(target),
        "size_bytes": target.stat().st_size,
        "created_at": created_at,
    }


def list_backups(db_path: Path) -> list[dict]:
    """List valid SQLite backups, newest first."""
    directory = backup_dir(db_path)
    if not directory.is_dir():
        return []
    items: list[dict] = []
    for path in directory.glob("*.db"):
        if not _is_sqlite_file(path):
            continue
        stat = path.stat()
        items.append(
            {
                "filename": path.name,
                "path": str(path),
                "size_bytes": stat.st_size,
                "created_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
                .replace(microsecond=0)
                .isoformat(),
            }
        )
    items.sort(key=lambda item: item["created_at"], reverse=True)
    return items


def restore_backup(db_path: Path, backup_path: Path) -> dict:
    """Restore a backup into ``db_path`` after saving the current database."""
    target = Path(db_path)
    source = Path(backup_path)
    allowed = backup_dir(target)

    resolved_source = source.resolve()
    resolved_allowed = allowed.resolve()
    if (
        resolved_source.parent != resolved_allowed
        and resolved_allowed not in resolved_source.parents
    ):
        raise ValueError(f"备份文件必须位于 backups 目录内: {allowed}")
    if not source.is_file():
        raise ValueError(f"备份文件不存在: {source}")
    if not _is_sqlite_file(source):
        raise ValueError("备份文件不是有效的 SQLite 数据库文件")
    if not target.parent.is_dir():
        raise ValueError(f"目标目录不存在: {target.parent}")

    safety_backup = create_backup(target)

    src = sqlite3.connect(str(source))
    try:
        dst = sqlite3.connect(str(target))
        try:
            src.backup(dst)
        finally:
            dst.close()
    except sqlite3.Error as exc:
        raise ValueError(f"恢复备份失败: {exc}") from exc
    finally:
        src.close()

    return {
        "ok": True,
        "db_path": str(target),
        "backup_path": str(source),
        "filename": source.name,
        "size_bytes": target.stat().st_size,
        "auto_backup": safety_backup,
    }
