"""Endpoints internos de observabilidade (/internal/*)."""

from __future__ import annotations

import logging
import os
import secrets

from fastapi import APIRouter, HTTPException, Request, status

from api.security import allow_internal_operation, is_production, note_auth_failure
from kernel.inspect import sdk as inspect_sdk
from kernel.inspect.recorder import get_recorder

log = logging.getLogger("kernelbots.api.internal")

router = APIRouter(prefix="/internal", tags=["internal"])


def _services(request: Request):
    services = getattr(request.app.state, "services", None)
    if services is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Kernel services are not configured",
        )
    return services


def _internal_token(request: Request) -> str | None:
    dedicated = (os.getenv("ACL_INTERNAL_BEARER_TOKEN") or "").strip()
    if dedicated:
        return dedicated
    # Em produção nunca partilhar o token de reload (least privilege).
    if is_production():
        return None
    settings = _services(request).context_manager.settings
    return settings.reload_bearer_token


def _verify_internal_bearer(request: Request) -> None:
    allow_internal_operation(request)
    expected = _internal_token(request)
    if not expected:
        raise HTTPException(
            status_code=503,
            detail="internal token not configured (ACL_INTERNAL_BEARER_TOKEN)",
        )
    auth = request.headers.get("Authorization") or ""
    if not auth.startswith("Bearer "):
        note_auth_failure(request, scope="internal")
        raise HTTPException(status_code=401, detail="Authorization Bearer token required")
    token = auth[7:].strip()
    if not token or not secrets.compare_digest(token, expected):
        note_auth_failure(request, scope="internal")
        raise HTTPException(status_code=401, detail="Invalid internal bearer token")


@router.get("/system")
async def internal_system(request: Request) -> dict:
    _verify_internal_bearer(request)
    return inspect_sdk.system(_services(request))


@router.get("/disciplines")
async def internal_disciplines(request: Request) -> dict:
    _verify_internal_bearer(request)
    return inspect_sdk.disciplines(_services(request))


@router.get("/rag")
async def internal_rag(request: Request) -> dict:
    _verify_internal_bearer(request)
    return inspect_sdk.rag(_services(request))


@router.get("/rag/query/{request_id}")
async def internal_rag_query(request_id: str, request: Request) -> dict:
    _verify_internal_bearer(request)
    payload = inspect_sdk.rag_query(request_id)
    if payload is None:
        raise HTTPException(status_code=404, detail="request_id not found in recorder buffer")
    return payload


@router.get("/context/{request_id}")
async def internal_context(request_id: str, request: Request) -> dict:
    _verify_internal_bearer(request)
    payload = inspect_sdk.context(request_id)
    if payload is None:
        raise HTTPException(status_code=404, detail="request_id not found in recorder buffer")
    return payload


@router.get("/prompt/{request_id}")
async def internal_prompt(request_id: str, request: Request) -> dict:
    _verify_internal_bearer(request)
    payload = inspect_sdk.prompt(request_id)
    if payload is None:
        raise HTTPException(status_code=404, detail="prompt not stored or request_id unknown")
    return payload


@router.get("/pipeline/{request_id}")
async def internal_pipeline(request_id: str, request: Request) -> dict:
    _verify_internal_bearer(request)
    payload = inspect_sdk.pipeline(request_id)
    if payload is None:
        raise HTTPException(status_code=404, detail="request_id not found in recorder buffer")
    return payload


@router.get("/models")
async def internal_models(request: Request) -> dict:
    _verify_internal_bearer(request)
    return inspect_sdk.models(_services(request))


@router.get("/metrics")
async def internal_metrics(request: Request) -> dict:
    _verify_internal_bearer(request)
    return inspect_sdk.metrics(_services(request))


@router.get("/health/deep")
async def internal_health_deep(request: Request) -> dict:
    _verify_internal_bearer(request)
    return inspect_sdk.health_deep(_services(request))


@router.get("/memory/session/{session_id}")
async def internal_memory_session(session_id: str, request: Request) -> dict:
    _verify_internal_bearer(request)
    return inspect_sdk.memory_session(_services(request), session_id)


@router.get("/requests/recent")
async def internal_requests_recent(request: Request) -> dict:
    _verify_internal_bearer(request)
    limit_raw = request.query_params.get("limit", "20")
    try:
        limit = max(1, min(int(limit_raw), 100))
    except ValueError:
        limit = 20
    rows = get_recorder().recent(limit)
    return {
        "items": [
            {
                "request_id": r.request_id,
                "kind": r.kind,
                "channel": r.channel,
                "created_at": r.created_at,
                "error": r.error,
            }
            for r in rows
        ]
    }


@router.post("/traces/events", status_code=202)
async def ingest_trace_events(request: Request) -> dict:
    """Ingestão de eventos TRACE (Orbit → Kernel). Best-effort via queue."""
    _verify_internal_bearer(request)
    from kernel.trace import emit_event, redact_trace_data

    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="JSON body required") from None

    if isinstance(body, dict) and "events" in body:
        raw_events = body.get("events")
        if not isinstance(raw_events, list):
            raise HTTPException(status_code=400, detail="events must be a list")
        events = raw_events
    elif isinstance(body, list):
        events = body
    elif isinstance(body, dict):
        events = [body]
    else:
        raise HTTPException(status_code=400, detail="invalid body")

    queued = 0
    for ev in events[:200]:
        if not isinstance(ev, dict):
            continue
        tid = str(ev.get("trace_id") or "").strip()
        stage = str(ev.get("stage") or "").strip()
        service = str(ev.get("service") or "orbit").strip()
        if not tid or not stage:
            continue
        data = ev.get("data") if isinstance(ev.get("data"), dict) else {}
        ts = ev.get("timestamp")
        timestamp = str(ts).strip() if ts else None
        if emit_event(
            service=service,
            stage=stage,
            trace_id=tid,
            data=redact_trace_data(data),
            timestamp=timestamp,
        ):
            queued += 1

    return {"queued": queued}
