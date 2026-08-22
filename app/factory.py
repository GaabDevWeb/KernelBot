"""Montagem da API HTTP do Kernel."""

from __future__ import annotations

import logging
import os
import uuid
from collections.abc import Callable
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from api.internal_routes import router as internal_router
from api.routes import router
from api.routes_v1 import router as v1_router
from api.security import is_production, validate_production_security_config
from api.adapters_routes import router as adapters_router
from api.comms_routes import router as comms_router
from api.knowledge_routes import router as knowledge_router
from api.lab_routes import router as lab_router
from api.ops_routes import router as ops_router
from api.settings_routes import router as settings_router
from api.traces_routes import router as traces_router
from api.users_routes import router as users_router
from app.state import AppServices
from kernel.trace import start_trace_bus, stop_trace_bus
from kernel.comms.scheduler import start_comms_scheduler, stop_comms_scheduler
from kernel.comms.store import init_comms_store
from kernel.users.store import init_users_store


log = logging.getLogger("kernelbots.app")

_TRACES_STATIC = Path(__file__).resolve().parent.parent / "templates" / "traces"
_OPS_STATIC = Path(__file__).resolve().parent.parent / "templates" / "ops"


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Headers de segurança aplicáveis a uma API JSON."""

    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        if request.url.scheme == "https" or os.getenv("KERNELBOT_FORCE_HSTS", "").lower() in (
            "1",
            "true",
            "yes",
        ):
            response.headers.setdefault(
                "Strict-Transport-Security",
                "max-age=31536000; includeSubDomains",
            )
        return response


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Gera X-Request-Id no servidor (ignora spoofing do cliente)."""

    async def dispatch(self, request: Request, call_next):
        request_id = uuid.uuid4().hex
        request.state.request_id = request_id
        response: Response = await call_next(request)
        response.headers["X-Request-Id"] = request_id
        return response


def _resolve_trace_db_path(app: FastAPI) -> Path:
    services = getattr(app.state, "services", None)
    if services is not None:
        settings = getattr(services.context_manager, "settings", None)
        path = getattr(settings, "trace_db_path", None)
        if path is not None:
            return Path(path)
    raw = (os.getenv("ACL_TRACE_DB_PATH") or "data/traces.sqlite3").strip()
    p = Path(raw).expanduser()
    if not p.is_absolute():
        # project root = parent of app/
        root = Path(__file__).resolve().parent.parent
        p = root / p
    p = p.resolve()
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def create_app(
    services: AppServices | None = None,
    *,
    services_factory: Callable[[], AppServices] | None = None,
) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Validação fail-fast só no boot real (services_factory), não em testes com stubs.
        if services_factory is not None:
            validate_production_security_config()
        if getattr(app.state, "services", None) is None and services_factory is not None:
            app.state.services = services_factory()
        try:
            days = 30
            services = getattr(app.state, "services", None)
            settings = getattr(getattr(services, "context_manager", None), "settings", None)
            if settings is not None and getattr(settings, "trace_retention_days", None):
                days = int(settings.trace_retention_days)
            else:
                days = int((os.getenv("ACL_TRACE_RETENTION_DAYS") or "30").strip() or "30")
            await start_trace_bus(_resolve_trace_db_path(app), retention_days=days)
            log.info("Trace bus iniciado.")
            try:
                from kernel.ops.log_ring import install_ops_log_handler

                install_ops_log_handler()
            except Exception as exc:
                log.warning("Ops log ring skip: %s", exc)
            # Retenção imediata no boot (além do loop horário)
            try:
                from kernel.trace import get_trace_store

                store = get_trace_store()
                if store is not None:
                    purged = store.purge_older_than(days)
                    if purged:
                        log.info("Trace retention: removidos %s traces (> %s dias)", purged, days)
            except Exception as exc:
                log.warning("Trace retention skip: %s", exc)
        except Exception as exc:
            log.warning("Trace bus não iniciado: %s", exc)
        try:
            raw_comms = (os.getenv("ACL_COMM_DB_PATH") or "data/comms.sqlite3").strip()
            comms_path = Path(raw_comms).expanduser()
            if not comms_path.is_absolute():
                comms_path = Path(__file__).resolve().parent.parent / comms_path
            init_comms_store(comms_path.resolve())
            await start_comms_scheduler()
            log.info("Comms store/scheduler iniciados (%s)", comms_path)
        except Exception as exc:
            log.warning("Comms não iniciado: %s", exc)
        try:
            raw_users = (os.getenv("ACL_USERS_DB_PATH") or "data/users.sqlite3").strip()
            users_path = Path(raw_users).expanduser()
            if not users_path.is_absolute():
                users_path = Path(__file__).resolve().parent.parent / users_path
            init_users_store(users_path.resolve())
            log.info("Users store iniciado (%s)", users_path)
        except Exception as exc:
            log.warning("Users store não iniciado: %s", exc)
        log.info("Kernel iniciado e pronto para receber requisições.")
        yield
        try:
            await stop_comms_scheduler()
        except Exception:
            pass
        try:
            await stop_trace_bus()
        except Exception:
            pass
        log.info("Servidor finalizado.")

    docs_flag = (os.getenv("ACL_ENABLE_DOCS") or "").strip().lower()
    if docs_flag in {"1", "true", "yes", "on"}:
        docs_url: str | None = "/docs"
        redoc_url: str | None = "/redoc"
        openapi_url: str | None = "/openapi.json"
    elif is_production() or docs_flag in {"0", "false", "no", "off"}:
        docs_url = None
        redoc_url = None
        openapi_url = None
    else:
        docs_url = "/docs"
        redoc_url = "/redoc"
        openapi_url = "/openapi.json"

    app = FastAPI(
        title="Kernel API",
        lifespan=lifespan,
        docs_url=docs_url,
        redoc_url=redoc_url,
        openapi_url=openapi_url,
    )
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestIdMiddleware)
    app.state.services = services
    app.include_router(router)
    app.include_router(internal_router)
    app.include_router(v1_router)
    app.include_router(traces_router)
    app.include_router(ops_router)
    app.include_router(knowledge_router)
    app.include_router(comms_router)
    app.include_router(users_router)
    app.include_router(lab_router)
    app.include_router(adapters_router)
    app.include_router(settings_router)
    if _TRACES_STATIC.is_dir():
        app.mount(
            "/traces-static",
            StaticFiles(directory=str(_TRACES_STATIC)),
            name="traces_static",
        )
    if _OPS_STATIC.is_dir():
        app.mount(
            "/ops-static",
            StaticFiles(directory=str(_OPS_STATIC)),
            name="ops_static",
        )
    return app
