"""Serviço Usuários — conversas (transcript+pin+traces) e helpers Ops."""

from __future__ import annotations

import csv
import io
import json
import logging
import zipfile
from typing import Any
from urllib.parse import unquote

from kernel.memory.pinned_store import PinnedSessionStore
from kernel.memory.transcript_store import TranscriptStore
from kernel.trace import get_trace_store
from kernel.users.store import UserSession, UsersStore, get_users_store

log = logging.getLogger("kernelbots.users")


def decode_memory_key_segments(memory_key: str) -> list[str]:
    return [unquote(p) for p in (memory_key or "").split(":")]


def conversation_bundle(
    session: UserSession,
    *,
    transcript_store: TranscriptStore | None,
    pinned_store: PinnedSessionStore | None,
) -> dict[str, Any]:
    """Junta transcript live, pin e traces recentes do user."""
    transcript: list[dict[str, str]] = []
    pin_info: dict[str, Any] | None = None
    if transcript_store is not None:
        transcript = transcript_store.get(session.memory_key)
    if pinned_store is not None:
        pinned = pinned_store.get(session.memory_key)
        if pinned is not None:
            pin_info = {
                "scope_key": pinned.scope_key,
                "display_name": pinned.display_name,
                "turns_left": pinned.turns_left,
                "chunks": len(pinned.chunks or []),
                "chunk_previews": [
                    {
                        "source": str(c.get("source") or c.get("path") or "")[:120],
                        "text": str(c.get("text") or c.get("content") or "")[:240],
                    }
                    for c in (pinned.chunks or [])[:5]
                ],
            }

    traces: list[dict[str, Any]] = []
    store = get_trace_store()
    if store is not None:
        try:
            from kernel.trace.store import TraceFilters

            # filtrar por user_id no JSON
            items = store.search_traces(
                TraceFilters(text=session.user_id, limit=30)
            )
            for t in items:
                if session.user_id and session.user_id not in (
                    t.user_label or ""
                ) and session.user_id not in (t.summary or ""):
                    # ainda pode estar só no data_json — search text já fez LIKE
                    pass
                traces.append(
                    {
                        "trace_id": t.trace_id,
                        "updated_at": t.updated_at,
                        "status": t.status,
                        "duration_ms": t.duration_ms,
                        "origin": t.origin,
                        "user_label": t.user_label,
                        "has_error": t.has_error,
                    }
                )
        except Exception as exc:
            log.debug("trace lookup skip: %s", exc)

    return {
        "session": session,
        "transcript": transcript,
        "pin": pin_info,
        "traces": traces,
        "live_pairs": len(transcript) // 2,
    }


def trace_error_stats_for_users(
    user_ids: set[str],
    *,
    hours: int = 168,
) -> dict[str, dict[str, Any]]:
    """Aproxima erros/latência por user_id a partir de traces (best-effort)."""
    out: dict[str, dict[str, Any]] = {
        uid: {"errors": 0, "traces": 0, "durations": []} for uid in user_ids
    }
    store = get_trace_store()
    if store is None or not user_ids:
        return out
    try:
        from datetime import datetime, timedelta, timezone

        from kernel.trace.store import duration_ms

        cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).strftime(
            "%Y-%m-%dT%H:%M:%S.000Z"
        )
        with store._lock:  # noqa: SLF001
            with store._connect() as conn:  # noqa: SLF001
                rows = conn.execute(
                    """
                    SELECT t.trace_id, t.created_at, t.updated_at, t.has_error, e.data_json
                    FROM traces t
                    JOIN trace_events e ON e.trace_id = t.trace_id
                    WHERE t.updated_at >= ?
                      AND e.stage = 'REQUEST_RECEIVED'
                    ORDER BY t.updated_at DESC
                    LIMIT 3000
                    """,
                    (cutoff,),
                ).fetchall()
        seen_traces: set[str] = set()
        for r in rows:
            try:
                data = json.loads(r["data_json"] or "{}")
            except (TypeError, json.JSONDecodeError):
                continue
            uid = str(data.get("user_id") or data.get("userId") or "")
            if uid not in out:
                continue
            tid = r["trace_id"]
            if tid in seen_traces:
                continue
            seen_traces.add(tid)
            out[uid]["traces"] += 1
            if r["has_error"]:
                out[uid]["errors"] += 1
            d = duration_ms(r["created_at"], r["updated_at"])
            if d is not None:
                out[uid]["durations"].append(d)
    except Exception as exc:
        log.debug("trace_error_stats skip: %s", exc)
    for uid, meta in out.items():
        durs = meta.pop("durations")
        meta["avg_ms"] = (sum(durs) / len(durs)) if durs else None
    return out


def build_export_zip(store: UsersStore) -> bytes:
    """ZIP com JSON+CSV de sessões, bloqueios e stats agregadas."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for table in ("user_sessions", "user_blocks"):
            rows = store.export_table(table)
            zf.writestr(f"{table}.json", json.dumps(rows, ensure_ascii=False, indent=2))
            if rows:
                out = io.StringIO()
                writer = csv.DictWriter(out, fieldnames=list(rows[0].keys()))
                writer.writeheader()
                writer.writerows(rows)
                zf.writestr(f"{table}.csv", out.getvalue())
        stats = store.user_stats(limit=500)
        # sqlite Row → dict pode ter int em `blocked`; normaliza para JSON/CSV
        stats_rows = [{k: (int(v) if k == "blocked" else v) for k, v in dict(r).items()} for r in stats]
        zf.writestr("user_stats.json", json.dumps(stats_rows, ensure_ascii=False, indent=2))
        if stats_rows:
            out = io.StringIO()
            writer = csv.DictWriter(out, fieldnames=list(stats_rows[0].keys()))
            writer.writeheader()
            writer.writerows(stats_rows)
            zf.writestr("user_stats.csv", out.getvalue())
    return buf.getvalue()


def is_user_blocked(platform: str, user_id: str) -> bool:
    store = get_users_store()
    if store is None:
        return False
    return store.is_blocked(platform, user_id)


def touch_user_session(
    *,
    platform: str,
    user_id: str,
    channel_id: str,
    session_id: str | None,
    memory_key: str,
    increment_messages: int = 0,
) -> None:
    store = get_users_store()
    if store is None:
        return
    try:
        store.touch_session(
            platform=platform,
            user_id=user_id,
            channel_id=channel_id,
            session_id=session_id,
            memory_key=memory_key,
            increment_messages=increment_messages,
        )
    except Exception as exc:
        log.warning("touch_session failed: %s", exc)
