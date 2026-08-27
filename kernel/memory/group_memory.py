"""Memória Histórica de Grupos — Armazenamento persistente (SQLite) e BM25 por canal.

Arquitetura Híbrida:
- Recente: últimas N mensagens do grupo para contexto imediato.
- Histórico: banco de dados completo de mensagens com busca BM25 e decaimento por recência.
- Isolamento estrito por `(platform, channel_id)`.
- Não mistura mensagens de alunos com a base de Knowledge RAG oficial.
"""

from __future__ import annotations

import json
import logging
import math
import re
import sqlite3
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from rank_bm25 import BM25Okapi

log = logging.getLogger("kernelbots.memory.group_memory")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS group_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    platform TEXT NOT NULL,
    channel_id TEXT NOT NULL,
    message_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    sender_name TEXT NOT NULL DEFAULT '',
    timestamp TEXT NOT NULL,
    content TEXT NOT NULL,
    reply_to TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    UNIQUE(platform, channel_id, message_id)
);

CREATE INDEX IF NOT EXISTS idx_group_msgs_chan_ts ON group_messages(platform, channel_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_group_msgs_chan_msg ON group_messages(platform, channel_id, message_id);

CREATE TABLE IF NOT EXISTS group_profiles (
    platform TEXT NOT NULL,
    channel_id TEXT NOT NULL,
    profile_json TEXT NOT NULL DEFAULT '{}',
    updated_at TEXT NOT NULL,
    message_count_at_update INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (platform, channel_id)
);

CREATE TABLE IF NOT EXISTS group_states (
    platform TEXT NOT NULL,
    channel_id TEXT NOT NULL,
    introduction_sent INTEGER NOT NULL DEFAULT 0,
    introduction_sent_at TEXT,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (platform, channel_id)
);
"""


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _tokenize(text: str) -> list[str]:
    return re.findall(r"\w+", text.lower())


@dataclass(frozen=True)
class GroupMessage:
    id: int
    platform: str
    channel_id: str
    message_id: str
    user_id: str
    sender_name: str
    timestamp: str
    content: str
    reply_to: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = ""


@dataclass(frozen=True)
class HistoricalSearchResult:
    message_id: str
    sender_name: str
    user_id: str
    content: str
    timestamp: str
    bm25_score: float
    recency_factor: float
    final_score: float


class GroupMemoryStore:
    """Armazenamento persistente de histórico de grupos e índice BM25 isolado por canal."""

    def __init__(self, db_path: Path | str) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._bm25_cache: dict[str, tuple[BM25Okapi, list[dict[str, Any]]]] = {}
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _init_schema(self) -> None:
        with self._lock:
            with self._connect() as conn:
                conn.executescript(_SCHEMA)
                conn.commit()

    def _cache_key(self, platform: str, channel_id: str) -> str:
        return f"{platform}:{channel_id}"

    def record_message(
        self,
        *,
        platform: str,
        channel_id: str,
        message_id: str,
        user_id: str,
        sender_name: str = "",
        timestamp: str | None = None,
        content: str,
        reply_to: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> GroupMessage:
        """Grava uma mensagem no histórico persistente do grupo."""
        if not platform or not channel_id or not message_id:
            raise ValueError("platform, channel_id e message_id são obrigatórios")
        meta = dict(metadata or {})
        msg_type = str(meta.get("message_type") or "text")
        status = str(meta.get("message_status") or "active")
        body = (content or "").strip()
        if not body and msg_type not in ("media", "deleted"):
            raise ValueError("content é obrigatório (exceto mídia/apagada com metadata)")
        if not body and msg_type == "media":
            body = "[mídia]"
        if not body and status == "deleted":
            body = "[mensagem apagada]"

        ts = (timestamp or "").strip() or _utc_now_iso()
        now = _utc_now_iso()
        meta_json = json.dumps(meta, ensure_ascii=False, default=str)
        name = (sender_name or "").strip()

        with self._lock:
            with self._connect() as conn:
                cursor = conn.execute(
                    """
                    INSERT INTO group_messages (
                        platform, channel_id, message_id, user_id, sender_name,
                        timestamp, content, reply_to, metadata_json, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(platform, channel_id, message_id) DO UPDATE SET
                        content = excluded.content,
                        sender_name = excluded.sender_name,
                        metadata_json = excluded.metadata_json
                    """,
                    (
                        platform,
                        channel_id,
                        message_id,
                        user_id,
                        name,
                        ts,
                        body,
                        reply_to,
                        meta_json,
                        now,
                    ),
                )
                row_id = cursor.lastrowid
                conn.commit()

            # Invalida o cache BM25 para este grupo
            self._bm25_cache.pop(self._cache_key(platform, channel_id), None)

            return GroupMessage(
                id=int(row_id or 0),
                platform=platform,
                channel_id=channel_id,
                message_id=message_id,
                user_id=user_id,
                sender_name=name,
                timestamp=ts,
                content=body,
                reply_to=reply_to,
                metadata=meta,
                created_at=now,
            )

    def record_messages_batch(self, messages: list[dict[str, Any]]) -> int:
        """Insere múltiplas mensagens em batch."""
        if not messages:
            return 0
        now = _utc_now_iso()
        inserted = 0
        touched_channels: set[str] = set()

        with self._lock:
            with self._connect() as conn:
                for m in messages:
                    plat = str(m.get("platform") or "").strip()
                    chan = str(m.get("channel_id") or "").strip()
                    mid = str(m.get("message_id") or "").strip()
                    meta = dict(m.get("metadata") or {})
                    msg_type = str(meta.get("message_type") or "text")
                    status = str(meta.get("message_status") or "active")
                    content = str(m.get("content") or "").strip()
                    if not content and msg_type == "media":
                        content = "[mídia]"
                    if not content and status == "deleted":
                        content = "[mensagem apagada]"
                    if not plat or not chan or not mid or not content:
                        continue
                    uid = str(m.get("user_id") or chan).strip()
                    name = str(m.get("sender_name") or "").strip()
                    ts = str(m.get("timestamp") or now).strip()
                    reply = m.get("reply_to")
                    meta_json = json.dumps(meta, ensure_ascii=False, default=str)

                    conn.execute(
                        """
                        INSERT INTO group_messages (
                            platform, channel_id, message_id, user_id, sender_name,
                            timestamp, content, reply_to, metadata_json, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(platform, channel_id, message_id) DO UPDATE SET
                            content = excluded.content,
                            sender_name = excluded.sender_name,
                            metadata_json = excluded.metadata_json
                        """,
                        (plat, chan, mid, uid, name, ts, content, reply, meta_json, now),
                    )
                    inserted += 1
                    touched_channels.add(self._cache_key(plat, chan))
                conn.commit()

            for ck in touched_channels:
                self._bm25_cache.pop(ck, None)

        return inserted

    def get_recent_messages(
        self,
        platform: str,
        channel_id: str,
        limit: int = 20,
    ) -> list[GroupMessage]:
        """Obtém as mensagens mais recentes (ordem cronológica mais antiga -> mais recente)."""
        limit = max(1, min(int(limit), 100))
        with self._lock:
            with self._connect() as conn:
                rows = conn.execute(
                    """
                    SELECT id, platform, channel_id, message_id, user_id, sender_name,
                           timestamp, content, reply_to, metadata_json, created_at
                    FROM group_messages
                    WHERE platform = ? AND channel_id = ?
                    ORDER BY id DESC
                    LIMIT ?
                    """,
                    (platform, channel_id, limit),
                ).fetchall()

        out = []
        for r in reversed(rows):
            try:
                meta = json.loads(r["metadata_json"] or "{}")
            except Exception:
                meta = {}
            out.append(
                GroupMessage(
                    id=int(r["id"]),
                    platform=r["platform"],
                    channel_id=r["channel_id"],
                    message_id=r["message_id"],
                    user_id=r["user_id"],
                    sender_name=r["sender_name"],
                    timestamp=r["timestamp"],
                    content=r["content"],
                    reply_to=r["reply_to"],
                    metadata=meta,
                    created_at=r["created_at"],
                )
            )
        return out

    def _get_bm25_index(
        self,
        platform: str,
        channel_id: str,
    ) -> tuple[BM25Okapi | None, list[dict[str, Any]]]:
        ck = self._cache_key(platform, channel_id)
        if ck in self._bm25_cache:
            return self._bm25_cache[ck]

        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, message_id, user_id, sender_name, timestamp, content,
                       metadata_json, created_at
                FROM group_messages
                WHERE platform = ? AND channel_id = ?
                ORDER BY id ASC
                """,
                (platform, channel_id),
            ).fetchall()

        docs: list[dict[str, Any]] = []
        for r in rows:
            try:
                meta = json.loads(r["metadata_json"] or "{}")
            except Exception:
                meta = {}
            if str(meta.get("message_status") or "") == "deleted":
                continue
            d = dict(r)
            d["metadata"] = meta
            docs.append(d)
        if not docs:
            return None, []

        tokenized = [_tokenize(d["content"]) for d in docs]
        bm25 = BM25Okapi(tokenized) if any(tokenized) else None
        res = (bm25, docs)
        self._bm25_cache[ck] = res
        return res

    def search_historical(
        self,
        platform: str,
        channel_id: str,
        query: str,
        *,
        top_k: int = 5,
        recency_weight: float = 0.3,
        max_age_days: int = 180,
    ) -> list[HistoricalSearchResult]:
        """Recupera mensagens históricas do grupo com BM25 + fator de recência.

        Fórmula determinística de scoring:
            recency_factor = max(0.0, 1.0 - (age_seconds / (max_age_days * 86400)))
            final_score = bm25_score * (1.0 + recency_weight * recency_factor)
        """
        clean_query = query.strip()
        tokens = _tokenize(clean_query)
        if not tokens:
            return []

        with self._lock:
            bm25, docs = self._get_bm25_index(platform, channel_id)
            if bm25 is None or not docs:
                return []

            raw_scores = bm25.get_scores(tokens)
            now_ts = time.time()
            max_age_sec = max(1.0, float(max_age_days) * 86400.0)

            results: list[HistoricalSearchResult] = []
            for i, score in enumerate(raw_scores):
                bm25_val = float(score)
                doc = docs[i]
                doc_tokens = set(_tokenize(doc["content"]))
                has_token_match = any(t in doc_tokens for t in tokens)

                if bm25_val <= 0.0 and not has_token_match:
                    continue

                effective_score = max(bm25_val, 0.1 if has_token_match else 0.0)
                if effective_score <= 0.0:
                    continue
                ts_str = doc.get("timestamp") or doc.get("created_at") or ""
                doc_ts = now_ts
                try:
                    dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                    doc_ts = dt.timestamp()
                except Exception:
                    pass

                age_sec = max(0.0, now_ts - doc_ts)
                recency_factor = max(0.0, min(1.0, 1.0 - (age_sec / max_age_sec)))
                final_score = effective_score * (1.0 + recency_weight * recency_factor)

                results.append(
                    HistoricalSearchResult(
                        message_id=str(doc["message_id"]),
                        sender_name=str(doc["sender_name"] or "membro"),
                        user_id=str(doc["user_id"]),
                        content=str(doc["content"]),
                        timestamp=str(doc["timestamp"]),
                        bm25_score=effective_score,
                        recency_factor=recency_factor,
                        final_score=final_score,
                    )
                )

            results.sort(key=lambda r: r.final_score, reverse=True)
            return results[: max(1, min(top_k, 20))]

    def get_group_profile(self, platform: str, channel_id: str) -> dict[str, Any] | None:
        """Lê o Group Profile persistido."""
        with self._lock:
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT profile_json FROM group_profiles WHERE platform = ? AND channel_id = ?",
                    (platform, channel_id),
                ).fetchone()
                if row is None:
                    return None
                try:
                    return json.loads(row["profile_json"])
                except Exception:
                    return None

    def update_group_profile(
        self,
        platform: str,
        channel_id: str,
        profile: dict[str, Any],
        message_count: int = 0,
    ) -> None:
        """Salva ou atualiza o Group Profile."""
        now = _utc_now_iso()
        p_json = json.dumps(profile, ensure_ascii=False, default=str)
        with self._lock:
            with self._connect() as conn:
                conn.execute(
                    """
                    INSERT INTO group_profiles (platform, channel_id, profile_json, updated_at, message_count_at_update)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(platform, channel_id) DO UPDATE SET
                        profile_json = excluded.profile_json,
                        updated_at = excluded.updated_at,
                        message_count_at_update = excluded.message_count_at_update
                    """,
                    (platform, channel_id, p_json, now, message_count),
                )
                conn.commit()

    def get_group_state(self, platform: str, channel_id: str) -> dict[str, Any]:
        """Obtém o estado de apresentação do grupo."""
        with self._lock:
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT introduction_sent, introduction_sent_at, updated_at FROM group_states WHERE platform = ? AND channel_id = ?",
                    (platform, channel_id),
                ).fetchone()
                if row is None:
                    return {
                        "introduction_sent": False,
                        "introduction_sent_at": None,
                        "updated_at": None,
                    }
                return {
                    "introduction_sent": bool(row["introduction_sent"]),
                    "introduction_sent_at": row["introduction_sent_at"],
                    "updated_at": row["updated_at"],
                }

    def set_group_state(
        self,
        platform: str,
        channel_id: str,
        introduction_sent: bool,
    ) -> None:
        """Atualiza o estado de apresentação do grupo (sobrevive a restarts e /reset)."""
        now = _utc_now_iso()
        with self._lock:
            with self._connect() as conn:
                existing = conn.execute(
                    "SELECT introduction_sent_at FROM group_states WHERE platform = ? AND channel_id = ?",
                    (platform, channel_id),
                ).fetchone()
                intro_at = (
                    existing["introduction_sent_at"]
                    if existing and existing["introduction_sent_at"]
                    else (now if introduction_sent else None)
                )
                conn.execute(
                    """
                    INSERT INTO group_states (platform, channel_id, introduction_sent, introduction_sent_at, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(platform, channel_id) DO UPDATE SET
                        introduction_sent = excluded.introduction_sent,
                        introduction_sent_at = excluded.introduction_sent_at,
                        updated_at = excluded.updated_at
                    """,
                    (platform, channel_id, 1 if introduction_sent else 0, intro_at, now),
                )
                conn.commit()

    def try_claim_introduction(self, platform: str, channel_id: str) -> bool:
        """Reserva atomicamente o direito de enviar apresentação (introduction_sent 0→1).

        Retorna True apenas para o primeiro caller concorrente. ``/reset`` não repõe
        este estado — apresentação é por grupo, não por sessão de transcript.
        """
        now = _utc_now_iso()
        with self._lock:
            with self._connect() as conn:
                conn.execute(
                    """
                    INSERT INTO group_states (platform, channel_id, introduction_sent, introduction_sent_at, updated_at)
                    VALUES (?, ?, 0, NULL, ?)
                    ON CONFLICT(platform, channel_id) DO NOTHING
                    """,
                    (platform, channel_id, now),
                )
                cur = conn.execute(
                    """
                    UPDATE group_states
                    SET introduction_sent = 1, introduction_sent_at = ?, updated_at = ?
                    WHERE platform = ? AND channel_id = ? AND introduction_sent = 0
                    """,
                    (now, now, platform, channel_id),
                )
                conn.commit()
                return int(cur.rowcount or 0) == 1

    def delete_group_memory(self, platform: str, channel_id: str) -> dict[str, Any]:
        """Exclusão isolada de dados de um grupo específico (mantém RAG e outros grupos intactos)."""
        with self._lock:
            with self._connect() as conn:
                c1 = conn.execute(
                    "DELETE FROM group_messages WHERE platform = ? AND channel_id = ?",
                    (platform, channel_id),
                ).rowcount
                c2 = conn.execute(
                    "DELETE FROM group_profiles WHERE platform = ? AND channel_id = ?",
                    (platform, channel_id),
                ).rowcount
                conn.commit()

            self._bm25_cache.pop(self._cache_key(platform, channel_id), None)
            log.info("Group memory deleted: %s:%s (messages=%s, profiles=%s)", platform, channel_id, c1, c2)
            return {"deleted_messages": c1, "deleted_profiles": c2, "platform": platform, "channel_id": channel_id}

    def purge_older_than(
        self,
        retention_days: int,
        *,
        platform: str | None = None,
        channel_id: str | None = None,
    ) -> dict[str, Any]:
        """Remove mensagens mais antigas que retention_days (manutenção)."""
        days = max(1, int(retention_days))
        cutoff = datetime.now(timezone.utc).timestamp() - (days * 86400.0)
        deleted = 0
        touched: set[str] = set()

        with self._lock:
            with self._connect() as conn:
                if platform and channel_id:
                    rows = conn.execute(
                        """
                        SELECT id, platform, channel_id, timestamp, created_at
                        FROM group_messages
                        WHERE platform = ? AND channel_id = ?
                        """,
                        (platform, channel_id),
                    ).fetchall()
                else:
                    rows = conn.execute(
                        "SELECT id, platform, channel_id, timestamp, created_at FROM group_messages"
                    ).fetchall()

                for r in rows:
                    ts_str = r["timestamp"] or r["created_at"] or ""
                    try:
                        dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                        ts_val = dt.timestamp()
                    except Exception:
                        continue
                    if ts_val < cutoff:
                        conn.execute("DELETE FROM group_messages WHERE id = ?", (r["id"],))
                        deleted += 1
                        touched.add(self._cache_key(r["platform"], r["channel_id"]))
                conn.commit()

            for ck in touched:
                self._bm25_cache.pop(ck, None)

        return {"deleted_messages": deleted, "retention_days": days, "groups_touched": len(touched)}

    def count_messages(self, platform: str, channel_id: str) -> int:
        with self._lock:
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT COUNT(*) AS c FROM group_messages WHERE platform = ? AND channel_id = ?",
                    (platform, channel_id),
                ).fetchone()
                return int(row["c"] or 0) if row else 0

    def get_stats(self, platform: str | None = None, channel_id: str | None = None) -> dict[str, Any]:
        """Estatísticas do armazenamento para o painel de Ops."""
        with self._lock:
            with self._connect() as conn:
                if platform and channel_id:
                    total_msgs = conn.execute(
                        "SELECT COUNT(*) as c FROM group_messages WHERE platform = ? AND channel_id = ?",
                        (platform, channel_id),
                    ).fetchone()["c"]
                    earliest = conn.execute(
                        "SELECT MIN(created_at) as m FROM group_messages WHERE platform = ? AND channel_id = ?",
                        (platform, channel_id),
                    ).fetchone()["m"]
                    latest = conn.execute(
                        "SELECT MAX(created_at) as m FROM group_messages WHERE platform = ? AND channel_id = ?",
                        (platform, channel_id),
                    ).fetchone()["m"]
                    has_profile = conn.execute(
                        "SELECT 1 FROM group_profiles WHERE platform = ? AND channel_id = ?",
                        (platform, channel_id),
                    ).fetchone() is not None
                    return {
                        "platform": platform,
                        "channel_id": channel_id,
                        "total_messages": int(total_msgs),
                        "period_start": earliest,
                        "period_end": latest,
                        "has_profile": has_profile,
                    }

                total_groups = conn.execute(
                    "SELECT COUNT(DISTINCT channel_id) as c FROM group_messages"
                ).fetchone()["c"]
                total_msgs = conn.execute(
                    "SELECT COUNT(*) as c FROM group_messages"
                ).fetchone()["c"]
                groups_list = conn.execute(
                    """
                    SELECT platform, channel_id, COUNT(*) as msg_count,
                           MIN(created_at) as first_seen, MAX(created_at) as last_seen
                    FROM group_messages
                    GROUP BY platform, channel_id
                    ORDER BY msg_count DESC
                    LIMIT 50
                    """
                ).fetchall()

                return {
                    "total_groups": int(total_groups),
                    "total_messages": int(total_msgs),
                    "groups": [
                        {
                            "platform": r["platform"],
                            "channel_id": r["channel_id"],
                            "message_count": int(r["msg_count"]),
                            "first_seen": r["first_seen"],
                            "last_seen": r["last_seen"],
                        }
                        for r in groups_list
                    ],
                }
