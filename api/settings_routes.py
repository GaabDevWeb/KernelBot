"""Ops Configurações — /ops/settings/* (P4)."""

from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from api.ops_auth import require_ops_cookie
from api.ops_routes import _ctx
from kernel.structured_log import redact_secrets

router = APIRouter(tags=["settings-ops"])

_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates" / "ops"
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_PROMPTS_DIR = _PROJECT_ROOT / "kernel" / "policies" / "systemPrompt"

# Temperature / timeout / max_tokens: hardcoded no provider/config (sem env seguro de escrita).
_OPENROUTER_TEMPERATURE = 0.7
_HTTP_TIMEOUT_S = 60.0
_MAX_TOKENS_NOTE = "não definido no Kernel (default do provider)"


def _services(request: Request):
    return getattr(request.app.state, "services", None)


def _settings_or_none(request: Request):
    services = _services(request)
    if services is None:
        return None
    cm = getattr(services, "context_manager", None)
    return getattr(cm, "settings", None) if cm is not None else None


def _env_bool(name: str, default: bool | None = None) -> bool | None:
    raw = (os.getenv(name) or "").strip().lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "on"}


def _flag_present(name: str) -> str:
    """Estado de secret: configured / missing — nunca o valor."""
    val = (os.getenv(name) or "").strip()
    return "configured" if val else "missing"


def _models_view(request: Request) -> dict[str, Any]:
    s = _settings_or_none(request)
    provider = (getattr(s, "llm_provider", None) or os.getenv("ACL_LLM_PROVIDER") or "cursor").strip()
    cursor_model = (getattr(s, "cursor_model", None) or os.getenv("ACL_CURSOR_MODEL") or "composer-2.5").strip()
    openrouter_models = list(getattr(s, "models", ()) or ())
    if not openrouter_models:
        openrouter_models = [
            "openrouter/free",
            "deepseek/deepseek-v4-flash",
            "meta-llama/llama-4-maverick",
        ]
    timeout = float(getattr(s, "http_timeout", _HTTP_TIMEOUT_S) or _HTTP_TIMEOUT_S)
    active = cursor_model if provider == "cursor" else (openrouter_models[0] if openrouter_models else "—")
    return {
        "llm_provider": provider,
        "active_model": active,
        "cursor_model": cursor_model,
        "openrouter_models": openrouter_models,
        "temperature": _OPENROUTER_TEMPERATURE,
        "max_tokens": _MAX_TOKENS_NOTE,
        "http_timeout_s": timeout,
        "cursor_chat_only": bool(
            getattr(s, "cursor_chat_only", None)
            if s is not None
            else (_env_bool("ACL_CURSOR_CHAT_ONLY", True) is True)
        ),
        "editable": False,
        "edit_note": (
            "Somente leitura: temperatura (0.7), timeout HTTP (60s) e lista OpenRouter "
            "estão hardcoded em kernel/config.py / chat_provider. Não há formulário "
            "env-backed seguro para editar estes parâmetros em runtime. Altere "
            "ACL_LLM_PROVIDER / ACL_CURSOR_MODEL no .env e reinicie o processo."
        ),
    }


def _list_prompt_files() -> list[dict[str, Any]]:
    if not _PROMPTS_DIR.is_dir():
        return []
    rows: list[dict[str, Any]] = []
    for path in sorted(_PROMPTS_DIR.glob("*.txt")):
        try:
            st = path.stat()
            mtime = datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).strftime(
                "%Y-%m-%d %H:%M:%SZ"
            )
            rows.append(
                {
                    "name": path.name,
                    "rel_path": f"kernel/policies/systemPrompt/{path.name}",
                    "size": st.st_size,
                    "mtime": mtime,
                    "mtime_epoch": int(st.st_mtime),
                }
            )
        except OSError:
            continue
    return rows


def _safe_prompt_path(name: str | None) -> Path | None:
    if not name:
        return None
    base = name.strip()
    if not base or "/" in base or "\\" in base or ".." in base:
        return None
    if not base.endswith(".txt"):
        return None
    path = (_PROMPTS_DIR / base).resolve()
    try:
        path.relative_to(_PROMPTS_DIR.resolve())
    except ValueError:
        return None
    if not path.is_file():
        return None
    return path


