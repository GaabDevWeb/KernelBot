"""Backup / restore file-level dos SQLite V1 (Group Memory, Comms, Users)."""

from __future__ import annotations

import shutil
import sqlite3
from pathlib import Path

from kernel.comms.store import CommsStore
from kernel.memory.group_memory import GroupMemoryStore


def _checkpoint_sqlite(path: Path) -> None:
    if not path.is_file():
        return
    with sqlite3.connect(str(path)) as conn:
        conn.execute("PRAGMA wal_checkpoint(FULL)")


def _backup_dir(src_root: Path, dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    for name in ("group_memory.sqlite3", "comms.sqlite3", "users.sqlite3"):
        p = src_root / name
        if p.is_file():
            _checkpoint_sqlite(p)
            shutil.copy2(p, dest / name)
            for suffix in ("-wal", "-shm"):
                extra = src_root / f"{name}{suffix}"
                if extra.is_file():
                    shutil.copy2(extra, dest / f"{name}{suffix}")


def _restore_dir(backup: Path, dest_root: Path) -> None:
    dest_root.mkdir(parents=True, exist_ok=True)
    for p in backup.glob("*.sqlite3"):
        shutil.copy2(p, dest_root / p.name)


def test_backup_restore_preserves_group_memory_and_comms(tmp_path: Path) -> None:
    live = tmp_path / "live"
    live.mkdir()
    backup = tmp_path / "backup"
    restored = tmp_path / "restored"
    restored.mkdir()

    gm = GroupMemoryStore(live / "group_memory.sqlite3")
    gm.record_message(
        platform="whatsapp",
        channel_id="group-a@g.us",
        message_id="bk-1",
        user_id="u1",
        content="Segredo backup ALPHA",
    )
    gm.record_message(
        platform="whatsapp",
        channel_id="group-b@g.us",
        message_id="bk-2",
        user_id="u2",
        content="Mensagem grupo B",
    )

    comms = CommsStore(live / "comms.sqlite3")
    comms.seed_default_templates()
    cid = comms.create_campaign(
        title="Campanha backup",
        body="Corpo",
        channel="whatsapp",
        dest_type="user",
        dest_ref="5511999@s.whatsapp.net",
        status="scheduled",
    )

    _backup_dir(live, backup)

    # corrupção controlada
    (live / "group_memory.sqlite3").write_bytes(b"corrupt")
    (live / "comms.sqlite3").unlink(missing_ok=True)

    _restore_dir(backup, restored)

    gm2 = GroupMemoryStore(restored / "group_memory.sqlite3")
    assert gm2.count_messages("whatsapp", "group-a@g.us") == 1
    assert gm2.search_historical("whatsapp", "group-b@g.us", "grupo B")
    assert gm2.search_historical("whatsapp", "group-a@g.us", "ALPHA")[0].message_id == "bk-1"
    # isolamento preservado
    assert gm2.search_historical("whatsapp", "group-b@g.us", "Segredo backup ALPHA") == []

    comms2 = CommsStore(restored / "comms.sqlite3")
    camp = comms2.get_campaign(cid)
    assert camp is not None
    assert camp.title == "Campanha backup"
    assert camp.status == "scheduled"
