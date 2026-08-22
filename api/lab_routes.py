"""Laboratório Ops P3 — /ops/lab/* (Playground, Replay, Diff, Benchmark)."""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from api.chat_pipeline import run_chat_pipeline
from api.ops_auth import require_ops_cookie
from api.ops_routes import _ctx
from api.routes import _services
from kernel.trace import emit_kernel, get_trace_store, new_trace_id
from kernel.trace.replay import text_diff
from kernel.trace.stages import KERNEL_REQUEST_RECEIVED
from kernel.trace.store import TraceFilters

router = APIRouter(tags=["lab-ops"])

_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates" / "ops"
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))


def _benchmark_models(services) -> list[str]:
    """Modelos A/B/C: env ACL_LAB_BENCHMARK_MODELS ou defaults do settings."""
    raw = (os.getenv("ACL_LAB_BENCHMARK_MODELS") or "").strip()
    if raw:
        models = [m.strip() for m in raw.split(",") if m.strip()]
        if models:
            return models[:5]
    try:
        settings = services.context_manager.settings
    except Exception:
        return []
    if settings.llm_provider == "cursor":
        return [settings.cursor_model]
    return list(settings.models)[:3]


def _available_models(services) -> list[str]:
    try:
        settings = services.context_manager.settings
    except Exception:
        return []
    if settings.llm_provider == "cursor":
        out = [settings.cursor_model]
        for m in settings.models:
            if m not in out:
                out.append(m)
        return out
    return list(settings.models)


def _default_top_k(services) -> int:
    try:
        return int(services.context_manager.settings.retrieval_top_k)
    except Exception:
        return 4


def _format_prompt(messages: list[dict] | None) -> str:
    if not messages:
        return ""
    parts: list[str] = []
    for m in messages:
        role = str(m.get("role") or "?")
        content = str(m.get("content") or "")
        parts.append(f"### {role}\n{content}")
    return "\n\n".join(parts)


def _result_meta(outcome, *, model: str | None = None) -> dict[str, Any]:
    meta = dict(outcome.metadata or {})
    perf = meta.get("trace_performance") or {}
    tokens = meta.get("trace_tokens") or {}
    return {
        "answer": outcome.answer or "",
        "prompt": _format_prompt(getattr(outcome.built, "messages", None)),
        "latency_ms": perf.get("total_ms"),
        "llm_ms": perf.get("llm_ms"),
        "tokens_used": meta.get("tokens_used"),
        "tokens": tokens,
        "model": model,
        "discipline": getattr(outcome.chat_response, "discipline", None)
        if outcome.chat_response
        else None,
        "confidence": getattr(outcome.chat_response, "confidence", None)
        if outcome.chat_response
        else None,
        "sources": list(getattr(outcome.chat_response, "sources", None) or [])
        if outcome.chat_response
        else [],
        "trace_id": meta.get("trace_id"),
    }


def _recent_traces(limit: int = 30):
    store = get_trace_store()
    if store is None:
        return []
    try:
        return store.search_traces(TraceFilters(limit=limit))
    except Exception:
        return []


@router.get("/ops/lab/playground", response_class=HTMLResponse)
async def lab_playground_get(request: Request):
    redirect = require_ops_cookie(request)
    if redirect:
        return redirect
    try:
        services = _services(request)
        models = _available_models(services)
        top_k = _default_top_k(services)
    except Exception:
        models = []
        top_k = 4
    return templates.TemplateResponse(
        request,
        "lab/playground.html",
        _ctx(
            "playground",
            models=models,
            form={
                "message": "",
                "model": models[0] if models else "",
                "temperature": "0.7",
                "top_k": str(top_k),
                "max_tokens": "1024",
            },
            result=None,
            error=None,
        ),
    )


