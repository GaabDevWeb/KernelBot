"""Utilizadores Ops — sessões registadas + bloqueios persistentes (SQLite)."""

from __future__ import annotations

import sqlite3
import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_SCHEMA = """
CREATE TABLE IF NOT EXISTS user_sessions (
    id TEXT PRIMARY KEY,
    platform TEXT NOT NULL,
    user_id TEXT NOT NULL,
    channel_id TEXT NOT NULL,
    session_id TEXT NOT NULL DEFAULT '',
    memory_key TEXT NOT NULL,
    first_seen TEXT NOT NULL,
    last_seen TEXT NOT NULL,
    message_count INTEGER NOT NULL DEFAULT 0
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_user_sessions_identity
  ON user_sessions(platform, user_id, channel_id, session_id);
CREATE INDEX IF NOT EXISTS idx_user_sessions_last ON user_sessions(last_seen DESC);
CREATE INDEX IF NOT EXISTS idx_user_sessions_user ON user_sessions(platform, user_id);

CREATE TABLE IF NOT EXISTS user_blocks (
    id TEXT PRIMARY KEY,
    platform TEXT NOT NULL,
    user_id TEXT NOT NULL,
    reason TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    created_by TEXT NOT NULL DEFAULT 'ops',
    active INTEGER NOT NULL DEFAULT 1,
    lifted_at TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_user_blocks_active
  ON user_blocks(platform, user_id) WHERE active = 1;
CREATE INDEX IF NOT EXISTS idx_user_blocks_list ON user_blocks(active, created_at DESC);
"""


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _new_id(prefix: str = "") -> str:
    return f"{prefix}{uuid.uuid4().hex[:12]}"


@dataclass(frozen=True)
class UserSession:
    id: str
    platform: str
    user_id: str
    channel_id: str
    session_id: str
    memory_key: str
    first_seen: str
    last_seen: str
    message_count: int
    blocked: bool = False


@dataclass(frozen=True)
class UserBlock:
    id: str
    platform: str
    user_id: str
    reason: str
    created_at: str
    created_by: str
    active: bool
    lifted_at: str | None


class UsersStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        with self._connect() as conn:
            conn.executescript(_SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def touch_session(
        self,
        *,
        platform: str,
        user_id: str,
        channel_id: str,
        session_id: str | None,
        memory_key: str,
        increment_messages: int = 0,
    ) -> str:
        plat = (platform or "").strip() or "unknown"
        uid = (user_id or "").strip() or "_anon"
        ch = (channel_id or "").strip() or "_"
        sid = (session_id or "").strip()
        now = _utc_now()
        with self._lock, self._connect() as conn:
            row = conn.execute(
                """
                SELECT id, message_count FROM user_sessions
                WHERE platform=? AND user_id=? AND channel_id=? AND session_id=?
                """,
                (plat, uid, ch, sid),
            ).fetchone()
            if row:
                conn.execute(
                    """
                    UPDATE user_sessions
                    SET last_seen=?, message_count=message_count+?, memory_key=?
                    WHERE id=?
                    """,
                    (now, max(0, int(increment_messages)), memory_key, row["id"]),
                )
                conn.commit()
                return str(row["id"])
            sid_row = _new_id("ses_")
            conn.execute(
                """
                INSERT INTO user_sessions
                (id, platform, user_id, channel_id, session_id, memory_key,
                 first_seen, last_seen, message_count)
                VALUES (?,?,?,?,?,?,?,?,?)
                """,
                (
                    sid_row,
                    plat,
                    uid,
                    ch,
                    sid,
                    memory_key,
                    now,
                    now,
                    max(0, int(increment_messages)),
                ),
            )
            conn.commit()
            return sid_row

    def list_sessions(self, *, limit: int = 200, q: str = "") -> list[UserSession]:
        limit = max(1, min(int(limit), 500))
        needle = (q or "").strip()
        with self._lock, self._connect() as conn:
            if needle:
                like = f"%{needle}%"
                rows = conn.execute(
                    """
                    SELECT s.*,
                      EXISTS(
                        SELECT 1 FROM user_blocks b
                        WHERE b.platform = s.platform AND b.user_id = s.user_id AND b.active = 1
                      ) AS blocked
                    FROM user_sessions s
                    WHERE s.user_id LIKE ? OR s.platform LIKE ? OR s.channel_id LIKE ?
                       OR s.memory_key LIKE ?
                    ORDER BY s.last_seen DESC
                    LIMIT ?
                    """,
                    (like, like, like, like, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT s.*,
                      EXISTS(
                        SELECT 1 FROM user_blocks b
                        WHERE b.platform = s.platform AND b.user_id = s.user_id AND b.active = 1
                      ) AS blocked
                    FROM user_sessions s
                    ORDER BY s.last_seen DESC
                    LIMIT ?
                    """,
                    (limit,),
                ).fetchall()
        return [self._row_session(r) for r in rows]

    def get_session(self, session_row_id: str) -> UserSession | None:
        with self._lock, self._connect() as conn:
            row = conn.execute(
                """
                SELECT s.*,
                  EXISTS(
                    SELECT 1 FROM user_blocks b
                    WHERE b.platform = s.platform AND b.user_id = s.user_id AND b.active = 1
                  ) AS blocked
                FROM user_sessions s WHERE s.id = ?
                """,
                (session_row_id,),
            ).fetchone()
        return self._row_session(row) if row else None

    def get_session_by_key(self, memory_key: str) -> UserSession | None:
        with self._lock, self._connect() as conn:
            row = conn.execute(
                """
                SELECT s.*,
                  EXISTS(
                    SELECT 1 FROM user_blocks b
                    WHERE b.platform = s.platform AND b.user_id = s.user_id AND b.active = 1
                  ) AS blocked
                FROM user_sessions s WHERE s.memory_key = ?
                ORDER BY s.last_seen DESC LIMIT 1
                """,
                (memory_key,),
            ).fetchone()
        return self._row_session(row) if row else None

    def user_stats(self, *, limit: int = 100) -> list[dict[str, Any]]:
        """Agrega por platform+user_id."""
        limit = max(1, min(int(limit), 500))
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                """
                SELECT
                  s.platform,
                  s.user_id,
                  MIN(s.first_seen) AS first_seen,
                  MAX(s.last_seen) AS last_seen,
                  SUM(s.message_count) AS messages,
                  COUNT(*) AS sessions,
                  EXISTS(
                    SELECT 1 FROM user_blocks b
                    WHERE b.platform = s.platform AND b.user_id = s.user_id AND b.active = 1
                  ) AS blocked
                FROM user_sessions s
                GROUP BY s.platform, s.user_id
                ORDER BY messages DESC, last_seen DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]

    def is_blocked(self, platform: str, user_id: str) -> bool:
        plat = (platform or "").strip()
        uid = (user_id or "").strip()
        if not plat or not uid:
            return False
        with self._lock, self._connect() as conn:
            row = conn.execute(
                """
                SELECT 1 FROM user_blocks
                WHERE platform=? AND user_id=? AND active=1
                LIMIT 1
                """,
                (plat, uid),
            ).fetchone()
        return row is not None

    def get_active_block(self, platform: str, user_id: str) -> UserBlock | None:
        with self._lock, self._connect() as conn:
            row = conn.execute(
                """
                SELECT * FROM user_blocks
                WHERE platform=? AND user_id=? AND active=1
                LIMIT 1
                """,
                ((platform or "").strip(), (user_id or "").strip()),
            ).fetchone()
        return self._row_block(row) if row else None

    def block_user(
        self,
        *,
        platform: str,
        user_id: str,
        reason: str = "",
        created_by: str = "ops",
    ) -> str:
        plat = (platform or "").strip()
        uid = (user_id or "").strip()
        if not plat or not uid:
            raise ValueError("platform e user_id obrigatórios")
        # se já activo, actualiza motivo
        existing = self.get_active_block(plat, uid)
        now = _utc_now()
        with self._lock, self._connect() as conn:
            if existing:
                conn.execute(
                    "UPDATE user_blocks SET reason=?, created_by=?, created_at=? WHERE id=?",
                    (reason.strip(), created_by, now, existing.id),
                )
                conn.commit()
                return existing.id
            bid = _new_id("blk_")
            conn.execute(
                """
                INSERT INTO user_blocks
                (id, platform, user_id, reason, created_at, created_by, active)
                VALUES (?,?,?,?,?,?,1)
                """,
                (bid, plat, uid, reason.strip(), now, created_by),
            )
            conn.commit()
            return bid

    def unblock_user(self, *, platform: str, user_id: str) -> bool:
        plat = (platform or "").strip()
        uid = (user_id or "").strip()
        now = _utc_now()
        with self._lock, self._connect() as conn:
            cur = conn.execute(
                """
                UPDATE user_blocks SET active=0, lifted_at=?
                WHERE platform=? AND user_id=? AND active=1
                """,
                (now, plat, uid),
            )
            conn.commit()
            return cur.rowcount > 0

    def list_blocks(self, *, active_only: bool = True, limit: int = 200) -> list[UserBlock]:
        limit = max(1, min(int(limit), 500))
        with self._lock, self._connect() as conn:
            if active_only:
                rows = conn.execute(
                    "SELECT * FROM user_blocks WHERE active=1 ORDER BY created_at DESC LIMIT ?",
                    (limit,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM user_blocks ORDER BY created_at DESC LIMIT ?",
                    (limit,),
                ).fetchall()
        return [self._row_block(r) for r in rows]

    def export_table(self, table: str) -> list[dict[str, Any]]:
        allowed = {"user_sessions", "user_blocks"}
        if table not in allowed:
            raise ValueError("table not allowed")
        with self._lock, self._connect() as conn:
            rows = conn.execute(f"SELECT * FROM {table}").fetchall()  # noqa: S608
        return [dict(r) for r in rows]

    @staticmethod
    def _row_session(row: sqlite3.Row) -> UserSession:
        return UserSession(
            id=row["id"],
            platform=row["platform"],
            user_id=row["user_id"],
            channel_id=row["channel_id"],
            session_id=row["session_id"] or "",
            memory_key=row["memory_key"],
            first_seen=row["first_seen"],
            last_seen=row["last_seen"],
            message_count=int(row["message_count"] or 0),
            blocked=bool(row["blocked"]) if "blocked" in row.keys() else False,
        )

    @staticmethod
    def _row_block(row: sqlite3.Row) -> UserBlock:
        return UserBlock(
            id=row["id"],
            platform=row["platform"],
            user_id=row["user_id"],
            reason=row["reason"] or "",
            created_at=row["created_at"],
            created_by=row["created_by"] or "ops",
            active=bool(row["active"]),
            lifted_at=row["lifted_at"],
        )


_store: UsersStore | None = None


def init_users_store(db_path: Path) -> UsersStore:
    global _store
    _store = UsersStore(db_path)
    return _store


def get_users_store() -> UsersStore | None:
    return _store


def reset_users_store_for_tests() -> None:
    global _store
    _store = None
