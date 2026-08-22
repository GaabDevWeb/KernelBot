"""Recorder in-process de pipelines para observabilidade interna."""

from __future__ import annotations

import os
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from typing import Any


def _env_flag(name: str, default: bool = False) -> bool:
    raw = (os.getenv(name) or "").strip().lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "on"}


def _store_prompts() -> bool:
    # Default seguro: não persistir prompts completos em RAM.
    return _env_flag("ACL_INTERNAL_STORE_PROMPTS", default=False)


@dataclass
class PipelineRecord:
    request_id: str
    created_at: float
    kind: str  # chat | search | reload
    channel: str | None = None
    user_id: str | None = None
    session_id: str | None = None
    message_preview: str | None = None
    effective_discipline: str | None = None
    stages: list[dict[str, Any]] = field(default_factory=list)
    rag: dict[str, Any] | None = None
    context: dict[str, Any] | None = None
    prompt: list[dict[str, str]] | None = None
    prompt_meta: dict[str, Any] | None = None
    provider: dict[str, Any] | None = None
    response: dict[str, Any] | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "created_at": self.created_at,
            "kind": self.kind,
            "channel": self.channel,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "message_preview": self.message_preview,
            "effective_discipline": self.effective_discipline,
            "stages": list(self.stages),
            "rag": self.rag,
            "context": self.context,
            "prompt": self.prompt,
            "prompt_meta": self.prompt_meta,
            "provider": self.provider,
            "response": self.response,
            "error": self.error,
        }


class PipelineRecorder:
    """Ring buffer process-local (alinhado a pin/rate-limit)."""

    def __init__(self, capacity: int = 256) -> None:
        self._capacity = max(16, capacity)
        self._lock = threading.Lock()
        self._records: dict[str, PipelineRecord] = {}
        self._order: deque[str] = deque()
        self._started_at = time.time()
        self.metrics: dict[str, int] = {
            "requests_total": 0,
            "chat_total": 0,
            "search_total": 0,
            "chat_errors": 0,
            "rate_limited": 0,
            "provider_fallbacks": 0,
            "reloads": 0,
        }

    def new_request_id(self) -> str:
        return uuid.uuid4().hex

    def incr(self, key: str, amount: int = 1) -> None:
        with self._lock:
            self.metrics[key] = int(self.metrics.get(key, 0)) + amount

    def put(self, record: PipelineRecord) -> None:
        with self._lock:
            if record.request_id in self._records:
                self._records[record.request_id] = record
                return
            self._records[record.request_id] = record
            self._order.append(record.request_id)
            while len(self._order) > self._capacity:
                old = self._order.popleft()
                self._records.pop(old, None)

    def get(self, request_id: str) -> PipelineRecord | None:
        with self._lock:
            return self._records.get(request_id)

    def recent(self, limit: int = 50) -> list[PipelineRecord]:
        with self._lock:
            ids = list(self._order)[-max(1, limit) :]
            return [self._records[i] for i in reversed(ids) if i in self._records]

    def metrics_snapshot(self, *, index_chunks: int = 0, index_silos: int = 0) -> dict[str, Any]:
        with self._lock:
            out = dict(self.metrics)
        out["index_chunks"] = index_chunks
        out["index_silos"] = index_silos
        out["uptime_s"] = round(time.time() - self._started_at, 3)
        out["records_buffered"] = len(self._order)
        return out


_RECORDER = PipelineRecorder()


def get_recorder() -> PipelineRecorder:
    return _RECORDER


def reset_recorder_for_tests() -> PipelineRecorder:
    global _RECORDER
    _RECORDER = PipelineRecorder()
    return _RECORDER


def candidate_dicts(candidates: tuple | list) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for c in candidates:
        out.append(
            {
                "source": getattr(c, "source", None),
                "score": getattr(c, "raw_score", None),
                "score_normalized": getattr(c, "normalized_score", None),
                "discipline": getattr(c, "discipline", None),
                "matched_terms": list(getattr(c, "matched_terms", ()) or ()),
                "snippet": (getattr(c, "text", "") or "")[:240],
            }
        )
    return out


def build_rag_view(
    *,
    candidates: tuple | list,
    decision: Any | None,
) -> dict[str, Any]:
    selected = list(getattr(decision, "selected_candidates", ()) or ()) if decision else []
    selected_sources = {getattr(c, "source", None) for c in selected}
    considered = candidate_dicts(candidates)
    discarded = [c for c in considered if c.get("source") not in selected_sources]
    trace = getattr(decision, "trace", None) if decision else None
    return {
        "query": getattr(trace, "query", None) if trace else None,
        "normalized_query": getattr(trace, "normalized_query", None) if trace else None,
        "informative_terms": list(getattr(trace, "informative_terms", ()) or ()) if trace else [],
        "reason": getattr(decision, "reason", None) if decision else None,
        "confidence": getattr(decision, "confidence", None) if decision else None,
        "allow_generation": getattr(decision, "allow_generation", None) if decision else None,
        "top_score": getattr(trace, "top_score", None) if trace else None,
        "score_margin": getattr(trace, "score_margin", None) if trace else None,
        "coverage": getattr(trace, "coverage", None) if trace else None,
        "candidates_found": considered,
        "candidates_selected": candidate_dicts(selected),
        "candidates_discarded": discarded,
        "trace": trace.to_dict() if trace is not None and hasattr(trace, "to_dict") else None,
    }


def build_context_view(trace: Any, messages: list[dict] | None) -> dict[str, Any]:
    system_chars = 0
    history_turns = 0
    if messages:
        for m in messages:
            if m.get("role") == "system":
                system_chars += len(str(m.get("content") or ""))
            elif m.get("role") in {"user", "assistant"}:
                history_turns += 1
        # user actual conta no history_turns acima; ajustar: último user é current
        if history_turns > 0:
            history_turns = max(0, history_turns - 1)
    return {
        "label": getattr(trace, "label", None),
        "sources": list(getattr(trace, "sources", ()) or ()),
        "source_details": [dict(d) for d in (getattr(trace, "source_details", ()) or ())],
        "pinned_active": getattr(trace, "pinned_active", False),
        "pinned_display": getattr(trace, "pinned_display", None),
        "pin_chunks_used": getattr(trace, "pin_chunks_used", False),
        "mode": getattr(trace, "mode", None),
        "decision": getattr(trace, "decision", None),
        "reason": getattr(trace, "reason", None),
        "confidence": getattr(trace, "confidence", None),
        "catalog_match": getattr(trace, "catalog_match", False),
        "system_chars": system_chars,
        "history_turns_in_prompt": history_turns,
        "message_count": len(messages or []),
    }


def maybe_store_prompt(messages: list[dict]) -> tuple[list[dict[str, str]] | None, dict[str, Any]]:
    from kernel.structured_log import redact_secrets

    meta = {
        "stored": _store_prompts(),
        "roles": [str(m.get("role")) for m in messages],
        "total_chars": sum(len(str(m.get("content") or "")) for m in messages),
    }
    if not _store_prompts():
        return None, meta
    stored = [
        {
            "role": str(m.get("role") or ""),
            "content": redact_secrets(str(m.get("content") or "")),
        }
        for m in messages
    ]
    return stored, meta