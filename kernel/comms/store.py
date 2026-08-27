"""Comunicações — store SQLite (campanhas, templates, públicos, anexos, entregas)."""

from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_SCHEMA = """
CREATE TABLE IF NOT EXISTS comm_templates (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    body TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS comm_audiences (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS comm_audience_members (
    id TEXT PRIMARY KEY,
    audience_id TEXT NOT NULL,
    member_type TEXT NOT NULL,
    member_ref TEXT NOT NULL,
    label TEXT NOT NULL DEFAULT '',
    FOREIGN KEY (audience_id) REFERENCES comm_audiences(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_comm_aud_members ON comm_audience_members(audience_id);

CREATE TABLE IF NOT EXISTS comm_attachments (
    id TEXT PRIMARY KEY,
    sha256 TEXT NOT NULL UNIQUE,
    filename TEXT NOT NULL,
    content_type TEXT NOT NULL,
    size_bytes INTEGER NOT NULL,
    storage_path TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS comm_campaigns (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    channel TEXT NOT NULL,
    dest_type TEXT NOT NULL,
    dest_ref TEXT NOT NULL,
    status TEXT NOT NULL,
    scheduled_at TEXT,
    template_id TEXT,
    is_test INTEGER NOT NULL DEFAULT 0,
    preview_text TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    created_by TEXT NOT NULL DEFAULT 'ops'
);

CREATE TABLE IF NOT EXISTS comm_campaign_attachments (
    campaign_id TEXT NOT NULL,
    attachment_id TEXT NOT NULL,
    PRIMARY KEY (campaign_id, attachment_id),
    FOREIGN KEY (campaign_id) REFERENCES comm_campaigns(id) ON DELETE CASCADE,
    FOREIGN KEY (attachment_id) REFERENCES comm_attachments(id)
);

CREATE TABLE IF NOT EXISTS comm_deliveries (
    id TEXT PRIMARY KEY,
    campaign_id TEXT NOT NULL,
    dest_ref TEXT NOT NULL,
    dest_type TEXT NOT NULL,
    status TEXT NOT NULL,
    error TEXT NOT NULL DEFAULT '',
    latency_ms REAL,
    adapter_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    sent_at TEXT,
    FOREIGN KEY (campaign_id) REFERENCES comm_campaigns(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_comm_del_campaign ON comm_deliveries(campaign_id);

CREATE TABLE IF NOT EXISTS comm_audit (
    id TEXT PRIMARY KEY,
    campaign_id TEXT,
    action TEXT NOT NULL,
    detail_json TEXT NOT NULL DEFAULT '{}',
    trace_id TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_comm_audit_created ON comm_audit(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_comm_campaigns_status ON comm_campaigns(status);
CREATE INDEX IF NOT EXISTS idx_comm_campaigns_sched ON comm_campaigns(scheduled_at);
"""


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _new_id(prefix: str = "") -> str:
    return f"{prefix}{uuid.uuid4().hex[:16]}" if prefix else uuid.uuid4().hex


@dataclass(frozen=True)
class Campaign:
    id: str
    title: str
    body: str
    channel: str
    dest_type: str
    dest_ref: str
    status: str
    scheduled_at: str | None
    template_id: str | None
    is_test: bool
    preview_text: str
    created_at: str
    updated_at: str
    created_by: str


