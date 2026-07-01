"""Montagem do FastAPI: lifespan, templates com path absoluto, routers."""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from api.routes import router
from app.state import AppServices

log = logging.getLogger("kernelbots.app")


def _is_production() -> bool:
    return os.getenv("KERNELBOT_ENV", "").strip().lower() == "production"


class DevSourceNoCacheMiddleware(BaseHTTPMiddleware):
    """Evita cache agressivo de módulos ES em /src durante desenvolvimento."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        if request.url.path.startswith("/src/"):
            response.headers["Cache-Control"] = "no-store"
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Headers de segurança para respostas HTML e API."""

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
        path = request.url.path
        if path == "/" or path.startswith("/assets/") or path.startswith("/src/"):
            csp = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com; "
                "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
                "font-src 'self' https://fonts.gstatic.com data:; "
                "img-src 'self' data: blob:; "
                "connect-src 'self'; "
                "frame-ancestors 'none'; "
                "base-uri 'self'; "
                "form-action 'self'"
            )
            response.headers.setdefault("Content-Security-Policy", csp)
        return response


def create_app(services: AppServices) -> FastAPI:
    templates_dir = Path(__file__).resolve().parent.parent / "templates"
    templates = Jinja2Templates(directory=str(templates_dir))

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        log.info("🚀 Kernel iniciado e pronto para receber requisições.")
        yield
        log.info("🛑 Servidor finalizado.")

    app = FastAPI(title="Kernel — Assistente de Estudo", lifespan=lifespan)
    app.add_middleware(SecurityHeadersMiddleware)
    if not _is_production():
        app.add_middleware(DevSourceNoCacheMiddleware)
    app.state.services = services
    app.state.templates = templates

    frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
    core_json = Path(__file__).resolve().parent.parent / "core" / "disciplines.json"
    assets_dir = frontend_dir / "assets"
    src_dir = frontend_dir / "src"

    @app.get("/src/config/disciplines.json")
    def disciplines_config() -> FileResponse:
        return FileResponse(core_json, media_type="application/json")

    @app.get("/favicon.ico")
    def favicon() -> FileResponse:
        icon = assets_dir / "images" / "icon.png"
        return FileResponse(icon, media_type="image/png")

    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")
    if src_dir.is_dir():
        app.mount("/src", StaticFiles(directory=str(src_dir)), name="src")

    app.include_router(router)

    return app
