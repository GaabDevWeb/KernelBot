"""Auth partilhada do painel operacional (/ops e /traces)."""

from __future__ import annotations

import os
import secrets

from fastapi import HTTPException, Request
from fastapi.responses import RedirectResponse

from api.security import allow_internal_operation, is_production, note_auth_failure

COOKIE_NAME = "trace_auth"
COOKIE_MAX_AGE = 60 * 60 * 12
LOGIN_PATH = "/ops/login"


def internal_token() -> str | None:
    dedicated = (os.getenv("ACL_INTERNAL_BEARER_TOKEN") or "").strip()
    if dedicated:
        return dedicated
    if is_production():
        return None
    return (os.getenv("ACL_RELOAD_BEARER_TOKEN") or os.getenv("KERNELBOT_RELOAD_TOKEN") or "").strip() or None


def require_ops_cookie(request: Request) -> RedirectResponse | None:
    try:
        allow_internal_operation(request)
        expected = internal_token()
        if not expected:
            raise HTTPException(status_code=503, detail="ACL_INTERNAL_BEARER_TOKEN not configured")
        cookie = (request.cookies.get(COOKIE_NAME) or "").strip()
        if not cookie or not secrets.compare_digest(cookie, expected):
            note_auth_failure(request, scope="ops")
            return RedirectResponse(url=LOGIN_PATH, status_code=303)
    except HTTPException as exc:
        if exc.status_code == 503:
            raise
        return RedirectResponse(url=LOGIN_PATH, status_code=303)
    return None