@router.post("/ops/lab/playground", response_class=HTMLResponse)
async def lab_playground_post(
    request: Request,
    message: str = Form(...),
    model: str = Form(""),
    temperature: str = Form("0.7"),
    top_k: str = Form("4"),
    max_tokens: str = Form("1024"),
):
    redirect = require_ops_cookie(request)
    if redirect:
        return redirect

    form = {
        "message": message,
        "model": model,
        "temperature": temperature,
        "top_k": top_k,
        "max_tokens": max_tokens,
    }
    try:
        services = _services(request)
        models = _available_models(services)
    except Exception as exc:
        return templates.TemplateResponse(
            request,
            "lab/playground.html",
            _ctx(
                "playground",
                models=[],
                form=form,
                result=None,
                error=f"Serviços indisponíveis: {type(exc).__name__}: {exc}",
            ),
            status_code=503,
        )

    msg = (message or "").strip()
    if not msg:
        return templates.TemplateResponse(
            request,
            "lab/playground.html",
            _ctx(
                "playground",
                models=models,
                form=form,
                result=None,
                error="Mensagem vazia.",
            ),
        )

    try:
        temp = float(temperature)
    except ValueError:
        temp = 0.7
    try:
        tk = int(top_k)
    except ValueError:
        tk = _default_top_k(services)
    try:
        mt = int(max_tokens)
    except ValueError:
        mt = 1024

    tid = new_trace_id()
    emit_kernel(
        KERNEL_REQUEST_RECEIVED,
        trace_id=tid,
        data={
            "platform": "ops-lab",
            "user_id": "ops",
            "message_preview": msg[:400],
            "pipeline_kind": "lab_playground",
        },
    )

    error = None
    result = None
    try:
        outcome = await run_chat_pipeline(
            request,
            services,
            request_id=getattr(request.state, "request_id", tid),
            message=msg,
            channel="cli",
            user_id="ops",
            discipline=None,
            session_key=f"lab:playground:{tid}",
            conversation_history=[],
            stream=False,
            request_metadata={"lab": "playground"},
            response_session_id=None,
            pipeline_kind="lab_playground",
            trace_id=tid,
            top_k=tk,
            model=(model or "").strip() or None,
            temperature=temp,
            max_tokens=mt,
        )
        result = _result_meta(outcome, model=(model or "").strip() or None)
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"

    return templates.TemplateResponse(
        request,
        "lab/playground.html",
        _ctx(
            "playground",
            models=models,
            form=form,
            result=result,
            error=error,
        ),
    )


@router.get("/ops/lab/replay", response_class=HTMLResponse)
async def lab_replay(request: Request):
    redirect = require_ops_cookie(request)
    if redirect:
        return redirect
    q = (request.query_params.get("trace_id") or "").strip()
    return templates.TemplateResponse(
        request,
        "lab/replay.html",
        _ctx(
            "replay",
            trace_id=q,
            recent=_recent_traces(40),
            flash=request.query_params.get("msg"),
        ),
    )


@router.get("/ops/lab/diff", response_class=HTMLResponse)
async def lab_diff(request: Request):
    redirect = require_ops_cookie(request)
    if redirect:
        return redirect
    a = (request.query_params.get("a") or request.query_params.get("trace_id") or "").strip()
    b = (request.query_params.get("b") or request.query_params.get("vs") or "").strip()
    error = None
    diff = None
    original_answer = ""
    replay_answer = ""
    message = None

    if a and b:
        store = get_trace_store()
        if store is None:
            error = "Trace store não inicializado."
        else:
            from kernel.trace.views import build_conversation_view

            a_snap = store.get_snapshot(a) or {}
            b_snap = store.get_snapshot(b) or {}
            original_answer = str((a_snap.get("conversation") or {}).get("answer") or "")
            replay_answer = str((b_snap.get("conversation") or {}).get("answer") or "")
            if not original_answer:
                original_answer = str(
                    build_conversation_view(store.get_trace(a), store.get_events(a)).get("answer")
                    or ""
                )
            if not replay_answer:
                replay_answer = str(
                    build_conversation_view(store.get_trace(b), store.get_events(b)).get("answer")
                    or ""
                )
            message = (a_snap.get("conversation") or {}).get("message")
            # Também comparar prompts se existirem
            a_prompt = (a_snap.get("prompt") or {})
            b_prompt = (b_snap.get("prompt") or {})
            diff = {
                "answer": text_diff(original_answer, replay_answer),
                "prompt": text_diff(
                    str(a_prompt.get("preview") or a_prompt.get("roles") or ""),
                    str(b_prompt.get("preview") or b_prompt.get("roles") or ""),
                ),
                "a_prompt": a_prompt,
                "b_prompt": b_prompt,
            }
    elif a and not b:
        store = get_trace_store()
        if store is not None:
            snap = store.get_snapshot(a) or {}
            b = str((snap.get("conversation") or {}).get("last_replay_id") or "")
            if b:
                return RedirectResponse(
                    url=f"/ops/lab/diff?a={a}&b={b}", status_code=303
                )
            error = "Indique o segundo trace (vs) ou faça um replay primeiro."

    return templates.TemplateResponse(
        request,
        "lab/diff.html",
        _ctx(
            "diff",
            a=a,
            b=b,
            recent=_recent_traces(40),
            error=error,
            diff=diff,
            original_answer=original_answer,
            replay_answer=replay_answer,
            message=message,
            traces_diff_href=f"/traces/{a}/diff?vs={b}" if a and b else None,
        ),
    )


