"""Contratos HTTP do Kernel."""

from __future__ import annotations

import logging
import secrets
import time
from collections.abc import AsyncGenerator

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import StreamingResponse

from api.chat_pipeline import run_chat_pipeline
from api.security import (
    allow_public_operation,
    note_auth_failure,
    search_snippet_chars,
    verify_channel_api_bearer,
)
from kernel.disciplines.disciplines import trace_label_by_discipline
from kernel.inspect.recorder import (
    PipelineRecord,
    build_rag_view,
    get_recorder,
)
from kernel.knowledge.catalog_sync import refresh_indexed_lesson_keys_state
from kernel.knowledge.lesson_catalog import normalize_lesson_key
from kernel.memory.session_key import memory_session_key
from kernel.rag.retrieval import build_decision, select_mode
from kernel.schemas.chat import ChatRequest, ChatResponse, confidence_to_float
from kernel.schemas.search import SearchCandidate, SearchRequest, SearchResponse

log = logging.getLogger("kernelbots.api.chat")

router = APIRouter()


def _services(request: Request):
    services = getattr(request.app.state, "services", None)
    if services is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Kernel services are not configured",
        )
    return services


def _request_id(request: Request) -> str:
    rid = getattr(request.state, "request_id", None)
    if isinstance(rid, str) and rid:
        return rid
    return get_recorder().new_request_id()


def _verify_reload_bearer(request: Request) -> None:
    """Exige Authorization: Bearer igual a ACL_RELOAD_BEARER_TOKEN (CI / operadores)."""
    settings = _services(request).context_manager.settings
    expected = settings.reload_bearer_token
    if not expected:
        log.warning(
            "ACL_RELOAD_BEARER_TOKEN não configurado — /reload e /health/catalog rejeitados"
        )
        raise HTTPException(status_code=503, detail="reload token not configured")

    auth = request.headers.get("Authorization") or ""
    if not auth.startswith("Bearer "):
        note_auth_failure(request, scope="reload")
        raise HTTPException(status_code=401, detail="Authorization Bearer token required")
    token = auth[7:].strip()
    if not token or not secrets.compare_digest(token, expected):
        note_auth_failure(request, scope="reload")
        raise HTTPException(status_code=401, detail="Invalid reload bearer token")

@router.get("/health")
async def health() -> dict[str, str]:
    """Liveness para Docker/Kubernetes (sem autenticação)."""
    return {"status": "ok"}


@router.get("/api/public-config")
async def public_config(request: Request) -> dict[str, str | bool]:
    """Configuração pública do catálogo, sem segredos."""
    settings = _services(request).context_manager.settings
    return {
        "iss_lesson_base": settings.iss_public_lesson_base,
        "catalog_enabled": settings.catalog_enabled,
    }


@router.get("/api/curriculum")
async def curriculum_all(request: Request) -> dict:
    """Lista disciplinas com aulas no catálogo."""
    services = _services(request)
    catalog = services.lesson_catalog
    if catalog is None:
        raise HTTPException(status_code=503, detail="Catálogo indisponível")
    labels = trace_label_by_discipline()
    disciplines = []
    for disc in catalog.list_disciplines():
        lessons = catalog.lessons_for_discipline(disc)
        disciplines.append(
            {
                "discipline": disc,
                "label": labels.get(disc, disc),
                "lesson_count": len(lessons),
            }
        )
    return {"disciplines": disciplines}


@router.get("/api/curriculum/{discipline_id}")
async def curriculum_discipline(request: Request, discipline_id: str) -> dict:
    """Aulas de uma disciplina para o painel curricular."""
    services = _services(request)
    catalog = services.lesson_catalog
    if catalog is None:
        raise HTTPException(status_code=503, detail="Catálogo indisponível")

    disc_norm = normalize_lesson_key(discipline_id, "x").split(":", 1)[0]
    lessons = catalog.lessons_for_discipline(disc_norm)
    if not lessons:
        all_discs = set(catalog.list_disciplines())
        if disc_norm not in all_discs:
            raise HTTPException(status_code=404, detail="Disciplina não encontrada no catálogo")

    labels = trace_label_by_discipline()
    return {
        "discipline": disc_norm,
        "label": labels.get(disc_norm, disc_norm),
        "lessons": [
            {
                "slug": entry.slug,
                "title": entry.title or entry.name,
                "order": idx + 1,
            }
            for idx, entry in enumerate(lessons)
        ],
    }


@router.get("/health/catalog")
async def health_catalog(request: Request) -> dict:
    """Snapshot de catálogo vs índice (protegido; Job 4 CI)."""
    _verify_reload_bearer(request)
    services = _services(request)
    settings = services.context_manager.settings
    drift = services.catalog_drift_report or {}
    catalog_only = list(drift.get("catalog_only") or [])
    return {
        "catalog_enabled": settings.catalog_enabled,
        "indexed_lesson_keys_count": len(services.indexed_lesson_keys),
        "catalog_lesson_keys_count": int(drift.get("catalog_count") or 0),
        "catalog_only_count": int(drift.get("catalog_only_count") or len(catalog_only)),
        "catalog_only_sample": catalog_only[:10],
    }