async def _probe_provider(name: str, *, api_key_configured: bool) -> dict[str, Any]:
    """Health check best-effort (sem expor chaves)."""
    started = time.perf_counter()
    if not api_key_configured:
        return {
            "name": name,
            "status": "unconfigured",
            "latency_ms": None,
            "last_error": "API key missing in env",
            "detail": None,
        }
    if name == "cursor":
        # Cursor SDK é local — não há HTTP público fiável; só confirma configuração.
        elapsed = round((time.perf_counter() - started) * 1000, 1)
        return {
            "name": name,
            "status": "configured",
            "latency_ms": elapsed,
            "last_error": None,
            "detail": "chave presente; probe HTTP não aplicável (Cursor SDK local)",
        }
    if name == "openrouter":
        url = "https://openrouter.ai/api/v1/models"
        # Probe sem Authorization: valida reachability; auth real não é testada aqui
        # para evitar logar/expor a chave no painel.
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.get(url)
            elapsed = round((time.perf_counter() - started) * 1000, 1)
            if r.status_code < 500:
                return {
                    "name": name,
                    "status": "reachable",
                    "latency_ms": elapsed,
                    "last_error": None,
                    "detail": f"HTTP {r.status_code} em /api/v1/models",
                }
            return {
                "name": name,
                "status": "error",
                "latency_ms": elapsed,
                "last_error": f"http_{r.status_code}",
                "detail": None,
            }
        except Exception as exc:
            elapsed = round((time.perf_counter() - started) * 1000, 1)
            return {
                "name": name,
                "status": "error",
                "latency_ms": elapsed,
                "last_error": redact_secrets(str(exc))[:200],
                "detail": None,
            }
    return {
        "name": name,
        "status": "unknown",
        "latency_ms": None,
        "last_error": "provider_not_supported",
        "detail": None,
    }


def _system_flags_view(request: Request) -> dict[str, Any]:
    s = _settings_or_none(request)
    version = (os.getenv("KERNEL_VERSION") or "dev").strip() or "dev"
    env = (os.getenv("KERNELBOT_ENV") or "development").strip() or "development"
    retention = getattr(s, "trace_retention_days", None)
    if retention is None:
        try:
            retention = int((os.getenv("ACL_TRACE_RETENTION_DAYS") or "30").strip() or "30")
        except ValueError:
            retention = 30
    trace_db = getattr(s, "trace_db_path", None)
    if trace_db is not None:
        trace_db_display = str(trace_db)
    else:
        trace_db_display = (os.getenv("ACL_TRACE_DB_PATH") or "data/traces.sqlite3").strip()

    secrets = {
        "OPENROUTER_API_KEY": _flag_present("OPENROUTER_API_KEY"),
        "CURSOR_API_KEY": _flag_present("CURSOR_API_KEY"),
        "ACL_INTERNAL_BEARER_TOKEN": _flag_present("ACL_INTERNAL_BEARER_TOKEN"),
        "ACL_API_BEARER_TOKEN": _flag_present("ACL_API_BEARER_TOKEN"),
        "ACL_RELOAD_BEARER_TOKEN": _flag_present("ACL_RELOAD_BEARER_TOKEN"),
        "DB_PASSWORD": _flag_present("DB_PASSWORD"),
    }
    flags = {
        "ACL_TRACE_ENABLED": _env_bool("ACL_TRACE_ENABLED", True),
        "ACL_TRACE_STORE_PROMPTS": _env_bool("ACL_TRACE_STORE_PROMPTS", True),
        "ACL_INTERNAL_STORE_PROMPTS": _env_bool("ACL_INTERNAL_STORE_PROMPTS", False),
        "ACL_ENABLE_DOCS": _env_bool("ACL_ENABLE_DOCS", None),
        "ACL_DISAMBIGUATION_ENABLED": _env_bool("ACL_DISAMBIGUATION_ENABLED", False),
        "ACL_CATALOG_ENABLED": _env_bool("ACL_CATALOG_ENABLED", False),
        "ACL_CURSOR_CHAT_ONLY": _env_bool("ACL_CURSOR_CHAT_ONLY", True),
        "ACL_GROUNDING_POLICY": (os.getenv("ACL_GROUNDING_POLICY") or "anchored").strip(),
        "ACL_LLM_PROVIDER": (os.getenv("ACL_LLM_PROVIDER") or "cursor").strip(),
        "ACL_GLOBAL_CONTEXT": (os.getenv("ACL_GLOBAL_CONTEXT") or "geral").strip(),
    }
    return {
        "version": version,
        "env": env,
        "trace_retention_days": retention,
        "trace_db_path": redact_secrets(trace_db_display),
        "secrets": secrets,
        "flags": flags,
        "orbit_internal_url": redact_secrets(
            (os.getenv("ORBIT_INTERNAL_URL") or "http://127.0.0.1:8010").strip()
        ),
    }


