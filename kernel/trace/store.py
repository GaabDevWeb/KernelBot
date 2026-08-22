"""SQLite persistente para TRACE operacional (fatias A+B)."""

from __future__ import annotations

import json
import logging
import sqlite3
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

log = logging.getLogger("kernelbots.trace.store")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS traces (
    trace_id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    has_error INTEGER NOT NULL DEFAULT 0,
    services TEXT NOT NULL DEFAULT '',
    summary TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS trace_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trace_id TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    service TEXT NOT NULL,
    stage TEXT NOT NULL,
    data_json TEXT NOT NULL DEFAULT '{}',
    priority INTEGER NOT NULL DEFAULT 10,
    FOREIGN KEY (trace_id) REFERENCES traces(trace_id)
);

CREATE INDEX IF NOT EXISTS idx_trace_events_trace_id ON trace_events(trace_id);
CREATE INDEX IF NOT EXISTS idx_traces_updated_at ON traces(updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_trace_events_stage ON trace_events(stage);
CREATE INDEX IF NOT EXISTS idx_trace_events_ts ON trace_events(timestamp);

CREATE TABLE IF NOT EXISTS trace_snapshots (
    trace_id TEXT PRIMARY KEY,
    conversation_json TEXT NOT NULL DEFAULT '{}',
    rag_json TEXT NOT NULL DEFAULT '{}',
    prompt_json TEXT NOT NULL DEFAULT '{}',
    tokens_json TEXT NOT NULL DEFAULT '{}',
    performance_json TEXT NOT NULL DEFAULT '{}',
    system_metrics_json TEXT NOT NULL DEFAULT '{}',
    replay_of TEXT,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (trace_id) REFERENCES traces(trace_id)
);
"""


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def parse_iso_ts(value: str | None) -> datetime | None:
    if not value:
        return None
    raw = value.strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def duration_ms(start: str | None, end: str | None) -> float | None:
    a = parse_iso_ts(start)
    b = parse_iso_ts(end)
    if a is None or b is None:
        return None
    return max(0.0, (b - a).total_seconds() * 1000.0)


@dataclass(frozen=True)
class TraceSummary:
    trace_id: str
    created_at: str
    updated_at: str
    has_error: bool
    services: str
    summary: str
    event_count: int = 0
    origin: str = ""
    user_label: str = ""
    duration_ms: float | None = None
    status: str = "ok"


@dataclass(frozen=True)
class TraceEventRow:
    id: int
    trace_id: str
    timestamp: str
    service: str
    stage: str
    data: dict[str, Any]
    priority: int
    delta_ms: float | None = None


@dataclass(frozen=True)
class TraceMetrics:
    total_traces: int
    total_errors: int
    traces_24h: int
    errors_24h: int
    avg_duration_ms: float | None
    events_total: int
    p95_ms: float | None = None
    p99_ms: float | None = None
    p50_ms: float | None = None
    messages_today: int = 0
    messages_last_hour: int = 0
    errors_last_hour: int = 0
    timeouts_24h: int = 0
    active_users_24h: int = 0


@dataclass(frozen=True)
class HourlyBucket:
    hour: str  # YYYY-MM-DDTHH
    messages: int
    errors: int
    avg_duration_ms: float | None


def _percentile(sorted_vals: list[float], p: float) -> float | None:
    if not sorted_vals:
        return None
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    k = (len(sorted_vals) - 1) * (p / 100.0)
    f = int(k)
    c = min(f + 1, len(sorted_vals) - 1)
    if f == c:
        return sorted_vals[f]
    return sorted_vals[f] + (sorted_vals[c] - sorted_vals[f]) * (k - f)


@dataclass(frozen=True)
class TraceFilters:
    trace_id: str = ""
    phone: str = ""
    group: str = ""
    text: str = ""
    since: str = ""
    until: str = ""
    errors_only: bool = False
    limit: int = 100


class TraceStore:
    """Store síncrono thread-safe (sqlite3); chamadas async via to_thread."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
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

    def insert_event(
        self,
        *,
        trace_id: str,
        timestamp: str | None,
        service: str,
        stage: str,
        data: dict[str, Any] | None,
        priority: int,
    ) -> None:
        tid = (trace_id or "").strip()
        if not tid:
            raise ValueError("trace_id required")
        ts = (timestamp or "").strip() or _utc_now_iso()
        svc = (service or "").strip() or "unknown"
        stg = (stage or "").strip() or "UNKNOWN"
        payload = json.dumps(data or {}, ensure_ascii=False, default=str)
        is_error = 1 if stg.upper() == "ERROR" or priority <= 0 else 0
        summary = f"{svc}:{stg}"

        with self._lock:
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT services, has_error FROM traces WHERE trace_id = ?",
                    (tid,),
                ).fetchone()
                if row is None:
                    conn.execute(
                        """
                        INSERT INTO traces (trace_id, created_at, updated_at, has_error, services, summary)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (tid, ts, ts, is_error, svc, summary),
                    )
                else:
                    services = set(filter(None, (row["services"] or "").split(",")))
                    services.add(svc)
                    has_error = 1 if row["has_error"] or is_error else 0
                    conn.execute(
                        """
                        UPDATE traces
                        SET updated_at = ?, has_error = ?, services = ?, summary = ?
                        WHERE trace_id = ?
                        """,
                        (ts, has_error, ",".join(sorted(services)), summary, tid),
                    )
                conn.execute(
                    """
                    INSERT INTO trace_events (trace_id, timestamp, service, stage, data_json, priority)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (tid, ts, svc, stg, payload, int(priority)),
                )
                conn.commit()

    def _row_to_summary(self, r: sqlite3.Row, *, enrich: bool = True) -> TraceSummary:
        base = TraceSummary(
            trace_id=r["trace_id"],
            created_at=r["created_at"],
            updated_at=r["updated_at"],
            has_error=bool(r["has_error"]),
            services=r["services"] or "",
            summary=r["summary"] or "",
            event_count=int(r["event_count"] or 0) if "event_count" in r.keys() else 0,
            status="error" if r["has_error"] else "ok",
        )
        if not enrich:
            return base
        meta = self._enrich_trace(base.trace_id, created_at=base.created_at, updated_at=base.updated_at)
        return TraceSummary(
            trace_id=base.trace_id,
            created_at=base.created_at,
            updated_at=base.updated_at,
            has_error=base.has_error,
            services=base.services,
            summary=base.summary,
            event_count=base.event_count,
            origin=meta["origin"],
            user_label=meta["user_label"],
            duration_ms=meta["duration_ms"],
            status=base.status,
        )

    def _enrich_trace(self, trace_id: str, *, created_at: str, updated_at: str) -> dict[str, Any]:
        events = self.get_events(trace_id, with_deltas=False)
        origin = "kernel"
        user_label = ""
        for e in events:
            data = e.data or {}
            channel = str(data.get("channel") or "")
            if channel == "group" or data.get("groupJid") or str(data.get("channel_id") or "").endswith("@g.us"):
                origin = "group"
            elif channel == "1:1" or data.get("jid") or data.get("userId") or data.get("user_id"):
                if origin != "group":
                    origin = "1:1"
            for key in ("userId", "user_id", "jid", "authorJid", "author_jid"):
                if data.get(key) and not user_label:
                    user_label = str(data[key])
            if data.get("groupJid") and origin == "group" and not user_label:
                user_label = str(data.get("authorJid") or data.get("userId") or data["groupJid"])
        if "orbit" in ("" if not events else ",".join(sorted({e.service for e in events}))):
            if origin == "kernel":
                origin = "orbit"
        dur = duration_ms(created_at, updated_at)
        if events:
            dur = duration_ms(events[0].timestamp, events[-1].timestamp) or dur
        return {"origin": origin, "user_label": user_label, "duration_ms": dur}

    def list_traces(self, *, limit: int = 50, trace_id: str | None = None) -> list[TraceSummary]:
        filters = TraceFilters(trace_id=(trace_id or "").strip(), limit=limit)
        return self.search_traces(filters)

    def search_traces(self, filters: TraceFilters) -> list[TraceSummary]:
        limit = max(1, min(int(filters.limit or 100), 500))
        clauses: list[str] = []
        params: list[Any] = []

        tid = (filters.trace_id or "").strip()
        if tid:
            clauses.append("t.trace_id = ?")
            params.append(tid)

        if filters.errors_only:
            clauses.append("t.has_error = 1")

        since = (filters.since or "").strip()
        until = (filters.until or "").strip()
        if since:
            clauses.append("t.updated_at >= ?")
            params.append(since)
        if until:
            clauses.append("t.updated_at <= ?")
            params.append(until)

        phone = (filters.phone or "").strip()
        group = (filters.group or "").strip()
        text = (filters.text or "").strip()

        # Filtros em data_json / summary via EXISTS
        for needle, label in ((phone, "phone"), (group, "group"), (text, "text")):
            if not needle:
                continue
            like = f"%{needle}%"
            clauses.append(
                """
                EXISTS (
                  SELECT 1 FROM trace_events e
                  WHERE e.trace_id = t.trace_id
                    AND (e.data_json LIKE ? OR e.stage LIKE ? OR t.summary LIKE ? OR t.trace_id LIKE ?)
                )
                """
            )
            params.extend([like, like, like, like])

        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        sql = f"""
            SELECT t.*,
                   (SELECT COUNT(*) FROM trace_events e WHERE e.trace_id = t.trace_id) AS event_count
            FROM traces t
            {where}
            ORDER BY t.updated_at DESC
            LIMIT ?
        """
        params.append(limit)

        with self._lock:
            with self._connect() as conn:
                rows = conn.execute(sql, params).fetchall()

        return [self._row_to_summary(r, enrich=True) for r in rows]

    def get_events(self, trace_id: str, *, with_deltas: bool = True) -> list[TraceEventRow]:
        tid = (trace_id or "").strip()
        with self._lock:
            with self._connect() as conn:
                rows = conn.execute(
                    """
                    SELECT id, trace_id, timestamp, service, stage, data_json, priority
                    FROM trace_events
                    WHERE trace_id = ?
                    ORDER BY timestamp ASC, id ASC
                    """,
                    (tid,),
                ).fetchall()
        out: list[TraceEventRow] = []
        prev_ts: str | None = None
        for r in rows:
            try:
                data = json.loads(r["data_json"] or "{}")
                if not isinstance(data, dict):
                    data = {"value": data}
            except json.JSONDecodeError:
                data = {"raw": r["data_json"]}
            delta = duration_ms(prev_ts, r["timestamp"]) if with_deltas else None
            out.append(
                TraceEventRow(
                    id=int(r["id"]),
                    trace_id=r["trace_id"],
                    timestamp=r["timestamp"],
                    service=r["service"],
                    stage=r["stage"],
                    data=data,
                    priority=int(r["priority"]),
                    delta_ms=delta,
                )
            )
            prev_ts = r["timestamp"]
        return out

    def get_trace(self, trace_id: str) -> TraceSummary | None:
        rows = self.search_traces(TraceFilters(trace_id=trace_id, limit=1))
        return rows[0] if rows else None

    def list_trace_ids(
        self,
        *,
        since: str | None = None,
        until: str | None = None,
        all_records: bool = False,
        limit: int = 5000,
    ) -> list[str]:
        filters = TraceFilters(
            since=(since or "").strip(),
            until=(until or "").strip(),
            limit=5000 if all_records else max(1, min(limit, 5000)),
        )
        return [t.trace_id for t in self.search_traces(filters)]

    def metrics(self, *, hours: int = 24) -> TraceMetrics:
        hours = max(1, min(int(hours), 168))
        now = datetime.now(timezone.utc)
        cutoff = (now - timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        today = now.strftime("%Y-%m-%dT00:00:00.000Z")
        hour_ago = (now - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        with self._lock:
            with self._connect() as conn:
                total = conn.execute("SELECT COUNT(*) AS c FROM traces").fetchone()["c"]
                errors = conn.execute(
                    "SELECT COUNT(*) AS c FROM traces WHERE has_error = 1"
                ).fetchone()["c"]
                t24 = conn.execute(
                    "SELECT COUNT(*) AS c FROM traces WHERE updated_at >= ?",
                    (cutoff,),
                ).fetchone()["c"]
                e24 = conn.execute(
                    "SELECT COUNT(*) AS c FROM traces WHERE has_error = 1 AND updated_at >= ?",
                    (cutoff,),
                ).fetchone()["c"]
                events_total = conn.execute("SELECT COUNT(*) AS c FROM trace_events").fetchone()["c"]
                today_c = conn.execute(
                    "SELECT COUNT(*) AS c FROM traces WHERE created_at >= ?",
                    (today,),
                ).fetchone()["c"]
                hour_c = conn.execute(
                    "SELECT COUNT(*) AS c FROM traces WHERE created_at >= ?",
                    (hour_ago,),
                ).fetchone()["c"]
                hour_err = conn.execute(
                    "SELECT COUNT(*) AS c FROM traces WHERE has_error = 1 AND updated_at >= ?",
                    (hour_ago,),
                ).fetchone()["c"]
                recent = conn.execute(
                    """
                    SELECT created_at, updated_at FROM traces
                    WHERE updated_at >= ?
                    ORDER BY updated_at DESC
                    LIMIT 500
                    """,
                    (cutoff,),
                ).fetchall()
                timeouts = conn.execute(
                    """
                    SELECT COUNT(DISTINCT te.trace_id) AS c
                    FROM trace_events te
                    WHERE te.timestamp >= ?
                      AND (
                        lower(te.stage) LIKE '%timeout%'
                        OR lower(te.data_json) LIKE '%timeout%'
                      )
                    """,
                    (cutoff,),
                ).fetchone()["c"]
                # aproximação de utilizadores activos: jids/userIds em eventos recentes
                user_rows = conn.execute(
                    """
                    SELECT data_json FROM trace_events
                    WHERE timestamp >= ?
                    ORDER BY id DESC
                    LIMIT 2000
                    """,
                    (cutoff,),
                ).fetchall()
        durations = []
        for r in recent:
            d = duration_ms(r["created_at"], r["updated_at"])
            if d is not None:
                durations.append(d)
        durations.sort()
        avg = (sum(durations) / len(durations)) if durations else None
        users: set[str] = set()
        for ur in user_rows:
            try:
                data = json.loads(ur["data_json"] or "{}")
            except (TypeError, json.JSONDecodeError):
                continue
            if not isinstance(data, dict):
                continue
            for key in ("userId", "user_id", "jid", "authorJid", "author_jid"):
                val = data.get(key)
                if val:
                    users.add(str(val)[:120])
                    break
        return TraceMetrics(
            total_traces=int(total),
            total_errors=int(errors),
            traces_24h=int(t24),
            errors_24h=int(e24),
            avg_duration_ms=avg,
            events_total=int(events_total),
            p50_ms=_percentile(durations, 50),
            p95_ms=_percentile(durations, 95),
            p99_ms=_percentile(durations, 99),
            messages_today=int(today_c),
            messages_last_hour=int(hour_c),
            errors_last_hour=int(hour_err),
            timeouts_24h=int(timeouts or 0),
            active_users_24h=len(users),
        )

    def hourly_series(self, *, hours: int = 24) -> list[HourlyBucket]:
        """Séries horárias para gráficos SVG (mensagens / erros / latência média)."""
        hours = max(1, min(int(hours), 168))
        now = datetime.now(timezone.utc)
        # alinhar ao início da hora
        start = (now - timedelta(hours=hours - 1)).replace(minute=0, second=0, microsecond=0)
        cutoff = start.strftime("%Y-%m-%dT%H:%M:%S.000Z")
        with self._lock:
            with self._connect() as conn:
                rows = conn.execute(
                    """
                    SELECT created_at, updated_at, has_error
                    FROM traces
                    WHERE created_at >= ?
                    ORDER BY created_at ASC
                    """,
                    (cutoff,),
                ).fetchall()
        buckets: dict[str, list[tuple[float | None, bool]]] = {}
        cursor = start
        end_hour = now.replace(minute=0, second=0, microsecond=0)
        while cursor <= end_hour:
            key = cursor.strftime("%Y-%m-%dT%H")
            buckets[key] = []
            cursor += timedelta(hours=1)
        for r in rows:
            created = r["created_at"] or ""
            key = created[:13] if len(created) >= 13 else ""
            if key not in buckets:
                continue
            d = duration_ms(r["created_at"], r["updated_at"])
            buckets[key].append((d, bool(r["has_error"])))
        out: list[HourlyBucket] = []
        for key in sorted(buckets.keys()):
            items = buckets[key]
            durs = [d for d, _ in items if d is not None]
            avg = (sum(durs) / len(durs)) if durs else None
            out.append(
                HourlyBucket(
                    hour=key,
                    messages=len(items),
                    errors=sum(1 for _, err in items if err),
                    avg_duration_ms=avg,
                )
            )
        return out

    def upsert_snapshot(
        self,
        trace_id: str,
        *,
        conversation: dict[str, Any] | None = None,
        rag: dict[str, Any] | None = None,
        prompt: dict[str, Any] | None = None,
        tokens: dict[str, Any] | None = None,
        performance: dict[str, Any] | None = None,
        system_metrics: dict[str, Any] | None = None,
        replay_of: str | None = None,
    ) -> None:
        tid = (trace_id or "").strip()
        if not tid:
            return
        ts = _utc_now_iso()
        with self._lock:
            with self._connect() as conn:
                # garantir linha em traces
                exists = conn.execute(
                    "SELECT 1 FROM traces WHERE trace_id = ?", (tid,)
                ).fetchone()
                if exists is None:
                    conn.execute(
                        """
                        INSERT INTO traces (trace_id, created_at, updated_at, has_error, services, summary)
                        VALUES (?, ?, ?, 0, 'kernel', 'snapshot')
                        """,
                        (tid, ts, ts),
                    )
                row = conn.execute(
                    "SELECT * FROM trace_snapshots WHERE trace_id = ?", (tid,)
                ).fetchone()

                def _merge(old: str | None, new: dict | None) -> str:
                    base: dict[str, Any] = {}
                    if old:
                        try:
                            parsed = json.loads(old)
                            if isinstance(parsed, dict):
                                base = parsed
                        except json.JSONDecodeError:
                            pass
                    if new:
                        base.update(new)
                    return json.dumps(base, ensure_ascii=False, default=str)

                if row is None:
                    conn.execute(
                        """
                        INSERT INTO trace_snapshots (
                          trace_id, conversation_json, rag_json, prompt_json, tokens_json,
                          performance_json, system_metrics_json, replay_of, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            tid,
                            json.dumps(conversation or {}, ensure_ascii=False, default=str),
                            json.dumps(rag or {}, ensure_ascii=False, default=str),
                            json.dumps(prompt or {}, ensure_ascii=False, default=str),
                            json.dumps(tokens or {}, ensure_ascii=False, default=str),
                            json.dumps(performance or {}, ensure_ascii=False, default=str),
                            json.dumps(system_metrics or {}, ensure_ascii=False, default=str),
                            replay_of,
                            ts,
                        ),
                    )
                else:
                    conn.execute(
                        """
                        UPDATE trace_snapshots SET
                          conversation_json = ?,
                          rag_json = ?,
                          prompt_json = ?,
                          tokens_json = ?,
                          performance_json = ?,
                          system_metrics_json = ?,
                          replay_of = COALESCE(?, replay_of),
                          updated_at = ?
                        WHERE trace_id = ?
                        """,
                        (
                            _merge(row["conversation_json"], conversation),
                            _merge(row["rag_json"], rag),
                            _merge(row["prompt_json"], prompt),
                            _merge(row["tokens_json"], tokens),
                            _merge(row["performance_json"], performance),
                            _merge(row["system_metrics_json"], system_metrics),
                            replay_of,
                            ts,
                            tid,
                        ),
                    )
                conn.commit()

    def get_snapshot(self, trace_id: str) -> dict[str, Any] | None:
        tid = (trace_id or "").strip()
        with self._lock:
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT * FROM trace_snapshots WHERE trace_id = ?", (tid,)
                ).fetchone()
        if row is None:
            return None

        def _load(raw: str | None) -> dict[str, Any]:
            try:
                data = json.loads(raw or "{}")
                return data if isinstance(data, dict) else {}
            except json.JSONDecodeError:
                return {}

        return {
            "trace_id": tid,
            "conversation": _load(row["conversation_json"]),
            "rag": _load(row["rag_json"]),
            "prompt": _load(row["prompt_json"]),
            "tokens": _load(row["tokens_json"]),
            "performance": _load(row["performance_json"]),
            "system_metrics": _load(row["system_metrics_json"]),
            "replay_of": row["replay_of"],
            "updated_at": row["updated_at"],
        }

    def purge_older_than(self, days: int) -> int:
        days = max(1, min(int(days), 3650))
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime(
            "%Y-%m-%dT%H:%M:%S.000Z"
        )
        with self._lock:
            with self._connect() as conn:
                ids = [
                    r["trace_id"]
                    for r in conn.execute(
                        "SELECT trace_id FROM traces WHERE updated_at < ?",
                        (cutoff,),
                    ).fetchall()
                ]
                if not ids:
                    return 0
                placeholders = ",".join("?" for _ in ids)
                conn.execute(
                    f"DELETE FROM trace_events WHERE trace_id IN ({placeholders})", ids
                )
                conn.execute(
                    f"DELETE FROM trace_snapshots WHERE trace_id IN ({placeholders})", ids
                )
                conn.execute(
                    f"DELETE FROM traces WHERE trace_id IN ({placeholders})", ids
                )
                conn.commit()
                return len(ids)

    def collect_bundle(self, trace_ids: list[str]) -> dict[str, Any]:
        """Dados estruturados para ZIP / views."""
        traces: list[dict[str, Any]] = []
        events: list[dict[str, Any]] = []
        messages: list[dict[str, Any]] = []
        orbit_lines: list[str] = []
        kernel_lines: list[str] = []

        for tid in trace_ids:
            summary = self.get_trace(tid)
            evs = self.get_events(tid, with_deltas=True)
            if summary is None and not evs:
                continue
            if summary:
                traces.append(
                    {
                        "trace_id": summary.trace_id,
                        "created_at": summary.created_at,
                        "updated_at": summary.updated_at,
                        "has_error": summary.has_error,
                        "services": summary.services,
                        "summary": summary.summary,
                        "origin": summary.origin,
                        "user_label": summary.user_label,
                        "duration_ms": summary.duration_ms,
                        "status": summary.status,
                        "event_count": summary.event_count,
                    }
                )
            msg_in = None
            msg_out = None
            channel = None
            user = None
            for e in evs:
                events.append(
                    {
                        "id": e.id,
                        "trace_id": e.trace_id,
                        "timestamp": e.timestamp,
                        "service": e.service,
                        "stage": e.stage,
                        "data": e.data,
                        "priority": e.priority,
                        "delta_ms": e.delta_ms,
                    }
                )
                line = f"{e.timestamp} [{e.service}] {e.stage} {json.dumps(e.data, ensure_ascii=False)}"
                if e.service == "orbit":
                    orbit_lines.append(line)
                else:
                    kernel_lines.append(line)
                data = e.data or {}
                if e.stage in {"MESSAGE_RECEIVED", "MESSAGE_PARSED", "REQUEST_RECEIVED"}:
                    preview = data.get("message_preview") or data.get("message") or data.get("text")
                    if preview and msg_in is None:
                        msg_in = str(preview)
                if e.stage in {"RESPONSE_GENERATED", "RESPONSE_RETURNED", "MESSAGE_SENT_TO_WHATSAPP"}:
                    preview = data.get("answer_preview") or data.get("answer") or data.get("text")
                    if preview:
                        msg_out = str(preview)
                for k in ("channel", "channel_id", "groupJid", "jid"):
                    if data.get(k) and channel is None:
                        channel = str(data[k])
                for k in ("user_id", "userId", "authorJid", "jid"):
                    if data.get(k) and user is None:
                        user = str(data[k])
            messages.append(
                {
                    "trace_id": tid,
                    "user": user,
                    "channel": channel,
                    "message": msg_in,
                    "answer": msg_out,
                    "created_at": summary.created_at if summary else (evs[0].timestamp if evs else None),
                    "updated_at": summary.updated_at if summary else (evs[-1].timestamp if evs else None),
                }
            )

        return {
            "traces": traces,
            "events": events,
            "messages": messages,
            "orbit_log": "\n".join(orbit_lines) + ("\n" if orbit_lines else ""),
            "kernel_log": "\n".join(kernel_lines) + ("\n" if kernel_lines else ""),
        }