@router.post("/chat", response_model=None)
async def chat(payload: ChatRequest, request: Request) -> ChatResponse | StreamingResponse:
    recorder = get_recorder()
    request_id = _request_id(request)
    recorder.incr("requests_total")
    recorder.incr("chat_total")
    try:
        allow_public_operation(
            request, "chat", channel=payload.channel, user_id=payload.user_id
        )
    except HTTPException:
        recorder.incr("rate_limited")
        raise
    # /reload usa Bearer de ops; restantes usam auth de canal quando exigida
    if payload.message.lower() != "/reload":
        verify_channel_api_bearer(request, channel=payload.channel)
    services = _services(request)
    pin_key = memory_session_key(payload.channel, payload.user_id, payload.session_id)
    if payload.message.lower() == "/reload":
        _verify_reload_bearer(request)
        services.search_engine.rebuild()
        _keys, keys_refreshed = refresh_indexed_lesson_keys_state(services)
        chunk_count = len(services.search_engine.chunks)
        silo_count = len(services.search_engine.discipline_ids)
        status_msg = (
            f"Índice reconstruído: {chunk_count} chunk(s) total "
            f"({silo_count} silo(s) do MySQL)."
        )
        if not keys_refreshed:
            log.warning(
                "⚠ /reload: BM25 reconstruído, mas chaves de catálogo (indexed_lesson_keys) "
                "NÃO foram atualizadas — usando snapshot anterior (%d chave(s))",
                len(_keys),
            )
            status_msg += (
                f" Aviso: chaves de catálogo não atualizadas (MySQL indisponível); "
                f"continuando com {len(_keys)} chave(s) em cache."
            )
        log.info("✅ /reload concluído — %s", status_msg)
        recorder.incr("reloads")
        recorder.put(
            PipelineRecord(
                request_id=request_id,
                created_at=time.time(),
                kind="reload",
                channel=payload.channel,
                user_id=payload.user_id,
                message_preview="/reload",
                stages=[{"name": "reload", "ok": True, "keys_refreshed": keys_refreshed}],
                response={"status": status_msg},
            )
        )

        async def _reload_stream() -> AsyncGenerator[str, None]:
            yield f"data: {status_msg}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(
            _reload_stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"},
        )

    outcome = await run_chat_pipeline(
        request,
        services,
        request_id=request_id,
        message=payload.message,
        channel=payload.channel,
        user_id=payload.user_id,
        discipline=payload.discipline,
        session_key=pin_key,
        conversation_history=[item.model_dump() for item in payload.history],
        stream=payload.stream,
        request_metadata=payload.metadata,
        response_session_id=payload.session_id,
    )
    return outcome.streaming_response or outcome.chat_response


@router.post("/search", response_model=SearchResponse)
async def search(payload: SearchRequest, request: Request) -> SearchResponse:
    recorder = get_recorder()
    request_id = _request_id(request)
    recorder.incr("requests_total")
    recorder.incr("search_total")
    try:
        allow_public_operation(
            request, "search", channel=payload.channel, user_id=payload.user_id
        )
    except HTTPException:
        recorder.incr("rate_limited")
        raise
    verify_channel_api_bearer(request, channel=payload.channel)
    services = _services(request)
    settings = services.context_manager.settings
    snippet_limit = search_snippet_chars()
    candidates = services.search_engine.search_candidates(
        payload.message,
        candidate_k=min(settings.retrieval_candidate_k, payload.top_k),
        discipline_filter=payload.discipline,
    )
    decision = build_decision(
        query=payload.message,
        candidates=candidates,
        mode=select_mode(False, False, None, False),
        min_score=settings.retrieval_min_score,
        min_score_margin=settings.retrieval_min_score_margin,
        min_coverage=settings.retrieval_min_coverage,
        min_coverage_weighted=settings.retrieval_min_coverage_weighted,
        min_terms=settings.retrieval_min_terms,
        top_k=payload.top_k,
        max_per_source=settings.retrieval_max_chunks_per_source,
        acl_retrieval_mode=settings.retrieval_mode,
        disambiguation_enabled=settings.disambiguation_enabled,
    )
    selected = decision.selected_candidates[:payload.top_k]
    rag_view = build_rag_view(candidates=tuple(candidates), decision=decision)
    recorder.put(
        PipelineRecord(
            request_id=request_id,
            created_at=time.time(),
            kind="search",
            channel=payload.channel,
            user_id=payload.user_id,
            session_id=payload.session_id,
            message_preview=payload.message[:240],
            effective_discipline=payload.discipline,
            stages=[
                {"name": "validate", "ok": True},
                {"name": "retrieval", "reason": decision.reason, "confidence": decision.confidence},
            ],
            rag=rag_view,
            response={
                "sources": [c.source for c in selected],
                "decision": "answer" if decision.allow_generation else "hard_stop",
            },
        )
    )
    return SearchResponse(
        discipline=payload.discipline,
        decision="answer" if decision.allow_generation else "hard_stop",
        reason=decision.reason,
        confidence=confidence_to_float(decision.confidence),
        sources=[candidate.source for candidate in selected],
        candidates=[
            SearchCandidate(
                source=candidate.source,
                score=candidate.raw_score,
                score_normalized=candidate.normalized_score,
                snippet=candidate.text[:snippet_limit],
            )
            for candidate in selected
        ],
        metadata={
            "user_id": payload.user_id,
            "channel": payload.channel,
            "label": None,
            "request_id": request_id,
            "session_id": payload.session_id,
        },
    )
