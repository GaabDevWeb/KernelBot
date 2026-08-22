"""UI Usuários Ops — /ops/users/* (P2)."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates

from api.ops_auth import require_ops_cookie
from api.ops_routes import _ctx
from api.routes import _services
from kernel.trace import emit_kernel, new_trace_id
from kernel.users.service import (
    build_export_zip,
    conversation_bundle,
    trace_error_stats_for_users,
)
from kernel.users.store import get_users_store

router = APIRouter(tags=["users-ops"])

_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates" / "ops"
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))


@router.get("/ops/users/export.zip")
async def users_export(request: Request):
    redirect = require_ops_cookie(request)
    if redirect:
        return redirect
    store = get_users_store()
    if store is None:
        return RedirectResponse(url="/ops/login", status_code=303)
    data = build_export_zip(store)
    emit_kernel(
        "OPS_USERS_EXPORT",
        trace_id=new_trace_id(),
        data={"bytes": len(data)},
    )
    return Response(
        content=data,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=users-export.zip"},
    )

@router.get("/ops/users/sessions", response_class=HTMLResponse)
async def users_sessions(request: Request):
    redirect = require_ops_cookie(request)
    if redirect:
        return redirect
    store = get_users_store()
    q = (request.query_params.get("q") or "").strip()
    items = store.list_sessions(limit=200, q=q) if store else []
    return templates.TemplateResponse(
        request,
        "users/sessions.html",
        _ctx("sessions", items=items, q=q, flash=request.query_params.get("msg")),
    )


@router.get("/ops/users/conversations", response_class=HTMLResponse)
async def users_conversations(request: Request):
    redirect = require_ops_cookie(request)
    if redirect:
        return redirect
    store = get_users_store()
    items = store.list_sessions(limit=100) if store else []
    live_keys: set[str] = set()
    try:
        services = _services(request)
        live_keys = set(services.transcript_store.list_keys())
    except Exception:
        pass
    return templates.TemplateResponse(
        request,
        "users/conversations.html",
        _ctx("conversations", items=items, live_keys=live_keys),
    )


@router.get("/ops/users/conversations/{session_id}", response_class=HTMLResponse)
async def users_conversation_detail(request: Request, session_id: str):
    redirect = require_ops_cookie(request)
    if redirect:
        return redirect
    store = get_users_store()
    if store is None:
        return RedirectResponse(url="/ops/login", status_code=303)
    session = store.get_session(session_id)
    if session is None:
        return RedirectResponse(url="/ops/users/conversations?msg=not_found", status_code=303)
    transcript_store = None
    pinned_store = None
    try:
        services = _services(request)
        transcript_store = services.transcript_store
        pinned_store = services.pinned_store
    except Exception:
        pass
    bundle = conversation_bundle(
        session, transcript_store=transcript_store, pinned_store=pinned_store
    )
    return templates.TemplateResponse(
        request,
        "users/conversation_detail.html",
        _ctx("conversations", **bundle, flash=request.query_params.get("msg")),
    )


@router.post("/ops/users/conversations/{session_id}/clear-memory")
async def users_clear_memory(request: Request, session_id: str):
    redirect = require_ops_cookie(request)
    if redirect:
        return redirect
    store = get_users_store()
    if store is None:
        return RedirectResponse(url="/ops/login", status_code=303)
    session = store.get_session(session_id)
    if session is None:
        return RedirectResponse(url="/ops/users/conversations", status_code=303)
    try:
        services = _services(request)
        services.transcript_store.clear(session.memory_key)
        services.pinned_store.clear(session.memory_key)
        emit_kernel(
            "OPS_CLEAR_MEMORY",
            trace_id=new_trace_id(),
            data={
                "session_row": session_id,
                "user_id": session.user_id,
                "platform": session.platform,
            },
        )
    except Exception:
        pass
    return RedirectResponse(
        url=f"/ops/users/conversations/{session_id}?msg=memory_cleared",
        status_code=303,
    )


@router.get("/ops/users/stats", response_class=HTMLResponse)
async def users_stats(request: Request):
    redirect = require_ops_cookie(request)
    if redirect:
        return redirect
    store = get_users_store()
    rows = store.user_stats(limit=100) if store else []
    uids = {str(r["user_id"]) for r in rows}
    trace_meta = trace_error_stats_for_users(uids)
    enriched = []
    for r in rows:
        meta = trace_meta.get(str(r["user_id"]), {})
        enriched.append(
            {
                **dict(r),
                "trace_errors": meta.get("errors", 0),
                "trace_count": meta.get("traces", 0),
                "avg_ms": meta.get("avg_ms"),
            }
        )
    return templates.TemplateResponse(
        request, "users/stats.html", _ctx("user-stats", rows=enriched)
    )


@router.get("/ops/users/blocks", response_class=HTMLResponse)
async def users_blocks(request: Request):
    redirect = require_ops_cookie(request)
    if redirect:
        return redirect
    store = get_users_store()
    show_all = (request.query_params.get("all") or "").strip() in {"1", "true"}
    items = store.list_blocks(active_only=not show_all) if store else []
    return templates.TemplateResponse(
        request,
        "users/blocks.html",
        _ctx(
            "blocks",
            items=items,
            show_all=show_all,
            flash=request.query_params.get("msg"),
            error=None,
            form={},
        ),
    )


@router.post("/ops/users/blocks")
async def users_block_create(
    request: Request,
    platform: str = Form("whatsapp"),
    user_id: str = Form(...),
    reason: str = Form(""),
):
    redirect = require_ops_cookie(request)
    if redirect:
        return redirect
    store = get_users_store()
    if store is None:
        return RedirectResponse(url="/ops/login", status_code=303)
    try:
        bid = store.block_user(
            platform=platform.strip(),
            user_id=user_id.strip(),
            reason=reason,
            created_by="ops",
        )
        emit_kernel(
            "OPS_USER_BLOCKED",
            trace_id=new_trace_id(),
            data={
                "block_id": bid,
                "platform": platform,
                "user_id": user_id,
                "reason": reason[:200],
            },
        )
        return RedirectResponse(url="/ops/users/blocks?msg=blocked", status_code=303)
    except ValueError as exc:
        items = store.list_blocks(active_only=True)
        return templates.TemplateResponse(
            request,
            "users/blocks.html",
            _ctx(
                "blocks",
                items=items,
                show_all=False,
                flash=None,
                error=str(exc),
                form={"platform": platform, "user_id": user_id, "reason": reason},
            ),
            status_code=400,
        )


@router.post("/ops/users/blocks/unblock")
async def users_unblock(
    request: Request,
    platform: str = Form(...),
    user_id: str = Form(...),
):
    redirect = require_ops_cookie(request)
    if redirect:
        return redirect
    store = get_users_store()
    if store:
        store.unblock_user(platform=platform.strip(), user_id=user_id.strip())
        emit_kernel(
            "OPS_USER_UNBLOCKED",
            trace_id=new_trace_id(),
            data={"platform": platform, "user_id": user_id},
        )
    return RedirectResponse(
        url=f"/ops/users/blocks?msg=unblocked:{quote(user_id)}",
        status_code=303,
    )


@router.post("/ops/users/sessions/{session_id}/block")
async def users_block_from_session(
    request: Request,
    session_id: str,
    reason: str = Form(""),
):
    redirect = require_ops_cookie(request)
    if redirect:
        return redirect
    store = get_users_store()
    if store is None:
        return RedirectResponse(url="/ops/login", status_code=303)
    session = store.get_session(session_id)
    if session is None:
        return RedirectResponse(url="/ops/users/sessions", status_code=303)
    store.block_user(
        platform=session.platform,
        user_id=session.user_id,
        reason=reason or "Bloqueado a partir da sessão",
    )
    emit_kernel(
        "OPS_USER_BLOCKED",
        trace_id=new_trace_id(),
        data={"platform": session.platform, "user_id": session.user_id, "from": "session"},
    )
    return RedirectResponse(url="/ops/users/blocks?msg=blocked", status_code=303)
