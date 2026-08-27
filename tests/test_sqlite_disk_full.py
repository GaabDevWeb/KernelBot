"""Comportamento SQLite quando gravação falha (disk-full modelado)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from kernel.memory.group_memory import GroupMemoryStore


def test_group_memory_write_failure_surfaces(tmp_path: Path) -> None:
    store = GroupMemoryStore(tmp_path / "gm.sqlite3")
    with patch.object(store, "_connect") as mock_connect:
        mock_connect.side_effect = OSError("disk full")
        with pytest.raises(OSError, match="disk full"):
            store.record_message(
                platform="whatsapp",
                channel_id="g1@g.us",
                message_id="x1",
                user_id="u1",
                content="teste",
            )
