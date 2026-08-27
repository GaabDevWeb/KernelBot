"""API v1 (Kernel↔Orbit — ADR-0002, RF-004/RF-005): contrato multi-canal `ChannelContext`.

Endpoints expostos:
- `GET /v1/health` (liveness, sem auth)
- `POST /v1/chat` (chat com identidade de canal, idempotência, memória histórica e Group Profile)
- `POST /v1/groups/messages` (ingestão de mensagens de grupos)
- `GET /v1/groups/{platform}/{channel_id}/profile` (leitura do Group Profile)
- `POST /v1/groups/{platform}/{channel_id}/profile/refresh` (recalcula Group Profile)
- `DELETE /v1/groups/{platform}/{channel_id}/memory` (exclusão de memória do grupo)
- `GET /v1/groups/{platform}/{channel_id}/state` (leitura de estado: introduction_sent)
- `POST /v1/groups/{platform}/{channel_id}/state` (atualização de estado de apresentação)
- `GET /v1/groups/{platform}/{channel_id}/history` (busca na memória histórica do grupo)
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import JSONResponse, StreamingResponse

from api.chat_pipeline import run_chat_pipeline
from api.routes import _request_id, _services
from api.security import allow_public_operation, trace_message_preview_chars, verify_channel_api_bearer
from kernel.inspect.recorder import get_recorder
from kernel.memory.group_profile import GroupProfileAnalyzer
from kernel.memory.session_key import v1_memory_key
from kernel.group.invocation import (
    GROUP_INTRODUCTION_ANSWER,
    TRANSCRIPT_USER_MARKER,
    is_whatsapp_group,
    parse_invocation_from_metadata,
)
from kernel.schemas.chat import ChatRequestV1, ChatResponse, confidence_to_float
from kernel.schemas.group import GroupMessagesBatchRequest, GroupStateUpdateRequest
from kernel.trace import emit_kernel, resolve_trace_id
from kernel.trace.stages import (
    KERNEL_ERROR,
    KERNEL_IDEMPOTENCY_CHECK,
    KERNEL_PIN_LOADED,
    KERNEL_REQUEST_RECEIVED,
    KERNEL_RESPONSE_RETURNED,
    KERNEL_TRANSCRIPT_LOADED,
    KERNEL_CONTEXTUAL_INVOCATION,
)
from kernel.users.service import is_user_blocked, touch_user_session

router = APIRouter(prefix="/v1")
log = logging.getLogger("kernelbots.api.v1")


@router.get("/health")
async def health_v1() -> dict[str, str]:
    """Liveness v1 (sem autenticação — paridade com `GET /health` legado)."""
    return {"status": "ok"}


@router.post("/chat", response_model=None)
async def chat_v1(payload: ChatRequestV1, request: Request) -> ChatResponse | StreamingResponse:
    recorder = get_recorder()
    request_id = _request_id(request)
    recorder.incr("requests_total")
    recorder.incr("chat_total")

    channel = payload.context.platform
    user_id = payload.context.user_id
    channel_id = payload.context.channel_id
    trace_id = resolve_trace_id(request.headers.get("X-Trace-Id"))
    request.state.trace_id = trace_id

    # Auth/rate-limit ANTES de qualquer leitura ou limpeza de estado
    try:
        allow_public_operation(request, "chat", channel=channel, user_id=user_id)
    except HTTPException:
        recorder.incr("rate_limited")
        raise
    verify_channel_api_bearer(request, channel=channel)

    if is_user_blocked(channel, user_id):
        recorder.incr("blocked_user")
        emit_kernel(
            KERNEL_ERROR,
            trace_id=trace_id,
            data={
                "request_id": request_id,
                "error": "user_blocked",
                "platform": channel,
                "user_id": user_id,
            },
        )
        raise HTTPException(status_code=403, detail="Utilizador bloqueado.")

    services = _services(request)

    # --- Idempotência ---
    raw_msg_id = request.headers.get("X-Message-Id") or payload.metadata.get("message_id")
    msg_id = str(raw_msg_id).strip() if raw_msg_id else None
    idempotency_key = (
        f"{channel}:{channel_id}:{msg_id}" if msg_id else None
    )

    if idempotency_key and getattr(services, "idempotency_store", None):
        can_proceed, rec = services.idempotency_store.claim(idempotency_key, trace_id=trace_id)
        if not can_proceed and rec is not None:
            if rec.status == "completed" and rec.response_data is not None:
                emit_kernel(
                    KERNEL_IDEMPOTENCY_CHECK,
                    trace_id=trace_id,
                    data={"hit": True, "status": "completed", "message_id": msg_id},
                )
                if isinstance(rec.response_data, ChatResponse):
                    return rec.response_data
                return ChatResponse(**rec.response_data)
            if rec.status == "processing":
                emit_kernel(
                    KERNEL_IDEMPOTENCY_CHECK,
                    trace_id=trace_id,
                    data={"hit": True, "status": "processing", "message_id": msg_id},
                )
                raise HTTPException(status_code=409, detail="Mensagem já em processamento.")
        else:
            emit_kernel(
                KERNEL_IDEMPOTENCY_CHECK,
                trace_id=trace_id,
                data={"hit": False, "message_id": msg_id},
            )

    v1_key = v1_memory_key(
        payload.context.platform,
        payload.context.user_id,
        payload.context.channel_id,
        payload.context.session_id,
    )

    touch_user_session(
        platform=payload.context.platform,
        user_id=user_id,
        channel_id=payload.context.channel_id,
        session_id=payload.context.session_id,
        memory_key=v1_key,
        increment_messages=0,
    )

    # Gravar mensagem recebida no histórico persistente do grupo se aplicável
    if services.group_memory_store and channel_id and (payload.message or "").strip():
        try:
            services.group_memory_store.record_message(
                platform=channel,
                channel_id=channel_id,
                message_id=msg_id or f"m_{int(time.time()*1000)}",
                user_id=user_id,
                sender_name=str(payload.metadata.get("sender_name") or ""),
                content=payload.message,
                metadata=payload.metadata,
            )
            # Batch update trigger em background
            msg_count = services.group_memory_store.count_messages(channel, channel_id)
            threshold = getattr(services.context_manager.settings, "group_profile_update_threshold", 50)
            if msg_count > 0 and msg_count % threshold == 0:
                asyncio.create_task(
                    _async_update_group_profile(services.group_memory_store, channel, channel_id)
                )
        except Exception as exc:
            log.warning("Falha ao registrar mensagem no group memory store: %s", exc)

    emit_kernel(
        KERNEL_REQUEST_RECEIVED,
        trace_id=trace_id,
        data={
            "request_id": request_id,
            "platform": channel,
            "user_id": user_id,
            "channel_id": payload.context.channel_id,
            "reset_context": bool(payload.reset_context),
            "message_chars": len(payload.message or ""),
            "message_preview": (payload.message or "")[: trace_message_preview_chars()],
        },
    )

    if payload.reset_context:
        services.pinned_store.clear(v1_key)
        services.transcript_store.clear(v1_key)

    # `payload.history` (body v1) é aceite mas SEMPRE ignorado (G7)
    history_in = services.transcript_store.get(v1_key)
    emit_kernel(
        KERNEL_TRANSCRIPT_LOADED,
        trace_id=trace_id,
        data={
            "turns": len(history_in),
            "session_key_chars": len(v1_key),
            "transcript_preview": [
                {
                    "role": str(t.get("role") or ""),
                    "content": str(t.get("content") or "")[:400],
                }
                for t in history_in[-8:]
            ],
        },
    )

    pinned = services.pinned_store.get(v1_key)
    emit_kernel(
        KERNEL_PIN_LOADED,
        trace_id=trace_id,
        data={
            "pinned_active": pinned is not None,
            "turns_left": getattr(pinned, "turns_left", None) if pinned else None,
            "chunks": len(getattr(pinned, "chunks", []) or []) if pinned else 0,
        },
    )

    parsed_invocation = parse_invocation_from_metadata(
        payload.metadata,
        channel_id=channel_id or "",
        message=payload.message,
    )
    if parsed_invocation.is_contextual:
        recent = parsed_invocation.recent_context
        emit_kernel(
            KERNEL_CONTEXTUAL_INVOCATION,
            trace_id=trace_id,
            data={
                "request_id": request_id,
                "platform": channel,
                "user_id": user_id,
                "channel_id": channel_id,
                "invocation_type": parsed_invocation.type,
                "explicit_text": parsed_invocation.explicit_text,
                "recent_messages_count": len(recent),
                "no_useful_context": parsed_invocation.no_useful_context,
            },
        )

    # Primeira apresentação em grupo (@orbit sem texto)
    if (
        parsed_invocation.type == "contextual_invocation"
        and is_whatsapp_group(channel_id)
        and services.group_memory_store
        and not payload.reset_context
    ):
        group_state = services.group_memory_store.get_group_state(channel, channel_id)
        if not group_state.get("introduction_sent"):
            if services.group_memory_store.try_claim_introduction(channel, channel_id):
                intro = ChatResponse(
                    answer=GROUP_INTRODUCTION_ANSWER,
                    discipline=None,
                    sources=[],
                    confidence=confidence_to_float("high"),
                    metadata={
                        "user_id": user_id,
                        "channel": channel,
                        "session_id": payload.context.session_id,
                        "request_metadata": payload.metadata,
                        "request_id": request_id,
                        "trace_id": trace_id,
                        "introduction": True,
                    },
                )
                services.transcript_store.append_pair(
                    v1_key,
                    TRANSCRIPT_USER_MARKER,
                    intro.answer,
                    services.context_manager.settings.transcript_max_turns,
                )
                if idempotency_key and getattr(services, "idempotency_store", None):
                    services.idempotency_store.complete(
                        idempotency_key, intro, trace_id=trace_id
                    )
                emit_kernel(
                    KERNEL_RESPONSE_RETURNED,
                    trace_id=trace_id,
                    data={
                        "request_id": request_id,
                        "answer_chars": len(intro.answer),
                        "introduction": True,
                    },
                )
                return intro

    try:
        outcome = await run_chat_pipeline(
            request,
            services,
            request_id=request_id,
            message=payload.message,
            channel=channel,
            channel_id=channel_id,
            user_id=user_id,
            discipline=payload.discipline,
            session_key=v1_key,
            conversation_history=history_in,
            stream=payload.stream,
            request_metadata=payload.metadata,
            response_session_id=payload.context.session_id,
            trace_id=trace_id,
        )
    except Exception as exc:
        if idempotency_key and getattr(services, "idempotency_store", None):
            services.idempotency_store.fail(idempotency_key)
        emit_kernel(
            KERNEL_ERROR,
            trace_id=trace_id,
            data={"error": f"{type(exc).__name__}: {exc}", "request_id": request_id},
        )
        raise

    if outcome.chat_response is not None and outcome.answer:
        transcript_user = (payload.message or "").strip() or TRANSCRIPT_USER_MARKER
        services.transcript_store.append_pair(
            v1_key,
            transcript_user,
            outcome.answer,
            services.context_manager.settings.transcript_max_turns,
        )
        touch_user_session(
            platform=payload.context.platform,
            user_id=user_id,
            channel_id=payload.context.channel_id,
            session_id=payload.context.session_id,
            memory_key=v1_key,
            increment_messages=1,
        )
        if outcome.chat_response.metadata is not None:
            outcome.chat_response.metadata["trace_id"] = trace_id

        # Salvar resposta na idempotência
        if idempotency_key and getattr(services, "idempotency_store", None):
            services.idempotency_store.complete(
                idempotency_key,
                outcome.chat_response,
                trace_id=trace_id,
            )

        emit_kernel(
            KERNEL_RESPONSE_RETURNED,
            trace_id=trace_id,
            data={
                "request_id": request_id,
                "answer_chars": len(outcome.answer),
                "discipline": outcome.chat_response.discipline,
            },
        )

    return outcome.streaming_response or outcome.chat_response


# --- Helpers de background ---

async def _async_update_group_profile(store, platform: str, channel_id: str) -> None:
    try:
        msgs = store.get_recent_messages(platform, channel_id, limit=200)
        existing = store.get_group_profile(platform, channel_id)
        existing_prof = GroupProfile.from_dict(existing) if existing else None
        new_prof = GroupProfileAnalyzer.extract_profile(platform, channel_id, msgs, existing_profile=existing_prof)
        store.update_group_profile(platform, channel_id, new_prof.to_dict(), message_count=len(msgs))
    except Exception as exc:
        log.warning(
            "Falha ao actualizar Group Profile em background | platform=%s channel_id=%s: %s",
            platform,
            channel_id,
            exc,
        )


# --- Endpoints de Gestão de Memória de Grupo ---

@router.post("/groups/messages")
async def ingest_group_messages(
    payload: GroupMessagesBatchRequest,
    request: Request,
) -> dict[str, Any]:
    """Ingere lote de mensagens do grupo para indexação histórica."""
    allow_public_operation(request, "groups", channel=payload.platform)
    verify_channel_api_bearer(request, channel=payload.platform)
    services = _services(request)
    if not services.group_memory_store:
        raise HTTPException(status_code=503, detail="Group Memory Store desativado.")

    raw_list = [
        {
            "platform": payload.platform,
            "channel_id": payload.channel_id,
            "message_id": m.message_id,
            "user_id": m.user_id,
            "sender_name": m.sender_name,
            "timestamp": m.timestamp,
            "content": m.content,
            "reply_to": m.reply_to,
            "metadata": m.metadata,
        }
        for m in payload.messages
    ]
    inserted = services.group_memory_store.record_messages_batch(raw_list)
    return {
        "ok": True,
        "platform": payload.platform,
        "channel_id": payload.channel_id,
        "messages_received": len(payload.messages),
        "messages_inserted": inserted,
    }


@router.get("/groups/{platform}/{channel_id}/profile")
async def get_group_profile_endpoint(
    platform: str,
    channel_id: str,
    request: Request,
) -> dict[str, Any]:
    """Retorna o perfil semântico e social do grupo."""
    allow_public_operation(request, "groups", channel=platform)
    verify_channel_api_bearer(request, channel=platform)
    services = _services(request)
    if not services.group_memory_store:
        raise HTTPException(status_code=503, detail="Group Memory Store desativado.")

    profile = services.group_memory_store.get_group_profile(platform, channel_id)
    state = services.group_memory_store.get_group_state(platform, channel_id)
    stats = services.group_memory_store.get_stats(platform, channel_id)
    return {
        "platform": platform,
        "channel_id": channel_id,
        "profile": profile,
        "state": state,
        "stats": stats,
    }


@router.post("/groups/{platform}/{channel_id}/profile/refresh")
async def refresh_group_profile_endpoint(
    platform: str,
    channel_id: str,
    request: Request,
) -> dict[str, Any]:
    """Recalcula imediatamente o Group Profile a partir do histórico."""
    allow_public_operation(request, "groups", channel=platform)
    verify_channel_api_bearer(request, channel=platform)
    services = _services(request)
    if not services.group_memory_store:
        raise HTTPException(status_code=503, detail="Group Memory Store desativado.")

    msgs = services.group_memory_store.get_recent_messages(platform, channel_id, limit=300)
    existing = services.group_memory_store.get_group_profile(platform, channel_id)
    existing_prof = GroupProfile.from_dict(existing) if existing else None
    new_prof = GroupProfileAnalyzer.extract_profile(platform, channel_id, msgs, existing_profile=existing_prof)
    services.group_memory_store.update_group_profile(platform, channel_id, new_prof.to_dict(), message_count=len(msgs))
    return {
        "ok": True,
        "platform": platform,
        "channel_id": channel_id,
        "profile": new_prof.to_dict(),
        "messages_analyzed": len(msgs),
    }


@router.delete("/groups/{platform}/{channel_id}/memory")
async def delete_group_memory_endpoint(
    platform: str,
    channel_id: str,
    request: Request,
) -> dict[str, Any]:
    """Exclui mensagens e profile de um grupo específico de forma isolada."""
    allow_public_operation(request, "groups", channel=platform)
    verify_channel_api_bearer(request, channel=platform)
    services = _services(request)
    if not services.group_memory_store:
        raise HTTPException(status_code=503, detail="Group Memory Store desativado.")

    res = services.group_memory_store.delete_group_memory(platform, channel_id)
    return {"ok": True, **res}


@router.get("/groups/{platform}/{channel_id}/state")
async def get_group_state_endpoint(
    platform: str,
    channel_id: str,
    request: Request,
) -> dict[str, Any]:
    """Retorna estado de apresentação do grupo (introduction_sent)."""
    allow_public_operation(request, "groups", channel=platform)
    verify_channel_api_bearer(request, channel=platform)
    services = _services(request)
    if not services.group_memory_store:
        return {"platform": platform, "channel_id": channel_id, "introduction_sent": False}

    state = services.group_memory_store.get_group_state(platform, channel_id)
    return {"platform": platform, "channel_id": channel_id, **state}


@router.post("/groups/{platform}/{channel_id}/state")
async def set_group_state_endpoint(
    platform: str,
    channel_id: str,
    payload: GroupStateUpdateRequest,
    request: Request,
) -> dict[str, Any]:
    """Atualiza estado de apresentação do grupo."""
    allow_public_operation(request, "groups", channel=platform)
    verify_channel_api_bearer(request, channel=platform)
    services = _services(request)
    if not services.group_memory_store:
        raise HTTPException(status_code=503, detail="Group Memory Store desativado.")

    services.group_memory_store.set_group_state(platform, channel_id, payload.introduction_sent)
    return {
        "ok": True,
        "platform": platform,
        "channel_id": channel_id,
        "introduction_sent": payload.introduction_sent,
    }


@router.get("/groups/{platform}/{channel_id}/history")
async def search_group_history_endpoint(
    platform: str,
    channel_id: str,
    request: Request,
    query: str = Query(default="", min_length=0),
    top_k: int = Query(default=5, ge=1, le=50),
) -> dict[str, Any]:
    """Busca mensagens históricas via BM25 + recência."""
    allow_public_operation(request, "groups", channel=platform)
    verify_channel_api_bearer(request, channel=platform)
    services = _services(request)
    if not services.group_memory_store:
        raise HTTPException(status_code=503, detail="Group Memory Store desativado.")

    if query.strip():
        results = services.group_memory_store.search_historical(
            platform, channel_id, query, top_k=top_k
        )
        items = [
            {
                "message_id": r.message_id,
                "sender_name": r.sender_name,
                "user_id": r.user_id,
                "content": r.content,
                "timestamp": r.timestamp,
                "bm25_score": round(r.bm25_score, 4),
                "recency_factor": round(r.recency_factor, 4),
                "final_score": round(r.final_score, 4),
            }
            for r in results
        ]
    else:
        recent = services.group_memory_store.get_recent_messages(platform, channel_id, limit=top_k)
        items = [
            {
                "message_id": m.message_id,
                "sender_name": m.sender_name,
                "user_id": m.user_id,
                "content": m.content,
                "timestamp": m.timestamp,
            }
            for m in recent
        ]

    return {
        "platform": platform,
        "channel_id": channel_id,
        "query": query,
        "count": len(items),
        "results": items,
    }
