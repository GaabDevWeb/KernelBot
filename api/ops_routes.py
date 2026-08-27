"""Central de Operações do Kernel — /ops/* (Jinja + HTMX leve)."""

from __future__ import annotations

import os
import secrets
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from api.ops_auth import (
    COOKIE_MAX_AGE,
    COOKIE_NAME,
    internal_token,
    require_ops_cookie,
)
from api.security import allow_internal_operation, note_auth_failure
from kernel.ops.charts import svg_bar_chart, svg_line_chart
from kernel.ops.log_ring import log_stats, query_logs
from kernel.ops.runtime import process_info
from kernel.trace import get_trace_store
from kernel.trace.health import sample_system_metrics
from kernel.trace.store import TraceFilters

router = APIRouter(tags=["ops"])

_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates" / "ops"
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))

# Menu completo (P1 knowledge, P2 users, P3 lab, P4 adapters/settings activos)
NAV_TREE = [
    {"id": "dashboard", "label": "Dashboard", "href": "/ops/dashboard", "group": None},
    {
        "id": "ops",
        "label": "Operações",
        "children": [
            {"id": "traces", "label": "Traces", "href": "/ops/traces"},
            {"id": "groups", "label": "Memória de Grupos", "href": "/ops/groups"},
            {"id": "logs", "label": "Logs", "href": "/ops/logs"},
            {"id": "system", "label": "Sistema", "href": "/ops/system"},
            {"id": "metrics", "label": "Métricas", "href": "/ops/metrics"},
        ],
    },
    {
        "id": "comms",
        "label": "Comunicações",
        "children": [
            {"id": "comm-campaigns", "label": "Campanhas", "href": "/ops/comms/campaigns"},
            {"id": "comm-schedules", "label": "Agendamentos", "href": "/ops/comms/schedules"},
            {"id": "comm-templates", "label": "Templates", "href": "/ops/comms/templates"},
            {"id": "comm-audiences", "label": "Públicos", "href": "/ops/comms/audiences"},
            {"id": "comm-history", "label": "Histórico", "href": "/ops/comms/history"},
        ],
    },
    {
        "id": "knowledge",
        "label": "Conhecimento",
        "children": [
            {"id": "docs", "label": "Documentos", "href": "/ops/knowledge/docs"},
            {"id": "search", "label": "Busca", "href": "/ops/knowledge/search"},
            {"id": "rag", "label": "RAG Explorer", "href": "/ops/knowledge/rag"},
            {"id": "reindex", "label": "Reindexação", "href": "/ops/knowledge/reindex"},
        ],
    },
    {
        "id": "users",
        "label": "Usuários",
        "children": [
            {"id": "sessions", "label": "Sessões", "href": "/ops/users/sessions"},
            {"id": "conversations", "label": "Conversas", "href": "/ops/users/conversations"},
            {"id": "user-stats", "label": "Estatísticas", "href": "/ops/users/stats"},
            {"id": "blocks", "label": "Bloqueios", "href": "/ops/users/blocks"},
        ],
    },
    {
        "id": "lab",
        "label": "Laboratório",
        "children": [
            {"id": "playground", "label": "Playground", "href": "/ops/lab/playground"},
            {"id": "replay", "label": "Replay", "href": "/ops/lab/replay"},
            {"id": "diff", "label": "Diff", "href": "/ops/lab/diff"},
            {"id": "benchmark", "label": "Benchmark", "href": "/ops/lab/benchmark"},
        ],
    },
    {
        "id": "adapters",
        "label": "Adapters",
        "children": [
            {"id": "whatsapp", "label": "WhatsApp", "href": "/ops/adapters/whatsapp"},
            {"id": "discord", "label": "Discord", "href": "/ops/adapters/discord"},
        ],
    },
    {
        "id": "settings",
        "label": "Configurações",
        "children": [
            {"id": "models", "label": "Modelos", "href": "/ops/settings/models"},
            {"id": "prompts", "label": "Prompts", "href": "/ops/settings/prompts"},
            {"id": "providers", "label": "Providers", "href": "/ops/settings/providers"},
            {"id": "syscfg", "label": "Sistema", "href": "/ops/settings/system"},
        ],
    },
]


