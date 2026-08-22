"""Helpers de forensics / tokens / performance para o Flight Recorder."""

from __future__ import annotations

import os
from typing import Any

from kernel.structured_log import redact_secrets


def trace_enabled() -> bool:
    raw = (os.getenv("ACL_TRACE_ENABLED") or "true").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def store_prompts_enabled() -> bool:
    raw = (os.getenv("ACL_TRACE_STORE_PROMPTS") or "true").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def estimate_tokens(text: str) -> int:
    """Estimativa simples ~4 chars/token (quando o provider não reporta)."""
    n = len(text or "")
    return max(0, (n + 3) // 4)


def build_prompt_forensics(messages: list[dict], *, transcript: list[dict] | None, pin: Any) -> dict[str, Any]:
    roles = [str(m.get("role") or "") for m in messages]
    contents = [redact_secrets(str(m.get("content") or "")) for m in messages]
    total_chars = sum(len(c) for c in contents)
    system = next((c for r, c in zip(roles, contents) if r == "system"), "")
    # last user ≈ pergunta; histórico = restantes user/assistant no meio
    transcript_view = []
    for t in transcript or []:
        transcript_view.append(
            {
                "role": str(t.get("role") or ""),
                "content": redact_secrets(str(t.get("content") or ""))[:2000],
            }
        )
    pin_view = None
    if pin is not None:
        chunks = getattr(pin, "chunks", None) or []
        pin_view = {
            "scope_key": getattr(pin, "scope_key", None),
            "display_name": getattr(pin, "display_name", None),
            "turns_left": getattr(pin, "turns_left", None),
            "chunk_count": len(chunks),
            "chunks_preview": [
                {
                    "source": c.get("source"),
                    "text": redact_secrets(str(c.get("text") or ""))[:500],
                }
                for c in chunks[:6]
                if isinstance(c, dict)
            ],
        }
    stored_messages = None
    if store_prompts_enabled():
        stored_messages = [{"role": r, "content": c[:12000]} for r, c in zip(roles, contents)]
    return {
        "system_prompt": system[:20000] if store_prompts_enabled() else system[:500],
        "transcript": transcript_view[:40],
        "pin": pin_view,
        "messages": stored_messages,
        "roles": roles,
        "prompt_chars": total_chars,
        "prompt_tokens_est": estimate_tokens("".join(contents)),
        "stored_full": store_prompts_enabled(),
    }


def build_rag_forensics(
    *,
    query: str,
    built: Any,
) -> dict[str, Any]:
    cands = []
    for c in (getattr(built, "candidates_considered", None) or ())[:12]:
        cands.append(
            {
                "source": getattr(c, "source", None),
                "raw_score": getattr(c, "raw_score", None),
                "normalized_score": getattr(c, "normalized_score", None),
                "discipline": getattr(c, "discipline", None),
                "text_preview": redact_secrets(str(getattr(c, "text", "") or ""))[:400],
            }
        )
    trace = getattr(built, "trace", None)
    decision = getattr(built, "decision", None)
    dtrace = getattr(decision, "trace", None) if decision is not None else None
    return {
        "query": query[:1000],
        "normalized_query": getattr(dtrace, "normalized_query", None),
        "reason": getattr(trace, "reason", None),
        "confidence": getattr(trace, "confidence", None),
        "sources": list(getattr(trace, "sources", None) or ())[:20],
        "candidates": cands,
        "discipline": getattr(built, "effective_discipline", None),
    }


def build_tokens_forensics(
    *,
    prompt_chars: int,
    answer: str,
    metadata: dict | None,
) -> dict[str, Any]:
    prompt_tokens = estimate_tokens("x" * max(0, prompt_chars))
    completion_tokens = estimate_tokens(answer or "")
    meta = metadata or {}
    # Preferir campos reais se existirem
    pt = meta.get("prompt_tokens") or meta.get("input_tokens")
    ct = meta.get("completion_tokens") or meta.get("output_tokens")
    if isinstance(pt, (int, float)):
        prompt_tokens = int(pt)
    if isinstance(ct, (int, float)):
        completion_tokens = int(ct)
    return {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": prompt_tokens + completion_tokens,
        "input_chars": prompt_chars,
        "output_chars": len(answer or ""),
        "estimated": pt is None and ct is None,
        "provider_fragments": meta.get("tokens_used"),
    }


def build_performance_map(timings: dict[str, float | None]) -> dict[str, Any]:
    """timings em ms (float)."""
    clean = {k: (round(v, 2) if isinstance(v, (int, float)) else None) for k, v in timings.items()}
    total = clean.get("total_ms")
    if total is None:
        known = [v for v in clean.values() if isinstance(v, (int, float))]
        total = round(sum(known), 2) if known else None
        clean["total_ms"] = total
    return clean
