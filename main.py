"""Ponto de entrada: logging, serviços e aplicação FastAPI."""

from __future__ import annotations

import logging

import uvicorn
        
from app.factory import create_app
from app.state import AppServices
from core.config import Settings
from core.logging_config import configure_logging
from engine.chat_provider import ChatProvider
from engine.context import ContextManager
from engine.catalog_sync import bootstrap_catalog_state
from engine.pinned_store import PinnedSessionStore
from engine.search import SearchEngine

configure_logging()
log = logging.getLogger("kernelbots.main")


settings = Settings.load()
search_engine = SearchEngine(
    settings.bm25_score_threshold,
    settings.global_context_mode,
    settings=settings,
)

pinned_store = PinnedSessionStore()
lesson_catalog, indexed_lesson_keys, catalog_drift_report = bootstrap_catalog_state(settings)

context_manager = ContextManager(
    settings,
    search_engine,
    pinned_store=pinned_store,
    lesson_catalog=lesson_catalog,
    indexed_lesson_keys=indexed_lesson_keys,
)
chat_provider = ChatProvider(settings)

services = AppServices(
    search_engine=search_engine,
    context_manager=context_manager,
    chat_provider=chat_provider,
    pinned_store=pinned_store,
    lesson_catalog=lesson_catalog,
    indexed_lesson_keys=indexed_lesson_keys,
    catalog_drift_report=catalog_drift_report,
)
app = create_app(services)


if __name__ == "__main__":
    log.info("=" * 60)
    log.info("  ACL — Agente de Contexto Local")
    log.info(f"  Fonte de dados: MySQL ({settings.db_host}:{settings.db_port}/{settings.db_name})")
    log.info(f"  BM25 threshold: {settings.bm25_score_threshold}")
    log.info(f"  Contexto global (sem filtro): {settings.global_context_mode}")
    log.info(f"  Modelos ({len(settings.models)}): {', '.join(settings.models)}")
    log.info("=" * 60)
    uvicorn.run("main:app", host="127.0.0.1", port=8001, reload=False)