def _ctx(nav: str, **extra):
    return {"nav": nav, "nav_tree": NAV_TREE, **extra}


@router.get("/ops/login", response_class=HTMLResponse)
async def ops_login_form(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "login.html", {"error": None})


@router.post("/ops/login")
async def ops_login_submit(request: Request, token: str = Form(...)):
    allow_internal_operation(request)
    expected = internal_token()
    if not expected:
        return templates.TemplateResponse(
            request,
            "login.html",
            {"error": "Token interno não configurado (ACL_INTERNAL_BEARER_TOKEN)."},
            status_code=503,
        )
    provided = (token or "").strip()
    if not provided or not secrets.compare_digest(provided, expected):
        note_auth_failure(request, scope="ops")
        return templates.TemplateResponse(
            request,
            "login.html",
            {"error": "Token inválido."},
            status_code=401,
        )
    resp = RedirectResponse(url="/ops/dashboard", status_code=303)
    from api.security import is_production

    resp.set_cookie(
        key=COOKIE_NAME,
        value=provided,
        httponly=True,
        secure=is_production()
        or (os.getenv("KERNELBOT_COOKIE_SECURE") or "").strip().lower() in ("1", "true", "yes"),
        samesite="lax",
        max_age=COOKIE_MAX_AGE,
        path="/",
    )
    return resp


@router.get("/ops", response_class=HTMLResponse)
@router.get("/ops/", response_class=HTMLResponse)
@router.get("/ops/dashboard", response_class=HTMLResponse)
async def ops_dashboard(request: Request):
    redirect = require_ops_cookie(request)
    if redirect:
        return redirect
    store = get_trace_store()
    error = None
    metrics = None
    recent = []
    charts = {"messages": "", "latency": "", "errors": ""}
    system = sample_system_metrics()
    proc = process_info()
    if store is None:
        error = "Trace store não inicializado."
    else:
        metrics = store.metrics(hours=24)
        recent = store.search_traces(TraceFilters(limit=12))
        series = store.hourly_series(hours=24)
        charts = {
            "messages": svg_bar_chart(
                [b.messages for b in series],
                color="#0369a1",
                label="Mensagens por hora (24h)",
            ),
            "latency": svg_line_chart(
                [b.avg_duration_ms for b in series],
                color="#0f766e",
                label="Tempo médio de resposta (ms)",
            ),
            "errors": svg_bar_chart(
                [b.errors for b in series],
                color="#9f1239",
                label="Erros por hora (24h)",
            ),
        }
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        _ctx(
            "dashboard",
            metrics=metrics,
            recent=recent,
            error=error,
            charts=charts,
            system=system,
            proc=proc,
        ),
    )


@router.get("/ops/traces", response_class=HTMLResponse)
async def ops_traces_bridge(request: Request):
    redirect = require_ops_cookie(request)
    if redirect:
        return redirect
    # Reutiliza lista nativa com query string
    qs = request.url.query
    target = "/traces" + (f"?{qs}" if qs else "")
    return RedirectResponse(url=target, status_code=303)


@router.get("/ops/logs", response_class=HTMLResponse)
async def ops_logs(request: Request):
    redirect = require_ops_cookie(request)
    if redirect:
        return redirect
    qp = request.query_params
    service = (qp.get("service") or "").strip()
    level = (qp.get("level") or "").strip()
    text = (qp.get("text") or "").strip()
    try:
        limit = int(qp.get("limit") or "200")
    except ValueError:
        limit = 200
    entries = query_logs(service=service, level=level, text=text, limit=limit)
    rows = []
    for e in entries:
        rows.append(
            {
                "ts_human": datetime.fromtimestamp(e.ts, tz=timezone.utc).strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                "level": e.level,
                "service": e.service,
                "logger": e.logger,
                "message": e.message,
            }
        )
    # enriquecer com erros recentes de traces se ring vazio
    trace_errors = []
    store = get_trace_store()
    if store is not None and not rows:
        trace_errors = store.search_traces(TraceFilters(errors_only=True, limit=50))
    return templates.TemplateResponse(
        request,
        "logs.html",
        _ctx(
            "logs",
            entries=rows,
            stats=log_stats(),
            filters={"service": service, "level": level, "text": text, "limit": limit},
            trace_errors=trace_errors,
        ),
    )


