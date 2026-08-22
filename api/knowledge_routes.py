"""UI Conhecimento Ops — /ops/knowledge/* (P1)."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from api.ops_auth import require_ops_cookie
from api.ops_routes import _ctx
from api.routes import _services
from kernel.inspect import sdk as inspect_sdk
from kernel.knowledge.ops import explore_rag, list_documents, reindex_knowledge, run_search
from kernel.trace import emit_kernel, new_trace_id

router = APIRouter(tags=["knowledge-ops"])

_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates" / "ops"
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))


def _safe_services(request: Request):
    try:
        return _services(request)
    except Exception:
        return None


@router.get("/ops/knowledge/docs", response_class=HTMLResponse)
async def knowledge_docs(request: Request):
    redirect = require_ops_cookie(request)
    if redirect:
        return redirect
    qp = request.query_params
    q = (qp.get("q") or "").strip()
    discipline = (qp.get("discipline") or "").strip()
    try:
        limit = int(qp.get("limit") or "500")
    except ValueError:
        limit = 500
    services = _safe_services(request)
    error = None
    listing = {
        "documents": [],
        "total": 0,
        "shown": 0,
        "index_chunks": 0,
        "silos": [],
        "db_meta_count": 0,
    }
    if services is None:
        error = "Serviços do Kernel não inicializados (índice indisponível)."
    else:
        listing = list_documents(services, q=q, discipline=discipline, limit=limit)
    return templates.TemplateResponse(
        request,
        "knowledge/docs.html",
        _ctx(
            "docs",
            listing=listing,
            q=q,
            discipline=discipline,
            limit=limit,
            error=error,
        ),
    )


@router.get("/ops/knowledge/search", response_class=HTMLResponse)
async def knowledge_search(request: Request):
    redirect = require_ops_cookie(request)
    if redirect:
        return redirect
    qp = request.query_params
    q = (qp.get("q") or "").strip()
    mode = (qp.get("mode") or "hybrid").strip().lower()
    if mode not in ("bm25", "hybrid", "full"):
        mode = "hybrid"
    discipline = (qp.get("discipline") or "").strip()
    try:
        top_k = int(qp.get("top_k") or "8")
    except ValueError:
        top_k = 8
    services = _safe_services(request)
    error = None
    result = None
    silos: list[str] = []
    if services is None:
        error = "Serviços do Kernel não inicializados."
    else:
        silos = sorted(services.search_engine.discipline_ids)
        if q:
            try:
                result = run_search(
                    services,
                    query=q,
                    mode=mode,  # type: ignore[arg-type]
                    discipline=discipline or None,
                    top_k=top_k,
                )
            except Exception as exc:
                error = f"Falha na busca: {type(exc).__name__}: {exc}"
    return templates.TemplateResponse(
        request,
        "knowledge/search.html",
        _ctx(
            "search",
            q=q,
            mode=mode,
            discipline=discipline,
            top_k=top_k,
            result=result,
            silos=silos,
            error=error,
        ),
    )


@router.get("/ops/knowledge/rag", response_class=HTMLResponse)
async def knowledge_rag(request: Request):
    redirect = require_ops_cookie(request)
    if redirect:
        return redirect
    qp = request.query_params
    q = (qp.get("q") or "").strip()
    discipline = (qp.get("discipline") or "").strip()
    services = _safe_services(request)
    error = None
    result = None
    rag_cfg = None
    silos: list[str] = []
    if services is None:
        error = "Serviços do Kernel não inicializados."
    else:
        silos = sorted(services.search_engine.discipline_ids)
        rag_cfg = inspect_sdk.rag(services)
        if q:
            try:
                result = explore_rag(
                    services,
                    question=q,
                    discipline=discipline or None,
                )
            except Exception as exc:
                error = f"Falha no RAG Explorer: {type(exc).__name__}: {exc}"
    return templates.TemplateResponse(
        request,
        "knowledge/rag.html",
        _ctx(
            "rag",
            q=q,
            discipline=discipline,
            result=result,
            rag_cfg=rag_cfg,
            silos=silos,
            error=error,
        ),
    )


@router.get("/ops/knowledge/reindex", response_class=HTMLResponse)
async def knowledge_reindex_form(request: Request):
    redirect = require_ops_cookie(request)
    if redirect:
        return redirect
    services = _safe_services(request)
    silos: list[str] = []
    index_chunks = 0
    error = None
    if services is None:
        error = "Serviços do Kernel não inicializados."
    else:
        silos = sorted(services.search_engine.discipline_ids)
        index_chunks = len(services.search_engine.chunks)
    return templates.TemplateResponse(
        request,
        "knowledge/reindex.html",
        _ctx(
            "reindex",
            silos=silos,
            index_chunks=index_chunks,
            result=None,
            error=error,
            flash=request.query_params.get("msg"),
        ),
    )


@router.post("/ops/knowledge/reindex", response_class=HTMLResponse)
async def knowledge_reindex_run(
    request: Request,
    scope: str = Form("all"),
    discipline: str = Form(""),
    document: str = Form(""),
    ingest_disk: str = Form(""),
):
    redirect = require_ops_cookie(request)
    if redirect:
        return redirect
    services = _safe_services(request)
    if services is None:
        return RedirectResponse(url="/ops/knowledge/reindex?msg=no_services", status_code=303)
    scope_norm = (scope or "all").strip().lower()
    if scope_norm not in ("all", "discipline", "document"):
        scope_norm = "all"
    result = reindex_knowledge(
        services,
        scope=scope_norm,  # type: ignore[arg-type]
        discipline=(discipline or "").strip() or None,
        document=(document or "").strip() or None,
        ingest_disk=bool((ingest_disk or "").strip()),
    )
    try:
        emit_kernel(
            "OPS_REINDEX",
            trace_id=new_trace_id(),
            data={
                "scope": scope_norm,
                "discipline": (discipline or "").strip() or None,
                "document": (document or "").strip() or None,
                "ingest_disk": bool((ingest_disk or "").strip()),
                "chunk_total": result.get("chunk_total"),
                "ok": result.get("ok"),
            },
        )
    except Exception:
        pass
    silos = sorted(services.search_engine.discipline_ids)
    return templates.TemplateResponse(
        request,
        "knowledge/reindex.html",
        _ctx(
            "reindex",
            silos=silos,
            index_chunks=result.get("chunk_total") or 0,
            result=result,
            error=None,
            flash=None,
            form_scope=scope_norm,
            form_discipline=(discipline or "").strip(),
            form_document=(document or "").strip(),
            form_ingest=bool((ingest_disk or "").strip()),
        ),
    )
