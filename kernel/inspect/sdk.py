"""API de inspeção programática (sem HTTP)."""

from __future__ import annotations

import time
from typing import Any

from kernel.disciplines.disciplines import load_disciplines
from kernel.inspect.recorder import get_recorder
from kernel.knowledge.database import DB_CHUNK_OVERLAP, DB_CHUNK_WORDS


def pipeline(request_id: str) -> dict[str, Any] | None:
    rec = get_recorder().get(request_id)
    return rec.to_dict() if rec else None


def rag_query(request_id: str) -> dict[str, Any] | None:
    rec = get_recorder().get(request_id)
    if rec is None:
        return None
    return {"request_id": request_id, "rag": rec.rag}


def context(request_id: str) -> dict[str, Any] | None:
    rec = get_recorder().get(request_id)
    if rec is None:
        return None
    return {"request_id": request_id, "context": rec.context}


def prompt(request_id: str) -> dict[str, Any] | None:
    rec = get_recorder().get(request_id)
    if rec is None:
        return None
    return {
        "request_id": request_id,
        "prompt": rec.prompt,
        "prompt_meta": rec.prompt_meta,
    }


def rag(services: Any) -> dict[str, Any]:
    """Estado actual do índice + config RAG."""
    settings = services.context_manager.settings
    engine = services.search_engine
    return {
        "config": rag_config(services),
        "index": {
            "chunks": len(engine.chunks),
            "silos": list(engine.discipline_ids),
            "silo_count": len(engine.discipline_ids),
        },
        "catalog_enabled": settings.catalog_enabled,
        "indexed_lesson_keys_count": len(services.indexed_lesson_keys),
    }


def rag_config(services: Any) -> dict[str, Any]:
    s = services.context_manager.settings
    return {
        "candidate_k": s.retrieval_candidate_k,
        "top_k": s.retrieval_top_k,
        "max_chunks_per_source": s.retrieval_max_chunks_per_source,
        "min_score": s.retrieval_min_score,
        "min_score_margin": s.retrieval_min_score_margin,
        "min_coverage": s.retrieval_min_coverage,
        "min_coverage_weighted": s.retrieval_min_coverage_weighted,
        "min_terms": s.retrieval_min_terms,
        "retrieval_mode": s.retrieval_mode,
        "grounding_policy": s.grounding_policy,
        "chunk_words": DB_CHUNK_WORDS,
        "chunk_overlap": DB_CHUNK_OVERLAP,
        "disambiguation_enabled": s.disambiguation_enabled,
    }


def disciplines(services: Any) -> dict[str, Any]:
    registry = [
        {
            "id": d.id,
            "label": d.label,
            "command": d.command,
            "query_markers": list(d.query_markers),
        }
        for d in load_disciplines()
    ]
    return {
        "registry": registry,
        "indexed_silos": list(services.search_engine.discipline_ids),
        "catalog_enabled": services.context_manager.settings.catalog_enabled,
    }


def models(services: Any) -> dict[str, Any]:
    s = services.context_manager.settings
    return {
        "llm_provider": s.llm_provider,
        "cursor_model": s.cursor_model,
        "openrouter_models": list(s.models),
        "openrouter_temperature_fixed": getattr(s, "llm_temperature", 0.3),
        "note": "tokens_used em ACL_META conta fragmentos de stream, não tokens do provider",
    }


def metrics(services: Any) -> dict[str, Any]:
    engine = services.search_engine
    return get_recorder().metrics_snapshot(
        index_chunks=len(engine.chunks),
        index_silos=len(engine.discipline_ids),
    )


def system(services: Any) -> dict[str, Any]:
    s = services.context_manager.settings
    return {
        "product": "Kernel API",
        "llm_provider": s.llm_provider,
        "grounding_policy": s.grounding_policy,
        "global_context_mode": s.global_context_mode,
        "catalog_enabled": s.catalog_enabled,
        "project_root": str(s.project_root),
        "prompts_dir": str((s.project_root / "kernel" / "policies" / "systemPrompt")),
        "index_chunks": len(services.search_engine.chunks),
        "index_silos": list(services.search_engine.discipline_ids),
        "server_time": time.time(),
    }


def memory_session(services: Any, session_id: str) -> dict[str, Any]:
    store = services.pinned_store
    pin = store.get(session_id) if store else None
    if pin is None:
        return {"session_id": session_id, "pinned": False}
    return {
        "session_id": session_id,
        "pinned": True,
        "scope_key": pin.scope_key,
        "display_name": pin.display_name,
        "turns_left": pin.turns_left,
        "chunk_count": len(pin.chunks),
        "sources": [c.get("source") for c in pin.chunks],
    }


def health_deep(services: Any) -> dict[str, Any]:
    s = services.context_manager.settings
    engine = services.search_engine
    mysql_ok = len(engine.chunks) > 0 or bool(engine.discipline_ids)
    provider_configured = bool(
        (s.llm_provider == "cursor" and s.cursor_api_key)
        or (s.llm_provider == "openrouter" and s.openrouter_api_key)
    )
    ready = mysql_ok and provider_configured
    return {
        "status": "ready" if ready else "degraded",
        "checks": {
            "index_non_empty": mysql_ok,
            "index_chunks": len(engine.chunks),
            "index_silos": len(engine.discipline_ids),
            "provider_configured": provider_configured,
            "llm_provider": s.llm_provider,
            "catalog_enabled": s.catalog_enabled,
            "catalog_loaded": services.lesson_catalog is not None,
        },
    }
