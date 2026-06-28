"""Montagem do FastAPI: lifespan, templates com path absoluto, routers."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from api.routes import router
from app.state import AppServices

log = logging.getLogger("kernelbots.app")


class DevSourceNoCacheMiddleware(BaseHTTPMiddleware):
    """Evita cache agressivo de módulos ES em /src durante desenvolvimento."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        if request.url.path.startswith("/src/") or request.url.path.startswith("/playground/"):
            response.headers["Cache-Control"] = "no-store"
        return response


def create_app(services: AppServices) -> FastAPI:
    templates_dir = Path(__file__).resolve().parent.parent / "templates"
    templates = Jinja2Templates(directory=str(templates_dir))

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        log.info("🚀 ACL iniciado e pronto para receber requisições.")
        yield
        log.info("🛑 Servidor finalizado.")

    app = FastAPI(title="ACL — Agente de Contexto Local", lifespan=lifespan)
    app.add_middleware(DevSourceNoCacheMiddleware)
    app.state.services = services
    app.state.templates = templates

    frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
    playground_dir = Path(__file__).resolve().parent.parent / "playground"
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
    if playground_dir.is_dir():
        app.mount("/playground", StaticFiles(directory=str(playground_dir), html=True), name="playground")

    app.include_router(router)

    return app