@router.get("/ops/settings/models", response_class=HTMLResponse)
async def settings_models(request: Request):
    redirect = require_ops_cookie(request)
    if redirect:
        return redirect
    return templates.TemplateResponse(
        request,
        "settings/models.html",
        _ctx("models", model=_models_view(request)),
    )


@router.get("/ops/settings/prompts", response_class=HTMLResponse)
async def settings_prompts(request: Request):
    redirect = require_ops_cookie(request)
    if redirect:
        return redirect
    files = _list_prompt_files()
    selected_name = (request.query_params.get("file") or "").strip()
    if not selected_name and files:
        selected_name = files[0]["name"]
    content = None
    selected_meta = None
    err = None
    path = _safe_prompt_path(selected_name)
    if selected_name and path is None:
        err = "Ficheiro inválido ou fora de kernel/policies/systemPrompt/."
    elif path is not None:
        try:
            content = path.read_text(encoding="utf-8")
            st = path.stat()
            selected_meta = {
                "name": path.name,
                "rel_path": f"kernel/policies/systemPrompt/{path.name}",
                "mtime": datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).strftime(
                    "%Y-%m-%d %H:%M:%SZ"
                ),
                "size": st.st_size,
            }
        except OSError as exc:
            err = redact_secrets(str(exc))[:200]
    return templates.TemplateResponse(
        request,
        "settings/prompts.html",
        _ctx(
            "prompts",
            files=files,
            selected=selected_name,
            selected_meta=selected_meta,
            content=content,
            error=err,
            prompts_dir="kernel/policies/systemPrompt/",
            write_note=(
                "Somente leitura no painel. Alterar prompts em produção exige "
                "edição no repositório + deploy/reinício — sem write arbitrário "
                "via Ops (risco de bypass sem confirmação/auditoria)."
            ),
        ),
    )


@router.get("/ops/settings/providers", response_class=HTMLResponse)
async def settings_providers(request: Request):
    redirect = require_ops_cookie(request)
    if redirect:
        return redirect
    s = _settings_or_none(request)
    active = (getattr(s, "llm_provider", None) or os.getenv("ACL_LLM_PROVIDER") or "cursor").strip()
    cursor_key = bool(
        (getattr(s, "cursor_api_key", None) if s is not None else None)
        or (os.getenv("CURSOR_API_KEY") or "").strip()
    )
    or_key = bool(
        (getattr(s, "openrouter_api_key", None) if s is not None else None)
        or (os.getenv("OPENROUTER_API_KEY") or "").strip()
    )
    probes = [
        await _probe_provider("cursor", api_key_configured=cursor_key),
        await _probe_provider("openrouter", api_key_configured=or_key),
    ]
    for p in probes:
        p["active"] = p["name"] == active
    return templates.TemplateResponse(
        request,
        "settings/providers.html",
        _ctx("providers", providers=probes, active_provider=active),
    )


@router.get("/ops/settings/system", response_class=HTMLResponse)
async def settings_system(request: Request):
    redirect = require_ops_cookie(request)
    if redirect:
        return redirect
    return templates.TemplateResponse(
        request,
        "settings/system.html",
        _ctx("syscfg", cfg=_system_flags_view(request)),
    )