@router.get("/ops/system", response_class=HTMLResponse)
async def ops_system(request: Request):
    redirect = require_ops_cookie(request)
    if redirect:
        return redirect
    store = get_trace_store()
    db_path = None
    queue_depth = None
    try:
        from kernel.trace import get_trace_bus

        bus = get_trace_bus()
        if bus is not None:
            queue_depth = getattr(bus, "queue_size", None)
            if callable(queue_depth):
                queue_depth = queue_depth()
            elif queue_depth is None and hasattr(bus, "_queue"):
                try:
                    queue_depth = bus._queue.qsize()  # noqa: SLF001
                except Exception:
                    queue_depth = None
        if store is not None:
            db_path = getattr(store, "db_path", None)
    except Exception:
        pass
    system = sample_system_metrics(db_path=db_path)
    proc = process_info()
    partial = (request.headers.get("HX-Request") or "").lower() == "true"
    tpl = "system_partial.html" if partial else "system.html"
    return templates.TemplateResponse(
        request,
        tpl,
        _ctx(
            "system",
            system=system,
            proc=proc,
            queue_depth=queue_depth,
            now=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            version=os.getenv("KERNEL_VERSION") or "dev",
        ),
    )


@router.get("/ops/metrics", response_class=HTMLResponse)
async def ops_metrics(request: Request):
    redirect = require_ops_cookie(request)
    if redirect:
        return redirect
    store = get_trace_store()
    error = None
    metrics = None
    charts = {"messages": "", "latency": "", "errors": ""}
    mpm = None
    if store is None:
        error = "Trace store não inicializado."
    else:
        metrics = store.metrics(hours=24)
        series = store.hourly_series(hours=24)
        charts = {
            "messages": svg_bar_chart([b.messages for b in series], label="Msgs/hora"),
            "latency": svg_line_chart(
                [b.avg_duration_ms for b in series], label="Latência média ms"
            ),
            "errors": svg_bar_chart(
                [b.errors for b in series], color="#9f1239", label="Erros/hora"
            ),
        }
        # mensagens por minuto (última hora)
        if metrics.messages_last_hour is not None:
            mpm = round(metrics.messages_last_hour / 60.0, 2)
    err_rate = None
    if metrics and metrics.traces_24h:
        err_rate = round(100.0 * metrics.errors_24h / metrics.traces_24h, 2)
    return templates.TemplateResponse(
        request,
        "metrics.html",
        _ctx(
            "metrics",
            metrics=metrics,
            error=error,
            charts=charts,
            mpm=mpm,
            err_rate=err_rate,
        ),
    )


@router.get("/ops/groups", response_class=HTMLResponse)
async def ops_groups(request: Request, channel_id: str | None = None, query: str | None = None):
    redirect = require_ops_cookie(request)
    if redirect:
        return redirect

    services = getattr(request.app.state, "services", None)
    store = getattr(services, "group_memory_store", None) if services else None

    stats = store.get_stats() if store else {"total_groups": 0, "total_messages": 0, "groups": []}
    selected_group = None
    selected_profile = None
    selected_state = None
    historical_results = []

    if store and channel_id:
        selected_group = channel_id
        selected_profile = store.get_group_profile("whatsapp", channel_id)
        selected_state = store.get_group_state("whatsapp", channel_id)
        if query and query.strip():
            historical_results = store.search_historical("whatsapp", channel_id, query.strip(), top_k=10)
        else:
            historical_results = store.get_recent_messages("whatsapp", channel_id, limit=10)

    return templates.TemplateResponse(
        request,
        "group_memory.html",
        _ctx(
            "groups",
            stats=stats,
            selected_group=selected_group,
            selected_profile=selected_profile,
            selected_state=selected_state,
            historical_results=historical_results,
            query=query or "",
        ),
    )
