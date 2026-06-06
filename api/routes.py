"""Rotas GET / e POST /chat."""

from __future__ import annotations

import logging
import re
import secrets

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, StreamingResponse

from collections.abc import AsyncGenerator

from engine.context import ConversationHistoryError, _normalize_conversation_history

log = logging.getLogger("kernelbots.api.chat")

router = APIRouter()

_SESSION_ID_RE = re.compile(r"^[A-Za-z0-9_-]{8,128}$")


def _verify_reload_bearer(request: Request) -> None:
    """Exige Authorization: Bearer igual a ACL_RELOAD_BEARER_TOKEN (CI / operadores)."""
    settings = request.app.state.services.context_manager.settings
    expected = settings.reload_bearer_token
    if not expected:
        log.warning(
            "ACL_RELOAD_BEARER_TOKEN não configurado — /reload e /health/catalog rejeitados"
        )
        raise HTTPException(status_code=503, detail="reload token not configured")

    auth = request.headers.get("Authorization") or ""
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization Bearer token required")
    token = auth[7:].strip()
    if not token or not secrets.compare_digest(token, expected):
        raise HTTPException(status_code=401, detail="Invalid reload bearer token")


@router.get("/health")
async def health() -> dict[str, str]:
    """Liveness para Docker/Kubernetes (sem autenticação)."""
    return {"status": "ok"}


@router.get("/health/catalog")
async def health_catalog(request: Request) -> dict:
    """Snapshot de catálogo vs índice (protegido; Job 4 CI)."""
    _verify_reload_bearer(request)
    services = request.app.state.services
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


@router.get("/", response_class=HTMLResponse)
async def home(request: Request) -> HTMLResponse:
    client_ip = request.client.host if request.client else "desconhecido"
    log.info(f"🌐 Interface carregada — cliente: {client_ip}")
    templates = request.app.state.templates
    return templates.TemplateResponse(request=request, name="index.html")


@router.post("/chat")
async def chat(request: Request) -> StreamingResponse:
    client_ip = request.client.host if request.client else "desconhecido"
    services = request.app.state.services

    try:
        data = await request.json()
    except Exception:
        log.warning(f"⚠  Requisição inválida de {client_ip} — corpo não é JSON válido")
        raise HTTPException(status_code=400, detail="JSON inválido no corpo da requisição.")

    user_message: str = (data.get("message") or "").strip()
    if not user_message:
        log.warning(f"⚠  Requisição de {client_ip} com campo 'message' ausente ou vazio")
        raise HTTPException(status_code=400, detail="Campo 'message' ausente ou vazio.")

    raw_discipline = data.get("discipline")
    discipline: str | None
    if raw_discipline is None:
        discipline = None
    elif isinstance(raw_discipline, str):
        discipline = raw_discipline.strip() or None
    else:
        log.warning(f"⚠  Requisição de {client_ip} — campo 'discipline' com tipo inválido")
        raise HTTPException(
            status_code=400,
            detail="Campo 'discipline' deve ser string ou omitido.",
        )

    raw_session = data.get("session_id")
    session_id: str | None
    if raw_session is None:
        session_id = None
    elif isinstance(raw_session, str):
        s = raw_session.strip()
        if not s:
            session_id = None
        elif not _SESSION_ID_RE.match(s):
            log.warning(f"⚠  Requisição de {client_ip} — session_id com formato inválido")
            raise HTTPException(
                status_code=400,
                detail="Campo 'session_id' inválido (use 8–128 caracteres: letras, dígitos, _ ou -).",
            )
        else:
            session_id = s
    else:
        log.warning(f"⚠  Requisição de {client_ip} — campo 'session_id' com tipo inválido")
        raise HTTPException(
            status_code=400,
            detail="Campo 'session_id' deve ser string ou omitido.",
        )

    raw_history = data.get("history")
    if raw_history is not None and not isinstance(raw_history, list):
        log.warning(f"⚠  Requisição de {client_ip} — campo 'history' com tipo inválido")
        raise HTTPException(
            status_code=400,
            detail="Campo 'history' deve ser uma lista ou omitido.",
        )
    try:
        conversation_history = _normalize_conversation_history(raw_history)
    except ConversationHistoryError as exc:
        log.warning(f"⚠  Requisição de {client_ip} — history inválido: {exc}")
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if user_message.strip().lower() == "/reload":
        _verify_reload_bearer(request)

        from engine.catalog_sync import refresh_indexed_lesson_keys_state

        log.info("🔄 Comando /reload recebido — reconstruindo índice BM25...")
        services.search_engine.rebuild()
        _keys, keys_refreshed = refresh_indexed_lesson_keys_state(services)
        chunk_count = len(services.search_engine.chunks)
        silo_count = len(services.search_engine.discipline_ids)
        status = (
            f"Índice reconstruído: {chunk_count} chunk(s) total "
            f"({silo_count} silo(s) do MySQL)."
        )
        if not keys_refreshed:
            log.warning(
                "⚠ /reload: BM25 reconstruído, mas chaves de catálogo (indexed_lesson_keys) "
                "NÃO foram atualizadas — usando snapshot anterior (%d chave(s))",
                len(_keys),
            )
            status += (
                f" Aviso: chaves de catálogo não atualizadas (MySQL indisponível); "
                f"continuando com {len(_keys)} chave(s) em cache."
            )
        log.info("✅ /reload concluído — %s", status)

        async def _reload_stream() -> AsyncGenerator[str, None]:
            yield f"data: {status}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(
            _reload_stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"},
        )

    built = services.context_manager.build_messages(
        user_message,
        discipline_filter=discipline,
        session_id=session_id,
        conversation_history=conversation_history,
    )

    return StreamingResponse(
        services.chat_provider.stream_response(
            built.messages,
            trace=built.trace,
            decision=built.decision,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
