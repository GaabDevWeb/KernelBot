"""Montagem do FastAPI: lifespan, templates com path absoluto, routers."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from api.routes import router
from app.state import AppServices

log = logging.getLogger("kernelbots.app")


def create_app(services: AppServices) -> FastAPI:
    templates_dir = Path(__file__).resolve().parent.parent / "templates"
    templates = Jinja2Templates(directory=str(templates_dir))

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        log.info("🚀 ACL iniciado e pronto para receber requisições.")
        yield
        services.observer.stop()
        services.observer.join()
        log.info("🛑 Watchdog encerrado. Servidor finalizado.")

    app = FastAPI(title="ACL — Agente de Contexto Local", lifespan=lifespan)
    app.state.services = services
    app.state.templates = templates

    frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
    assets_dir = frontend_dir / "assets"
    src_dir = frontend_dir / "src"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")
    if src_dir.is_dir():
        app.mount("/src", StaticFiles(directory=str(src_dir)), name="src")

    app.include_router(router)
    return app
