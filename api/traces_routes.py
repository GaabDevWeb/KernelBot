"""Painel TRACE operacional — Jinja + cookie auth (fatias A+B)."""

from __future__ import annotations

import os
import secrets
from pathlib import Path
from urllib.parse import urlencode

from fastapi import APIRouter, Form, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates

from api.security import allow_internal_operation, is_production, note_auth_failure
from kernel.trace import get_trace_store
from kernel.trace.export import build_trace_zip
from kernel.trace.store import TraceFilters
from kernel.trace.views import build_conversation_view, build_rag_view

router = APIRouter(tags=["traces"])

_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates" / "traces"
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))

COOKIE_NAME = "trace_auth"
COOKIE_MAX_AGE = 60 * 60 * 12  # 12h


def _internal_token() -> str | None:
    dedicated = (os.getenv("ACL_INTERNAL_BEARER_TOKEN") or "").strip()
    if dedicated:
        return dedicated
    if is_production():
        return None
    return (os.getenv("ACL_RELOAD_BEARER_TOKEN") or os.getenv("KERNELBOT_RELOAD_TOKEN") or "").strip() or None


def _require_cookie(request: Request) -> RedirectResponse | None:
    try:
        allow_internal_operation(request)
        expected = _internal_token()
        if not expected:
            raise HTTPException(
                status_code=503,
                detail="ACL_INTERNAL_BEARER_TOKEN not configured",
            )
        cookie = (request.cookies.get(COOKIE_NAME) or "").strip()
        if not cookie or not secrets.compare_digest(cookie, expected):
            note_auth_failure(request, scope="traces")
            return RedirectResponse(url="/traces/login", status_code=303)
    except HTTPException as exc:
        if exc.status_code == 503:
            raise
        return RedirectResponse(url="/traces/login", status_code=303)
    return None


def _filters_from_request(request: Request) -> TraceFilters:
    qp = request.query_params
    errors = (qp.get("errors") or "").strip().lower() in {"1", "true", "yes", "on"}
    try:
        limit = int(qp.get("limit") or "100")
    except ValueError:
        limit = 100
    return TraceFilters(
        trace_id=(qp.get("q") or qp.get("trace_id") or "").strip(),
        phone=(qp.get("phone") or "").strip(),
        group=(qp.get("group") or "").strip(),
        text=(qp.get("text") or "").strip(),
        since=(qp.get("since") or "").strip(),
        until=(qp.get("until") or "").strip(),
        errors_only=errors,
        limit=limit,
    )


@router.get("/traces/login", response_class=HTMLResponse)
async def traces_login_form(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "login.html", {"error": None})


@router.post("/traces/login")
async def traces_login_submit(request: Request, token: str = Form(...)):
    allow_internal_operation(request)
    expected = _internal_token()
    if not expected:
        return templates.TemplateResponse(
            request,
            "login.html",
            {"error": "Token interno não configurado (ACL_INTERNAL_BEARER_TOKEN)."},
            status_code=503,
        )
    provided = (token or "").strip()
    if not provided or not secrets.compare_digest(provided, expected):
        note_auth_failure(request, scope="traces")
        return templates.TemplateResponse(
            request,
            "login.html",
            {"error": "Token inválido."},
            status_code=401,
        )
    resp = RedirectResponse(url="/ops/dashboard", status_code=303)
    resp.set_cookie(
        key=COOKIE_NAME,
        value=provided,
        httponly=True,
        samesite="lax",
        max_age=COOKIE_MAX_AGE,
        path="/",
    )
    return resp


@router.get("/traces/dashboard", response_class=HTMLResponse)
async def traces_dashboard(request: Request):
    redirect = _require_cookie(request)
    if redirect:
        return redirect
    store = get_trace_store()
    if store is None:
        metrics = None
        recent = []
        error = "Trace store não inicializado."
    else:
        error = None
        metrics = store.metrics(hours=24)
        recent = store.search_traces(TraceFilters(limit=15))
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {"metrics": metrics, "recent": recent, "error": error, "nav": "dashboard"},
    )


