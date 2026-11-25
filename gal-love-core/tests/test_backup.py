from __future__ import annotations

from pathlib import Path

import pytest

from app.backup import backup_dir, create_backup, list_backups, restore_backup
from app.db import connect
from app.repository import get_work, save_work_payload


def test_backup_dir_is_next_to_database(db_path: Path):
    assert backup_dir(db_path) == db_path.parent / "backups"


def test_create_backup_custom_output_dir(db_path: Path, tmp_path: Path):
    output = tmp_path / "custom_backups"
    info = create_backup(db_path, output)
    assert Path(info["path"]).parent == output
    assert Path(info["path"]).is_file()
    assert info["size_bytes"] > 0


def test_backup_and_restore_roundtrip(db_path: Path):
    conn = connect(db_path)
    work_id = save_work_payload(conn, {"source": "manual", "title": "Before Restore"})
    conn.close()

    info = create_backup(db_path)
    assert info["filename"].endswith(".db")
    assert info["created_at"]
    assert Path(info["path"]).read_bytes()[:16] == b"SQLite format 3\x00"
    backups = list_backups(db_path)
    assert len(backups) == 1
    assert backups[0]["filename"] == info["filename"]

    conn = connect(db_path)
    conn.execute("UPDATE works SET title = ? WHERE id = ?", ("After Restore", work_id))
    conn.commit()
    conn.close()

    result = restore_backup(db_path, Path(info["path"]))
    assert result["ok"] is True
    assert result["filename"] == info["filename"]
    assert result["auto_backup"]["filename"] != info["filename"]
    # The original backup plus the automatic safety backup.
    assert len(list_backups(db_path)) == 2

    conn = connect(db_path)
    restored = get_work(conn, work_id)
    conn.close()
    assert restored is not None
    assert restored["title"] == "Before Restore"


def test_restore_rejects_outside_and_invalid_files(db_path: Path, tmp_path: Path):
    conn = connect(db_path)
    conn.close()
    info = create_backup(db_path)

    outside = tmp_path / "outside.db"
    outside.write_bytes(Path(info["path"]).read_bytes())
    with pytest.raises(ValueError, match="backups"):
        restore_backup(db_path, outside)

    invalid = backup_dir(db_path) / "not_sqlite.db"
    invalid.write_text("this is not a database", encoding="utf-8")
    with pytest.raises(ValueError, match="SQLite"):
        restore_backup(db_path, invalid)


def test_list_backups_empty_for_fresh_database(db_path: Path):
    assert list_backups(db_path) == []
