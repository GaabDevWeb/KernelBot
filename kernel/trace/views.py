"""Helpers de vista para o painel TRACE (RAG + conversa)."""

from __future__ import annotations

from typing import Any

from kernel.trace.store import TraceEventRow, TraceSummary


def build_rag_view(events: list[TraceEventRow]) -> dict[str, Any] | None:
    rag_started = next((e for e in events if e.stage == "RAG_STARTED"), None)
    rag_finished = next((e for e in events if e.stage == "RAG_FINISHED"), None)
    if rag_started is None and rag_finished is None:
        return None
    data = (rag_finished.data if rag_finished else {}) or {}
    return {
        "query": data.get("query") or data.get("message_preview"),
        "sources": data.get("sources") or [],
        "candidates": data.get("candidates"),
        "confidence": data.get("confidence"),
        "reason": data.get("reason"),
        "discipline": data.get("discipline"),
        "started_at": rag_started.timestamp if rag_started else None,
        "finished_at": rag_finished.timestamp if rag_finished else None,
        "duration_ms": rag_finished.delta_ms if rag_finished else None,
    }


def build_conversation_view(
    summary: TraceSummary | None,
    events: list[TraceEventRow],
) -> dict[str, Any]:
    message = None
    answer = None
    channel = None
    user = None
    group = None
    for e in events:
        data = e.data or {}
        if message is None:
            for k in ("message_preview", "message", "text", "question"):
                if data.get(k):
                    message = str(data[k])
                    break
        if answer is None:
            for k in ("answer_preview", "answer", "text"):
                if e.stage in {
                    "RESPONSE_GENERATED",
                    "RESPONSE_RETURNED",
                    "MESSAGE_SENT_TO_WHATSAPP",
                    "RESPONSE_RECEIVED_FROM_KERNEL",
                } and data.get(k):
                    answer = str(data[k])
                    break
        if user is None:
            for k in ("user_id", "userId", "authorJid", "jid"):
                if data.get(k):
                    user = str(data[k])
                    break
        if group is None and (data.get("groupJid") or str(data.get("channel_id") or "").endswith("@g.us")):
            group = str(data.get("groupJid") or data.get("channel_id"))
        if channel is None:
            channel = data.get("channel") or data.get("platform") or data.get("channel_id")
    return {
        "message": message,
        "answer": answer,
        "user": user or (summary.user_label if summary else None),
        "channel": channel,
        "group": group,
        "origin": summary.origin if summary else None,
        "created_at": summary.created_at if summary else (events[0].timestamp if events else None),
        "updated_at": summary.updated_at if summary else (events[-1].timestamp if events else None),
        "duration_ms": summary.duration_ms if summary else None,
        "status": summary.status if summary else "ok",
    }
