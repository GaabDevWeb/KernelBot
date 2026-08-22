"""Controlos de segurança HTTP partilhados (auth de canal, IP, rate limit)."""

from __future__ import annotations

import logging
import os
import secrets

from fastapi import HTTPException, Request, status

from api.rate_limit import allow_request
from kernel.security_flags import is_production

log = logging.getLogger("kernelbots.api.security")

_CHAT_RATE_LIMIT = 30
_SEARCH_RATE_LIMIT = 20
_AUTH_FAIL_RATE_LIMIT = 10
_RATE_WINDOW_SEC = 60.0
_INTERNAL_RATE_LIMIT = 60


def require_api_auth() -> bool:
    """Em produção exige Bearer de canal; fora, só se ACL_REQUIRE_API_AUTH=true."""
    raw = (os.getenv("ACL_REQUIRE_API_AUTH") or "").strip().lower()
    if raw in {"1", "true", "yes", "on"}:
        return True
    if raw in {"0", "false", "no", "off"}:
        return False
    return is_production()

def _parse_channel_keys() -> dict[str, str]:
    """ACL_CHANNEL_API_KEYS=discord:tok1,telegram:tok2"""
    raw = (os.getenv("ACL_CHANNEL_API_KEYS") or "").strip()
    if not raw:
        return {}
    out: dict[str, str] = {}
    for part in raw.split(","):
        part = part.strip()
        if not part or ":" not in part:
            continue
        channel, token = part.split(":", 1)
        channel = channel.strip().lower()
        token = token.strip()
        if channel and token:
            out[channel] = token
    return out


def configured_api_tokens() -> tuple[str | None, dict[str, str]]:
    global_token = (os.getenv("ACL_API_BEARER_TOKEN") or "").strip() or None
    return global_token, _parse_channel_keys()


def validate_production_security_config() -> None:
    """Fail-fast em production se auth de canal / tokens internos estiverem mal."""
    if not is_production():
        return
    global_token, channel_keys = configured_api_tokens()
    if require_api_auth() and not global_token and not channel_keys:
        raise RuntimeError(
            "KERNELBOT_ENV=production exige ACL_API_BEARER_TOKEN "
            "ou ACL_CHANNEL_API_KEYS (auth de canal para /chat e /search)."
        )
    internal = (os.getenv("ACL_INTERNAL_BEARER_TOKEN") or "").strip()
    if not internal:
        raise RuntimeError(
            "KERNELBOT_ENV=production exige ACL_INTERNAL_BEARER_TOKEN "
            "(não reutilizar ACL_RELOAD_BEARER_TOKEN)."
        )
    reload_tok = (
        os.getenv("ACL_RELOAD_BEARER_TOKEN") or os.getenv("KERNELBOT_RELOAD_TOKEN") or ""
    ).strip()
    if reload_tok and secrets.compare_digest(internal, reload_tok):
        raise RuntimeError(
            "ACL_INTERNAL_BEARER_TOKEN deve ser distinto de ACL_RELOAD_BEARER_TOKEN."
        )


def client_ip(request: Request) -> str:
    """IP do cliente; X-Forwarded-For só se o peer estiver em ACL_TRUSTED_PROXY_IPS."""
    peer = request.client.host if request.client else "unknown"
    trusted_raw = (os.getenv("ACL_TRUSTED_PROXY_IPS") or "").strip()
    if not trusted_raw:
        return peer
    trusted = {p.strip() for p in trusted_raw.split(",") if p.strip()}
    if peer not in trusted:
        return peer
    xff = (request.headers.get("X-Forwarded-For") or "").strip()
    if not xff:
        return peer
    # primeiro hop = cliente original
    first = xff.split(",")[0].strip()
    return first or peer


def _bearer_token(request: Request) -> str | None:
    auth = request.headers.get("Authorization") or ""
    if not auth.startswith("Bearer "):
        return None
    token = auth[7:].strip()
    return token or None


def verify_channel_api_bearer(request: Request, *, channel: str) -> None:
    """Exige Bearer de API de canal quando `require_api_auth()`."""
    if not require_api_auth():
        return
    global_token, channel_keys = configured_api_tokens()
    if not global_token and not channel_keys:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="API auth not configured (ACL_API_BEARER_TOKEN / ACL_CHANNEL_API_KEYS)",
        )
    ip = client_ip(request)
    if not allow_request(
        f"apiauth:{ip}",
        limit=_AUTH_FAIL_RATE_LIMIT,
        window_sec=_RATE_WINDOW_SEC,
    ):
        raise HTTPException(status_code=429, detail="Muitas tentativas de autenticação.")

    token = _bearer_token(request)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization Bearer token required",
        )
    ch = (channel or "unknown").strip().lower()
    accepted = False
    if global_token and secrets.compare_digest(token, global_token):
        accepted = True
    elif ch in channel_keys and secrets.compare_digest(token, channel_keys[ch]):
        accepted = True
    if not accepted:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API bearer token",
        )


def allow_public_operation(
    request: Request,
    operation: str,
    *,
    channel: str | None = None,
    user_id: str | None = None,
) -> None:
    """Rate limit por IP (+ canal/user quando presentes)."""
    ip = client_ip(request)
    limit = _SEARCH_RATE_LIMIT if operation == "search" else _CHAT_RATE_LIMIT
    keys = [f"{operation}:ip:{ip}"]
    ch = (channel or "").strip().lower()
    if ch:
        keys.append(f"{operation}:ch:{ch}:{ip}")
    uid = (user_id or "").strip()
    if uid:
        keys.append(f"{operation}:user:{ch or 'unknown'}:{uid}")
    for key in keys:
        if not allow_request(key, limit=limit, window_sec=_RATE_WINDOW_SEC):
            raise HTTPException(
                status_code=429,
                detail="Muitas requisições. Tente novamente em instantes.",
            )


def allow_internal_operation(request: Request) -> None:
    ip = client_ip(request)
    if not allow_request(
        f"internal:{ip}",
        limit=_INTERNAL_RATE_LIMIT,
        window_sec=_RATE_WINDOW_SEC,
    ):
        raise HTTPException(status_code=429, detail="Muitas requisições internas.")


def note_auth_failure(request: Request, *, scope: str) -> None:
    """Regista falha de auth; 429 se brute-force."""
    ip = client_ip(request)
    if not allow_request(
        f"{scope}authfail:{ip}",
        limit=_AUTH_FAIL_RATE_LIMIT,
        window_sec=_RATE_WINDOW_SEC,
    ):
        raise HTTPException(status_code=429, detail="Muitas tentativas de autenticação.")


def search_snippet_chars() -> int:
    raw = (os.getenv("ACL_SEARCH_SNIPPET_CHARS") or "").strip()
    if raw.isdigit():
        return max(40, min(int(raw), 500))
    return 200
