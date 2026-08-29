"""Pipeline comum de chat (build_messages → provider → stream/aggregate).

Inclui emissão Flight Recorder (PROMPT_BUILT, forensics, performance).
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from fastapi import Request
from fastapi.responses import StreamingResponse

from kernel.inspect.recorder import (
    PipelineRecord,
    build_context_view,
    build_rag_view,
    get_recorder,
    maybe_store_prompt,
)
from kernel.orchestrator.context import BuildMessagesResult
from kernel.schemas.chat import ChatResponse, confidence_to_float
from kernel.trace import emit_kernel, get_trace_store
from kernel.trace.forensics import (
    build_performance_map,
    build_prompt_forensics,
    build_rag_forensics,
    build_tokens_forensics,
)
from kernel.trace.health import sample_system_metrics
from kernel.trace.stages import (
    KERNEL_CALENDAR_LOOKUP,
    KERNEL_ERROR,
    KERNEL_GROUP_MEMORY_LOOKUP,
    KERNEL_GROUP_PROFILE_LOADED,
    KERNEL_LLM_FINISHED,
    KERNEL_LLM_STARTED,
    KERNEL_PROMPT_BUILT,
    KERNEL_RAG_FINISHED,
    KERNEL_RAG_STARTED,
    KERNEL_RESPONSE_GENERATED,
    KERNEL_TEMPORAL_CONTEXT,
)

_SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "X-Accel-Buffering": "no",
    "Connection": "keep-alive",
}


def _context_snapshot_from_trace(trace_meta, conversation_history) -> dict | None:
    """Resumo das camadas de contexto para o snapshot/painel (sem segredos)."""
    if (
        trace_meta.temporal_context is None
        and not trace_meta.identity_active
        and not getattr(trace_meta, "domain_router_enabled", False)
    ):
        return None
    turns_used = (
        trace_meta.transcript_turns_used
        if getattr(trace_meta, "transcript_turns_used", None) is not None
        else len(conversation_history or [])
    )
    snapshot: dict = {
        "identity_active": trace_meta.identity_active,
        "institutional_files": list(trace_meta.institutional_files),
        "temporal": trace_meta.temporal_context,
        "temporal_intent": trace_meta.temporal_intent,
        "rag_skipped": trace_meta.rag_skipped,
        "transcript_turns_used": turns_used,
        "rag_sources_used": list(trace_meta.sources),
    }
    if trace_meta.calendar_context is not None:
        snapshot["calendar_events_used"] = trace_meta.calendar_context.get(
            "events_used", []
        )
    elif getattr(trace_meta, "router_enabled", False):
        snapshot["calendar_events_used"] = []
    if getattr(trace_meta, "group_memory_used", False):
        snapshot["group_memory_used"] = True
        snapshot["group_memory_hits_count"] = len(getattr(trace_meta, "group_memory_hits", ()) or ())
    if getattr(trace_meta, "group_profile_active", False):
        snapshot["group_profile_active"] = True
        snapshot["group_profile_topics"] = list(getattr(trace_meta, "group_profile_topics", ()) or ())
    if getattr(trace_meta, "router_enabled", False):
        snapshot["router_enabled"] = True
        snapshot["context_profile"] = trace_meta.context_profile
        snapshot["rag_skip_reason"] = trace_meta.rag_skip_reason
        snapshot["include_institutional"] = trace_meta.include_institutional
        snapshot["include_calendar"] = trace_meta.include_calendar
        snapshot["transcript_turns_requested"] = trace_meta.transcript_turns_requested
        snapshot["router_reasons"] = list(trace_meta.router_reasons or ())
    if getattr(trace_meta, "domain_router_enabled", False):
        snapshot["domain_router_enabled"] = True
        snapshot["selected_domain"] = getattr(trace_meta, "selected_domain", None)
        snapshot["domain_confidence"] = getattr(trace_meta, "domain_confidence", None)
        snapshot["domain_retrieval_scope"] = list(
            getattr(trace_meta, "domain_retrieval_scope", ()) or ()
        )
        snapshot["domain_fallback"] = getattr(trace_meta, "domain_fallback", False)
        snapshot["domain_multi"] = getattr(trace_meta, "domain_multi", False)
        snapshot["domain_candidates"] = [
            dict(c) for c in (getattr(trace_meta, "domain_candidates", ()) or ())
        ]
        snapshot["domain_router_latency_ms"] = getattr(
            trace_meta, "domain_router_latency_ms", None
        )
    return snapshot


@dataclass
class ChatPipelineOutcome:
    """Resultado do pipeline: exactamente um de `streaming_response`/`chat_response` é não-`None`."""

    built: BuildMessagesResult
    answer: str | None
    metadata: dict | None
    streaming_response: StreamingResponse | None
    chat_response: ChatResponse | None


async def run_chat_pipeline(
    request: Request,
    services,
    *,
    request_id: str,
    message: str,
    channel: str,
    user_id: str,
    discipline: str | None,
    session_key: str | None,
    conversation_history: list[dict[str, str]],
    stream: bool,
    request_metadata: dict | None,
    response_session_id: str | None,
    pipeline_kind: str = "chat",
    trace_id: str | None = None,
    channel_id: str | None = None,
    top_k: int | None = None,
    model: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> ChatPipelineOutcome:
    del request
    recorder = get_recorder()
    tid = (trace_id or "").strip() or None
    t_pipeline0 = time.perf_counter()
    timings: dict[str, float | None] = {}

    if tid:
        emit_kernel(
            KERNEL_RAG_STARTED,
            trace_id=tid,
            data={"request_id": request_id, "query": message[:500]},
        )

    t_rag0 = time.perf_counter()
    try:
        built = services.context_manager.build_messages(
            message,
            discipline_filter=discipline,
            session_id=session_key,
            conversation_history=conversation_history,
            top_k=top_k,
            request_metadata=request_metadata,
            channel_id=channel_id,
        )
    except Exception as exc:
        recorder.incr("chat_errors")
        recorder.put(
            PipelineRecord(
                request_id=request_id,
                created_at=time.time(),
                kind=pipeline_kind,
                channel=channel,
                user_id=user_id,
                session_id=response_session_id,
                message_preview=message[:240],
                error=f"{type(exc).__name__}: {exc}",
                stages=[{"name": "build_messages", "ok": False}],
            )
        )
        if tid:
            emit_kernel(
                KERNEL_ERROR,
                trace_id=tid,
                data={"stage": "RAG", "error": f"{type(exc).__name__}: {exc}"},
            )
        raise
    timings["rag_total_ms"] = (time.perf_counter() - t_rag0) * 1000.0
    timings["bm25_ms"] = timings["rag_total_ms"]  # BM25 está dentro de build_messages

    # Contexto em camadas: eventos dedicados quando os providers estão ativos.
    trace_meta = built.trace
    if tid and trace_meta.temporal_context is not None:
        temporal_data = {
            **trace_meta.temporal_context,
            "intent": trace_meta.temporal_intent,
            "rag_skipped": trace_meta.rag_skipped,
            "status": "success",
        }
        if getattr(trace_meta, "router_enabled", False):
            temporal_data["context_profile"] = trace_meta.context_profile
            temporal_data["rag_skip_reason"] = trace_meta.rag_skip_reason
            temporal_data["include_institutional"] = trace_meta.include_institutional
            temporal_data["include_calendar"] = trace_meta.include_calendar
            temporal_data["institutional_files"] = list(
                trace_meta.institutional_files or ()
            )
            temporal_data["transcript_turns_requested"] = (
                trace_meta.transcript_turns_requested
            )
            temporal_data["transcript_turns_used"] = trace_meta.transcript_turns_used
            temporal_data["router_reasons"] = list(trace_meta.router_reasons or ())
        emit_kernel(
            KERNEL_TEMPORAL_CONTEXT,
            trace_id=tid,
            data=temporal_data,
        )
    if tid and trace_meta.calendar_context is not None:
        emit_kernel(
            KERNEL_CALENDAR_LOOKUP,
            trace_id=tid,
            data={**trace_meta.calendar_context, "status": "success"},
        )
    if tid and getattr(trace_meta, "group_memory_used", False):
        emit_kernel(
            KERNEL_GROUP_MEMORY_LOOKUP,
            trace_id=tid,
            data={
                "hits_count": len(trace_meta.group_memory_hits),
                "hits": list(trace_meta.group_memory_hits)[:5],
                "status": "success",
            },
        )
    if tid and getattr(trace_meta, "group_profile_active", False):
        emit_kernel(
            KERNEL_GROUP_PROFILE_LOADED,
            trace_id=tid,
            data={
                "topics": list(trace_meta.group_profile_topics),
                "status": "success",
            },
        )

    rag_forensics = build_rag_forensics(query=message, built=built)
    if tid:
        emit_kernel(
            KERNEL_RAG_FINISHED,
            trace_id=tid,
            data={
                **{k: rag_forensics[k] for k in ("query", "reason", "confidence", "sources", "discipline") if k in rag_forensics},
                "candidates": len(built.candidates_considered),
                "normalized_query": rag_forensics.get("normalized_query"),
                "duration_ms": timings["rag_total_ms"],
                "status": "success",
            },
        )

    t_prompt0 = time.perf_counter()
    pin = services.pinned_store.get(session_key) if session_key else None
    prompt_forensics = build_prompt_forensics(
        built.messages,
        transcript=conversation_history,
        pin=pin,
    )
    context_snapshot = _context_snapshot_from_trace(trace_meta, conversation_history)
    if context_snapshot:
        prompt_forensics["context"] = context_snapshot
    timings["prompt_build_ms"] = (time.perf_counter() - t_prompt0) * 1000.0

    if tid:
        emit_kernel(
            KERNEL_PROMPT_BUILT,
            trace_id=tid,
            data={
                "prompt_chars": prompt_forensics.get("prompt_chars"),
                "prompt_tokens_est": prompt_forensics.get("prompt_tokens_est"),
                "roles": prompt_forensics.get("roles"),
                "stored_full": prompt_forensics.get("stored_full"),
                "duration_ms": timings["prompt_build_ms"],
                "status": "success",
            },
        )

    prompt_stored, prompt_meta = maybe_store_prompt(built.messages)
    rag_view = build_rag_view(
        candidates=built.candidates_considered,
        decision=built.decision,
    )
    context_view = build_context_view(built.trace, built.messages)
    record = PipelineRecord(
        request_id=request_id,
        created_at=time.time(),
        kind=pipeline_kind,
        channel=channel,
        user_id=user_id,
        session_id=response_session_id,
        message_preview=message[:240],
        effective_discipline=built.effective_discipline or discipline,
        stages=[
            {"name": "validate", "ok": True},
            {
                "name": "scope",
                "discipline_request": discipline,
                "discipline_effective": built.effective_discipline,
                "label": built.trace.label,
            },
            {
                "name": "retrieval",
                "reason": built.trace.reason,
                "confidence": built.trace.confidence,
                "candidates": len(built.candidates_considered),
            },
            {
                "name": "assemble",
                "system_chars": context_view["system_chars"],
                "history_turns": context_view["history_turns_in_prompt"],
            },
            {"name": "provider", "stream": stream},
        ],
        rag=rag_view,
        context=context_view,
        prompt=prompt_stored,
        prompt_meta=prompt_meta,
    )

    if tid:
        emit_kernel(KERNEL_LLM_STARTED, trace_id=tid, data={"stream": stream, "status": "success"})

    if stream:
        stream_gen = services.chat_provider.stream_response(
            built.messages,
            trace=built.trace,
            decision=built.decision,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        recorder.put(record)
        streaming_response = StreamingResponse(
            stream_gen,
            media_type="text/event-stream",
            headers=dict(_SSE_HEADERS),
        )
        return ChatPipelineOutcome(
            built=built,
            answer=None,
            metadata=None,
            streaming_response=streaming_response,
            chat_response=None,
        )

    t_llm0 = time.perf_counter()
    try:
        answer, metadata = await services.chat_provider.complete_response(
            built.messages,
            trace=built.trace,
            decision=built.decision,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    except Exception as exc:
        if tid:
            emit_kernel(
                KERNEL_ERROR,
                trace_id=tid,
                data={"stage": "LLM", "error": f"{type(exc).__name__}: {exc}", "status": "error"},
            )
        raise
    timings["llm_ms"] = (time.perf_counter() - t_llm0) * 1000.0
    timings["response_build_ms"] = 0.0
    timings["total_ms"] = (time.perf_counter() - t_pipeline0) * 1000.0

    if tid:
        emit_kernel(
            KERNEL_LLM_FINISHED,
            trace_id=tid,
            data={
                "tokens_used_fragments": metadata.get("tokens_used"),
                "llm_called": metadata.get("llm_called"),
                "duration_ms": timings["llm_ms"],
                "status": "success",
            },
        )

    metadata.update(
        {
            "user_id": user_id,
            "channel": channel,
            "session_id": response_session_id,
            "request_metadata": request_metadata,
            "request_id": request_id,
        }
    )
    if tid:
        metadata["trace_id"] = tid

    effective_discipline = discipline
    if not effective_discipline:
        for detail in built.trace.source_details or ():
            disc = detail.get("discipline") if isinstance(detail, dict) else None
            if disc:
                effective_discipline = str(disc)
                break
    record.provider = {
        "llm_called": metadata.get("llm_called"),
        "tokens_used_fragments": metadata.get("tokens_used"),
        "prompt_tokens": metadata.get("prompt_tokens"),
        "completion_tokens": metadata.get("completion_tokens"),
        "total_tokens": metadata.get("total_tokens"),
        "model": metadata.get("model"),
        "provider_stream": metadata.get("provider_stream", True),
        "decision": metadata.get("decision"),
        "reason": metadata.get("reason"),
        "grounding_policy": metadata.get("grounding_policy"),
        "note": (
            "tokens do provider OpenRouter quando provider_stream=false; "
            "senão tokens_used conta fragmentos SSE"
        ),
    }
    record.response = {
        "discipline": effective_discipline or built.effective_discipline,
        "sources": list(metadata.get("sources") or built.trace.sources),
        "confidence": confidence_to_float(
            str(metadata.get("confidence") or built.trace.confidence)
        ),
        "answer_chars": len(answer),
    }
    recorder.put(record)
    chat_response = ChatResponse(
        answer=answer,
        discipline=effective_discipline or built.effective_discipline,
        sources=list(metadata.get("sources") or built.trace.sources),
        confidence=confidence_to_float(str(metadata.get("confidence") or built.trace.confidence)),
        metadata=metadata,
    )

    tokens = build_tokens_forensics(
        prompt_chars=int(prompt_forensics.get("prompt_chars") or 0),
        answer=answer,
        metadata=metadata,
    )
    performance = build_performance_map(timings)
    conversation = {
        "message": message[:4000],
        "answer": answer[:8000],
        "user": user_id,
        "channel": channel,
        "session_id": response_session_id,
        "trace_id": tid,
    }

    if tid:
        emit_kernel(
            KERNEL_RESPONSE_GENERATED,
            trace_id=tid,
            data={
                "answer_chars": len(answer),
                "answer_preview": answer[:800],
                "discipline": chat_response.discipline,
                "confidence": chat_response.confidence,
                "sources": list(chat_response.sources)[:12],
                "status": "success",
            },
        )
        store = get_trace_store()
        if store is not None:
            try:
                store.upsert_snapshot(
                    tid,
                    conversation=conversation,
                    rag=rag_forensics,
                    prompt=prompt_forensics,
                    tokens=tokens,
                    performance=performance,
                    system_metrics=sample_system_metrics(db_path=store.db_path),
                )
            except Exception:
                pass

    if chat_response.metadata is not None:
        chat_response.metadata["trace_performance"] = performance
        chat_response.metadata["trace_tokens"] = tokens

    return ChatPipelineOutcome(
        built=built,
        answer=answer,
        metadata=metadata,
        streaming_response=None,
        chat_response=chat_response,
    )