@router.get("/traces", response_class=HTMLResponse)
async def traces_list(request: Request):
    redirect = _require_cookie(request)
    if redirect:
        return redirect

    store = get_trace_store()
    filters = _filters_from_request(request)
    if store is None:
        items = []
        error = "Trace store não inicializado."
    else:
        error = None
        items = store.search_traces(filters)

    export_qs = urlencode(
        {
            k: v
            for k, v in {
                "q": filters.trace_id,
                "phone": filters.phone,
                "group": filters.group,
                "text": filters.text,
                "since": filters.since,
                "until": filters.until,
                "errors": "1" if filters.errors_only else "",
            }.items()
            if v
        }
    )
    return templates.TemplateResponse(
        request,
        "list.html",
        {
            "items": items,
            "filters": filters,
            "error": error,
            "nav": "list",
            "export_qs": export_qs,
        },
    )


@router.get("/traces/export.zip")
async def traces_export_bulk(
    request: Request,
    scope: str = Query("filtered"),
    since: str = Query(""),
    until: str = Query(""),
    q: str = Query(""),
    phone: str = Query(""),
    group: str = Query(""),
    text: str = Query(""),
    errors: str = Query(""),
):
    redirect = _require_cookie(request)
    if redirect:
        return redirect
    store = get_trace_store()
    if store is None:
        raise HTTPException(status_code=503, detail="Trace store não inicializado")

    scope_n = (scope or "filtered").strip().lower()
    if scope_n == "all":
        ids = store.list_trace_ids(all_records=True)
        zip_scope = "all"
    elif scope_n == "period":
        ids = store.list_trace_ids(since=since or None, until=until or None, all_records=True)
        zip_scope = "period"
    else:
        filters = TraceFilters(
            trace_id=q.strip(),
            phone=phone.strip(),
            group=group.strip(),
            text=text.strip(),
            since=since.strip(),
            until=until.strip(),
            errors_only=errors.strip().lower() in {"1", "true", "yes", "on"},
            limit=2000,
        )
        ids = [t.trace_id for t in store.search_traces(filters)]
        zip_scope = "filtered"

    if not ids:
        raise HTTPException(status_code=404, detail="Nenhum trace para exportar")

    payload = build_trace_zip(
        store,
        ids,
        scope=zip_scope,
        extra_meta={"since": since, "until": until, "filters": {
            "q": q, "phone": phone, "group": group, "text": text, "errors": errors,
        }},
    )
    filename = f"trace-export-{zip_scope}.zip"
    return Response(
        content=payload,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/traces/{trace_id}/export.zip")
async def traces_export_one(trace_id: str, request: Request):
    redirect = _require_cookie(request)
    if redirect:
        return redirect
    store = get_trace_store()
    if store is None:
        raise HTTPException(status_code=503, detail="Trace store não inicializado")
    events = store.get_events(trace_id)
    if store.get_trace(trace_id) is None and not events:
        raise HTTPException(status_code=404, detail="Trace não encontrado")
    payload = build_trace_zip(store, [trace_id], scope="trace")
    return Response(
        content=payload,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="trace-{trace_id}.zip"'},
    )


@router.post("/traces/{trace_id}/replay")
async def traces_replay(trace_id: str, request: Request):
    redirect = _require_cookie(request)
    if redirect:
        return redirect
    store = get_trace_store()
    if store is None:
        raise HTTPException(status_code=503, detail="Trace store não inicializado")

    summary = store.get_trace(trace_id)
    events = store.get_events(trace_id)
    snapshot = store.get_snapshot(trace_id)
    if summary is None and not events and snapshot is None:
        raise HTTPException(status_code=404, detail="Trace não encontrado")

    from kernel.trace.replay import extract_replay_inputs, text_diff
    from kernel.trace import new_trace_id, emit_kernel
    from kernel.trace.stages import KERNEL_REQUEST_RECEIVED
    from api.chat_pipeline import run_chat_pipeline
    from api.routes import _services

    inputs = extract_replay_inputs(snapshot, events)
    message = (inputs.get("message") or "").strip()
    if not message:
        raise HTTPException(status_code=400, detail="Sem mensagem para replay (snapshot incompleto)")

    services = _services(request)
    replay_tid = new_trace_id()
    user_id = str(inputs.get("user") or "replay")
    channel = str(inputs.get("channel") or "replay")
    history = []
    for t in inputs.get("transcript") or []:
        if isinstance(t, dict) and t.get("role") and t.get("content") is not None:
            history.append({"role": str(t["role"]), "content": str(t["content"])})

    emit_kernel(
        KERNEL_REQUEST_RECEIVED,
        trace_id=replay_tid,
        data={
            "replay_of": trace_id,
            "message_preview": message[:400],
            "platform": channel,
            "user_id": user_id,
        },
    )

    try:
        outcome = await run_chat_pipeline(
            request,
            services,
            request_id=getattr(request.state, "request_id", replay_tid),
            message=message,
            channel="whatsapp" if "whatsapp" in channel or "@" in channel else "cli",
            user_id=user_id,
            discipline=None,
            session_key=f"replay:{trace_id}",
            conversation_history=history,
            stream=False,
            request_metadata={"replay_of": trace_id},
            response_session_id=None,
            pipeline_kind="replay",
            trace_id=replay_tid,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Replay falhou: {type(exc).__name__}: {exc}") from exc

    answer = outcome.answer or ""
    original = str(inputs.get("answer_original") or "")
    if store.get_snapshot(replay_tid) is None:
        store.upsert_snapshot(replay_tid, replay_of=trace_id)
    else:
        store.upsert_snapshot(replay_tid, replay_of=trace_id)
    # marcar original
    store.upsert_snapshot(trace_id, conversation={"last_replay_id": replay_tid})

    diff = text_diff(original, answer)
    return templates.TemplateResponse(
        request,
        "replay.html",
        {
            "nav": "detail",
            "original_id": trace_id,
            "replay_id": replay_tid,
            "original_answer": original,
            "replay_answer": answer,
            "diff": diff,
            "message": message,
        },
    )


@router.get("/traces/{trace_id}/diff", response_class=HTMLResponse)
async def traces_diff(trace_id: str, request: Request, vs: str = Query("")):
    redirect = _require_cookie(request)
    if redirect:
        return redirect
    store = get_trace_store()
    if store is None:
        raise HTTPException(status_code=503, detail="Trace store não inicializado")
    other = (vs or "").strip()
    if not other:
        snap = store.get_snapshot(trace_id) or {}
        other = str((snap.get("conversation") or {}).get("last_replay_id") or "")
    if not other:
        raise HTTPException(status_code=400, detail="Indique ?vs=<trace_id> do replay")

    from kernel.trace.replay import text_diff
    from kernel.trace.views import build_conversation_view

    a_snap = store.get_snapshot(trace_id) or {}
    b_snap = store.get_snapshot(other) or {}
    a_ans = (a_snap.get("conversation") or {}).get("answer") or ""
    b_ans = (b_snap.get("conversation") or {}).get("answer") or ""
    if not a_ans:
        a_ans = build_conversation_view(store.get_trace(trace_id), store.get_events(trace_id)).get("answer") or ""
    if not b_ans:
        b_ans = build_conversation_view(store.get_trace(other), store.get_events(other)).get("answer") or ""
    diff = text_diff(str(a_ans), str(b_ans))
    return templates.TemplateResponse(
        request,
        "replay.html",
        {
            "nav": "detail",
            "original_id": trace_id,
            "replay_id": other,
            "original_answer": a_ans,
            "replay_answer": b_ans,
            "diff": diff,
            "message": (a_snap.get("conversation") or {}).get("message"),
        },
    )


@router.get("/traces/{trace_id}", response_class=HTMLResponse)
async def traces_detail(trace_id: str, request: Request):
    redirect = _require_cookie(request)
    if redirect:
        return redirect

    store = get_trace_store()
    if store is None:
        raise HTTPException(status_code=503, detail="Trace store não inicializado")

    summary = store.get_trace(trace_id)
    events = store.get_events(trace_id, with_deltas=True)
    snapshot = store.get_snapshot(trace_id)
    if summary is None and not events and snapshot is None:
        raise HTTPException(status_code=404, detail="Trace não encontrado")

    rag = (snapshot or {}).get("rag") or build_rag_view(events)
    conversation = (snapshot or {}).get("conversation") or build_conversation_view(summary, events)
    # normalizar shape conversation view
    if "message" not in conversation and snapshot:
        conversation = build_conversation_view(summary, events)

    return templates.TemplateResponse(
        request,
        "detail.html",
        {
            "trace": summary,
            "events": events,
            "trace_id": trace_id,
            "rag": rag,
            "conversation": conversation,
            "prompt": (snapshot or {}).get("prompt"),
            "tokens": (snapshot or {}).get("tokens"),
            "performance": (snapshot or {}).get("performance"),
            "system_metrics": (snapshot or {}).get("system_metrics"),
            "replay_of": (snapshot or {}).get("replay_of"),
            "nav": "detail",
        },
    )