class CommsStore:
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

    # --- templates ---
    def upsert_template(self, *, name: str, body: str, template_id: str | None = None) -> str:
        tid = template_id or _new_id("tpl_")
        now = _utc_now()
        with self._lock, self._connect() as conn:
            row = conn.execute("SELECT id FROM comm_templates WHERE id = ?", (tid,)).fetchone()
            if row:
                conn.execute(
                    "UPDATE comm_templates SET name=?, body=?, updated_at=? WHERE id=?",
                    (name, body, now, tid),
                )
            else:
                conn.execute(
                    "INSERT INTO comm_templates (id, name, body, created_at, updated_at) VALUES (?,?,?,?,?)",
                    (tid, name, body, now, now),
                )
            conn.commit()
        return tid

    def list_templates(self) -> list[dict[str, Any]]:
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM comm_templates ORDER BY updated_at DESC"
            ).fetchall()
        return [dict(r) for r in rows]

    def get_template(self, template_id: str) -> dict[str, Any] | None:
        with self._lock, self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM comm_templates WHERE id = ?", (template_id,)
            ).fetchone()
        return dict(row) if row else None

    def delete_template(self, template_id: str) -> None:
        with self._lock, self._connect() as conn:
            conn.execute("DELETE FROM comm_templates WHERE id = ?", (template_id,))
            conn.commit()

    def seed_default_templates(self) -> None:
        defaults = [
            (
                "Aula ao Vivo",
                "Boa noite.\n\nA aula começa às {hora}.\n\nLink:\n{link}",
            ),
            ("Material Disponível", "Material da aula:\n\n{link}"),
            ("Aviso Geral", "Comunicado:\n\n{mensagem}"),
        ]
        existing = {t["name"] for t in self.list_templates()}
        for name, body in defaults:
            if name not in existing:
                self.upsert_template(name=name, body=body)

    # --- audiences ---
    def create_audience(self, *, name: str, description: str = "") -> str:
        aid = _new_id("aud_")
        now = _utc_now()
        with self._lock, self._connect() as conn:
            conn.execute(
                "INSERT INTO comm_audiences (id, name, description, created_at, updated_at) VALUES (?,?,?,?,?)",
                (aid, name.strip(), description.strip(), now, now),
            )
            conn.commit()
        return aid

    def list_audiences(self) -> list[dict[str, Any]]:
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                """
                SELECT a.*,
                  (SELECT COUNT(*) FROM comm_audience_members m WHERE m.audience_id = a.id) AS member_count
                FROM comm_audiences a
                ORDER BY a.name ASC
                """
            ).fetchall()
        return [dict(r) for r in rows]

    def get_audience(self, audience_id: str) -> dict[str, Any] | None:
        with self._lock, self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM comm_audiences WHERE id = ?", (audience_id,)
            ).fetchone()
        return dict(row) if row else None

    def add_audience_member(
        self,
        audience_id: str,
        *,
        member_type: str,
        member_ref: str,
        label: str = "",
    ) -> str:
        mid = _new_id("mem_")
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO comm_audience_members (id, audience_id, member_type, member_ref, label)
                VALUES (?,?,?,?,?)
                """,
                (mid, audience_id, member_type, member_ref.strip(), label.strip()),
            )
            conn.execute(
                "UPDATE comm_audiences SET updated_at=? WHERE id=?",
                (_utc_now(), audience_id),
            )
            conn.commit()
        return mid

    def list_audience_members(self, audience_id: str) -> list[dict[str, Any]]:
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM comm_audience_members WHERE audience_id = ? ORDER BY label, member_ref",
                (audience_id,),
            ).fetchall()
        return [dict(r) for r in rows]

    def delete_audience_member(self, member_id: str) -> None:
        with self._lock, self._connect() as conn:
            conn.execute("DELETE FROM comm_audience_members WHERE id = ?", (member_id,))
            conn.commit()

    # --- attachments ---
    def get_attachment_by_sha(self, sha256: str) -> dict[str, Any] | None:
        with self._lock, self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM comm_attachments WHERE sha256 = ?", (sha256,)
            ).fetchone()
        return dict(row) if row else None

    def get_attachment(self, attachment_id: str) -> dict[str, Any] | None:
        with self._lock, self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM comm_attachments WHERE id = ?", (attachment_id,)
            ).fetchone()
        return dict(row) if row else None

    def register_attachment(
        self,
        *,
        sha256: str,
        filename: str,
        content_type: str,
        size_bytes: int,
        storage_path: str,
    ) -> str:
        existing = self.get_attachment_by_sha(sha256)
        if existing:
            return str(existing["id"])
        aid = _new_id("att_")
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO comm_attachments
                (id, sha256, filename, content_type, size_bytes, storage_path, created_at)
                VALUES (?,?,?,?,?,?,?)
                """,
                (aid, sha256, filename, content_type, size_bytes, storage_path, _utc_now()),
            )
            conn.commit()
        return aid

    # --- campaigns ---
    def create_campaign(
        self,
        *,
        title: str,
        body: str,
        channel: str,
        dest_type: str,
        dest_ref: str,
        status: str = "draft",
        scheduled_at: str | None = None,
        template_id: str | None = None,
        is_test: bool = False,
        preview_text: str = "",
        attachment_ids: list[str] | None = None,
        created_by: str = "ops",
    ) -> str:
        cid = _new_id("cmp_")
        now = _utc_now()
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO comm_campaigns
                (id, title, body, channel, dest_type, dest_ref, status, scheduled_at,
                 template_id, is_test, preview_text, created_at, updated_at, created_by)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    cid,
                    title.strip(),
                    body,
                    channel,
                    dest_type,
                    dest_ref.strip(),
                    status,
                    scheduled_at,
                    template_id,
                    1 if is_test else 0,
                    preview_text or body,
                    now,
                    now,
                    created_by,
                ),
            )
            for att_id in attachment_ids or []:
                conn.execute(
                    "INSERT OR IGNORE INTO comm_campaign_attachments (campaign_id, attachment_id) VALUES (?,?)",
                    (cid, att_id),
                )
            conn.commit()
        return cid

    def update_campaign_status(
        self,
        campaign_id: str,
        status: str,
        *,
        scheduled_at: str | None = None,
    ) -> None:
        with self._lock, self._connect() as conn:
            if scheduled_at is not None:
                conn.execute(
                    "UPDATE comm_campaigns SET status=?, scheduled_at=?, updated_at=? WHERE id=?",
                    (status, scheduled_at, _utc_now(), campaign_id),
                )
            else:
                conn.execute(
                    "UPDATE comm_campaigns SET status=?, updated_at=? WHERE id=?",
                    (status, _utc_now(), campaign_id),
                )
            conn.commit()

    def try_claim_for_send(self, campaign_id: str) -> bool:
        """Reserva envio de forma atómica (scheduled/draft → sending).

        Retorna False se a campanha foi cancelada, já enviada ou já em envio.
        """
        with self._lock, self._connect() as conn:
            cur = conn.execute(
                """
                UPDATE comm_campaigns
                SET status='sending', updated_at=?
                WHERE id=? AND status IN ('scheduled', 'draft')
                """,
                (_utc_now(), campaign_id),
            )
            conn.commit()
            return cur.rowcount == 1

    def get_campaign(self, campaign_id: str) -> Campaign | None:
        with self._lock, self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM comm_campaigns WHERE id = ?", (campaign_id,)
            ).fetchone()
        if not row:
            return None
        return Campaign(
            id=row["id"],
            title=row["title"],
            body=row["body"],
            channel=row["channel"],
            dest_type=row["dest_type"],
            dest_ref=row["dest_ref"],
            status=row["status"],
            scheduled_at=row["scheduled_at"],
            template_id=row["template_id"],
            is_test=bool(row["is_test"]),
            preview_text=row["preview_text"] or row["body"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            created_by=row["created_by"],
        )

    def list_campaigns(self, *, limit: int = 100, status: str = "") -> list[Campaign]:
        limit = max(1, min(int(limit), 500))
        with self._lock, self._connect() as conn:
            if status:
                rows = conn.execute(
                    "SELECT * FROM comm_campaigns WHERE status = ? ORDER BY updated_at DESC LIMIT ?",
                    (status, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM comm_campaigns ORDER BY updated_at DESC LIMIT ?",
                    (limit,),
                ).fetchall()
        out: list[Campaign] = []
        for row in rows:
            out.append(
                Campaign(
                    id=row["id"],
                    title=row["title"],
                    body=row["body"],
                    channel=row["channel"],
                    dest_type=row["dest_type"],
                    dest_ref=row["dest_ref"],
                    status=row["status"],
                    scheduled_at=row["scheduled_at"],
                    template_id=row["template_id"],
                    is_test=bool(row["is_test"]),
                    preview_text=row["preview_text"] or row["body"],
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                    created_by=row["created_by"],
                )
            )
        return out

    def campaign_attachment_ids(self, campaign_id: str) -> list[str]:
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                "SELECT attachment_id FROM comm_campaign_attachments WHERE campaign_id = ?",
                (campaign_id,),
            ).fetchall()
        return [r["attachment_id"] for r in rows]

    def list_campaign_attachments(self, campaign_id: str) -> list[dict[str, Any]]:
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                """
                SELECT a.* FROM comm_attachments a
                JOIN comm_campaign_attachments ca ON ca.attachment_id = a.id
                WHERE ca.campaign_id = ?
                """,
                (campaign_id,),
            ).fetchall()
        return [dict(r) for r in rows]

    def due_scheduled(self, *, now_iso: str | None = None) -> list[Campaign]:
        now = now_iso or _utc_now()
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM comm_campaigns
                WHERE status = 'scheduled' AND scheduled_at IS NOT NULL AND scheduled_at <= ?
                ORDER BY scheduled_at ASC
                LIMIT 50
                """,
                (now,),
            ).fetchall()
        return [self.get_campaign(r["id"]) for r in rows if self.get_campaign(r["id"])]

    def add_delivery(
        self,
        *,
        campaign_id: str,
        dest_ref: str,
        dest_type: str,
        status: str,
        error: str = "",
        latency_ms: float | None = None,
        adapter: dict[str, Any] | None = None,
    ) -> str:
        did = _new_id("dlv_")
        now = _utc_now()
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO comm_deliveries
                (id, campaign_id, dest_ref, dest_type, status, error, latency_ms, adapter_json, created_at, sent_at)
                VALUES (?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    did,
                    campaign_id,
                    dest_ref,
                    dest_type,
                    status,
                    error,
                    latency_ms,
                    json.dumps(adapter or {}, ensure_ascii=False),
                    now,
                    now if status == "sent" else None,
                ),
            )
            conn.commit()
        return did

    def list_deliveries(self, campaign_id: str) -> list[dict[str, Any]]:
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM comm_deliveries WHERE campaign_id = ? ORDER BY created_at DESC",
                (campaign_id,),
            ).fetchall()
        return [dict(r) for r in rows]

    def audit(
        self,
        action: str,
        *,
        campaign_id: str | None = None,
        detail: dict[str, Any] | None = None,
        trace_id: str | None = None,
    ) -> str:
        aid = _new_id("audt_")
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO comm_audit (id, campaign_id, action, detail_json, trace_id, created_at)
                VALUES (?,?,?,?,?,?)
                """,
                (
                    aid,
                    campaign_id,
                    action,
                    json.dumps(detail or {}, ensure_ascii=False),
                    trace_id,
                    _utc_now(),
                ),
            )
            conn.commit()
        return aid

    def export_table(self, table: str) -> list[dict[str, Any]]:
        allowed = {
            "comm_campaigns",
            "comm_templates",
            "comm_audiences",
            "comm_audience_members",
            "comm_deliveries",
            "comm_attachments",
            "comm_audit",
        }
        if table not in allowed:
            raise ValueError("table not allowed")
        with self._lock, self._connect() as conn:
            rows = conn.execute(f"SELECT * FROM {table}").fetchall()  # noqa: S608
        return [dict(r) for r in rows]


_store: CommsStore | None = None


def init_comms_store(db_path: Path) -> CommsStore:
    global _store
    _store = CommsStore(db_path)
    _store.seed_default_templates()
    return _store


def get_comms_store() -> CommsStore | None:
    return _store


def reset_comms_store_for_tests() -> None:
    global _store
    _store = None