@router.get("/ops/lab/benchmark", response_class=HTMLResponse)
async def lab_benchmark_get(request: Request):
    redirect = require_ops_cookie(request)
    if redirect:
        return redirect
    try:
        services = _services(request)
        models = _benchmark_models(services)
    except Exception:
        models = []
    return templates.TemplateResponse(
        request,
        "lab/benchmark.html",
        _ctx(
            "benchmark",
            models=models,
            form={"message": "", "temperature": "0.7", "top_k": "4", "max_tokens": "1024"},
            rows=None,
            error=None,
        ),
    )


@router.post("/ops/lab/benchmark", response_class=HTMLResponse)
async def lab_benchmark_post(
    request: Request,
    message: str = Form(...),
    temperature: str = Form("0.7"),
    top_k: str = Form("4"),
    max_tokens: str = Form("1024"),
):
    redirect = require_ops_cookie(request)
    if redirect:
        return redirect

    form = {
        "message": message,
        "temperature": temperature,
        "top_k": top_k,
        "max_tokens": max_tokens,
    }
    try:
        services = _services(request)
        models = _benchmark_models(services)
    except Exception as exc:
        return templates.TemplateResponse(
            request,
            "lab/benchmark.html",
            _ctx(
                "benchmark",
                models=[],
                form=form,
                rows=None,
                error=f"Serviços indisponíveis: {type(exc).__name__}: {exc}",
            ),
            status_code=503,
        )

    msg = (message or "").strip()
    if not msg:
        return templates.TemplateResponse(
            request,
            "lab/benchmark.html",
            _ctx(
                "benchmark",
                models=models,
                form=form,
                rows=None,
                error="Mensagem vazia.",
            ),
        )
    if not models:
        return templates.TemplateResponse(
            request,
            "lab/benchmark.html",
            _ctx(
                "benchmark",
                models=models,
                form=form,
                rows=None,
                error="Nenhum modelo configurado. Defina ACL_LAB_BENCHMARK_MODELS.",
            ),
        )

    try:
        temp = float(temperature)
    except ValueError:
        temp = 0.7
    try:
        tk = int(top_k)
    except ValueError:
        tk = 4
    try:
        mt = int(max_tokens)
    except ValueError:
        mt = 1024

    rows: list[dict[str, Any]] = []
    for model_name in models:
        tid = new_trace_id()
        emit_kernel(
            KERNEL_REQUEST_RECEIVED,
            trace_id=tid,
            data={
                "platform": "ops-lab",
                "user_id": "ops",
                "message_preview": msg[:400],
                "pipeline_kind": "lab_benchmark",
                "model": model_name,
            },
        )
        t0 = time.perf_counter()
        row: dict[str, Any] = {"model": model_name, "ok": False}
        try:
            outcome = await run_chat_pipeline(
                request,
                services,
                request_id=getattr(request.state, "request_id", tid),
                message=msg,
                channel="cli",
                user_id="ops",
                discipline=None,
                session_key=f"lab:bench:{tid}",
                conversation_history=[],
                stream=False,
                request_metadata={"lab": "benchmark", "model": model_name},
                response_session_id=None,
                pipeline_kind="lab_benchmark",
                trace_id=tid,
                top_k=tk,
                model=model_name,
                temperature=temp,
                max_tokens=mt,
            )
            meta = _result_meta(outcome, model=model_name)
            wall_ms = (time.perf_counter() - t0) * 1000.0
            row.update(
                {
                    "ok": True,
                    "answer": meta["answer"],
                    "latency_ms": meta["latency_ms"] or wall_ms,
                    "wall_ms": wall_ms,
                    "tokens_used": meta["tokens_used"],
                    "tokens": meta["tokens"],
                    "trace_id": meta["trace_id"],
                    "error": None,
                }
            )
        except Exception as exc:
            row.update(
                {
                    "ok": False,
                    "answer": "",
                    "latency_ms": (time.perf_counter() - t0) * 1000.0,
                    "wall_ms": (time.perf_counter() - t0) * 1000.0,
                    "tokens_used": None,
                    "tokens": {},
                    "trace_id": tid,
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )
        rows.append(row)

    return templates.TemplateResponse(
        request,
        "lab/benchmark.html",
        _ctx(
            "benchmark",
            models=models,
            form=form,
            rows=rows,
            error=None,
        ),
    )
