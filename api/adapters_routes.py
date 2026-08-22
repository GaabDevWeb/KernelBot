"""Ops Adapters — /ops/adapters/* (P4)."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from adapters.discord.outbound import outbound_status as discord_status
from adapters.whatsapp.outbound import orbit_outbound_base
from adapters.whatsapp.outbound import outbound_status as whatsapp_status
from api.ops_auth import require_ops_cookie
from api.ops_routes import _ctx
from kernel.structured_log import redact_secrets
from kernel.trace import get_trace_store

router = APIRouter(tags=["adapters-ops"])

_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates" / "ops"
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))

_SECRET_KEY_FRAGMENTS = (
    "token",
    "secret",
    "password",
    "api_key",
    "apikey",
    "authorization",
    "bearer",
    "credential",
)


def _is_secret_key(key: str) -> bool:
    k = (key or "").lower().replace("-", "_")
    return any(frag in k for frag in _SECRET_KEY_FRAGMENTS)


def _sanitize_status(raw: Any, *, depth: int = 0) -> Any:
    """Remove chaves sensíveis e redige strings (nunca tokens/API keys)."""
    if depth > 4:
        return "…"
    if isinstance(raw, dict):
        out: dict[str, Any] = {}
        for k, v in raw.items():
            key = str(k)
            if _is_secret_key(key):
                out[key] = "***"
                continue
            out[key] = _sanitize_status(v, depth=depth + 1)
        return out
    if isinstance(raw, list):
        return [_sanitize_status(x, depth=depth + 1) for x in raw[:40]]
    if isinstance(raw, str):
        return redact_secrets(raw)[:500]
    if isinstance(raw, (bool, int, float)) or raw is None:
        return raw
    return redact_secrets(str(raw))[:200]


def _pick(status: dict[str, Any], *keys: str) -> Any:
    for k in keys:
        if k in status and status[k] is not None:
            return status[k]
    return None


def _trace_msg_counts() -> tuple[int | None, int | None]:
    store = get_trace_store()
    if store is None:
        return None, None
    try:
        m = store.metrics(hours=24)
        return m.messages_today, m.messages_last_hour
    except Exception:
        return None, None


def _status_json(status: dict[str, Any]) -> str:
    return json.dumps(status, ensure_ascii=False, indent=2, default=str)


@router.get("/ops/adapters/whatsapp", response_class=HTMLResponse)
async def adapters_whatsapp(request: Request):
    redirect = require_ops_cookie(request)
    if redirect:
        return redirect

    raw = await whatsapp_status()
    status = _sanitize_status(raw) if isinstance(raw, dict) else {"ok": False, "error": "invalid_status"}
    if not isinstance(status, dict):
        status = {"ok": False, "error": "invalid_status"}

    ready = bool(_pick(status, "ready", "session_ready", "connected"))
    ok = bool(_pick(status, "ok")) if "ok" in status else ready
    reconnections = _pick(
        status,
        "reconnections",
        "reconnect_count",
        "reconnects",
        "reconnectCount",
    )
    session_label = _pick(status, "session", "session_id", "jid", "me")
    if isinstance(session_label, dict):
        session_label = _pick(session_label, "id", "jid", "user") or "presente"
    error = _pick(status, "error", "detail")

    msgs_today, msgs_hour = _trace_msg_counts()
    orbit_base = orbit_outbound_base()
    orbit_display = redact_secrets(orbit_base)

    return templates.TemplateResponse(
        request,
        "adapters/whatsapp.html",
        _ctx(
            "whatsapp",
            status_json=_status_json(status),
            ok=ok,
            ready=ready,
            reconnections=reconnections,
            session_label=session_label,
            error=error,
            msgs_today=msgs_today,
            msgs_hour=msgs_hour,
            orbit_url=orbit_display,
            token_configured=bool((os.getenv("ACL_INTERNAL_BEARER_TOKEN") or "").strip()),
        ),
    )


@router.get("/ops/adapters/discord", response_class=HTMLResponse)
async def adapters_discord(request: Request):
    redirect = require_ops_cookie(request)
    if redirect:
        return redirect

    raw = await discord_status()
    status = _sanitize_status(raw) if isinstance(raw, dict) else {"ok": False}
    if not isinstance(status, dict):
        status = {"ok": False, "error": "invalid_status"}

    return templates.TemplateResponse(
        request,
        "adapters/discord.html",
        _ctx(
            "discord",
            status_json=_status_json(status),
            ready=bool(status.get("ready")),
            ok=bool(status.get("ok")),
            error=status.get("error"),
            active=False,
        ),
    )
