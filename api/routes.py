"""Rotas GET / e POST /chat."""

from __future__ import annotations

import logging
import re

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, StreamingResponse

from collections.abc import AsyncGenerator

log = logging.getLogger("kernelbots.api.chat")

router = APIRouter()

_SESSION_ID_RE = re.compile(r"^[A-Za-z0-9_-]{8,128}$")


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

    if user_message.strip().lower() == "/reload":
        log.info("🔄 Comando /reload recebido — reconstruindo índice BM25...")
        services.search_engine.rebuild()
        chunk_count = len(services.search_engine.chunks)
        db_count = sum(1 for c in services.search_engine.chunks if c.get("source", "").startswith("db:"))
        md_count = chunk_count - db_count
        status = (
            f"Índice reconstruído: {chunk_count} chunk(s) total "
            f"({md_count} de arquivos .md + {db_count} do MySQL)."
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
    )

    return StreamingResponse(
        services.chat_provider.stream_response(built.messages, trace=built.trace),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
