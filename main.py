"""Ponto de entrada: logging, serviços e aplicação FastAPI."""

from __future__ import annotations

import logging

import uvicorn

from app.factory import create_app
from app.state import AppServices
from kernel.config import Settings
from kernel.context.builder import ContextBuilder
from kernel.context.calendar_provider import CalendarProvider
from kernel.context.institutional import InstitutionalContextProvider
from kernel.context.temporal import TemporalContextProvider
from kernel.logging_config import configure_logging
from kernel.memory.group_memory import GroupMemoryStore
from kernel.memory.idempotency import IdempotencyStore
from kernel.memory.pinned_store import PinnedSessionStore
from kernel.memory.transcript_store import TranscriptStore
from kernel.orchestrator.context import ContextManager
from kernel.providers.chat_provider import ChatProvider
from kernel.rag.search import SearchEngine

configure_logging()
log = logging.getLogger("kernelbots.main")


def build_services() -> AppServices:
    """Constrói dependências de infraestrutura do Kernel."""
    settings = Settings.load()
    search_engine = SearchEngine(
        settings.bm25_score_threshold,
        settings.global_context_mode,
        settings=settings,
    )
    pinned_store = PinnedSessionStore()
    transcript_store = TranscriptStore()
    group_mem_path = settings.group_memory_db_path or (settings.project_root / "data" / "group_memory.sqlite3")
    group_memory_store = GroupMemoryStore(group_mem_path) if settings.group_memory_enabled else None
    idempotency_store = IdempotencyStore(settings.idempotency_ttl_seconds)
    lesson_catalog, indexed_lesson_keys, catalog_drift_report = bootstrap_catalog_state(settings)
    context_builder = ContextBuilder(
        identity_prompt=settings.identity_prompt,
        institutional=InstitutionalContextProvider(settings.context_dir),
        temporal=TemporalContextProvider(settings.kernel_timezone),
        calendar=CalendarProvider(settings.calendar_path),
    )
    context_manager = ContextManager(
        settings,
        search_engine,
        pinned_store=pinned_store,
        lesson_catalog=lesson_catalog,
        indexed_lesson_keys=indexed_lesson_keys,
        context_builder=context_builder,
        group_memory_store=group_memory_store,
    )
    return AppServices(
        search_engine=search_engine,
        context_manager=context_manager,
        chat_provider=ChatProvider(settings),
        pinned_store=pinned_store,
        lesson_catalog=lesson_catalog,
        indexed_lesson_keys=indexed_lesson_keys,
        catalog_drift_report=catalog_drift_report,
        transcript_store=transcript_store,
        group_memory_store=group_memory_store,
        idempotency_store=idempotency_store,
    )


# Uvicorn (`main:app`) e `python main.py` usam o mesmo composition root.
# Serviços sobem no lifespan — importação do módulo não exige MySQL/.env.
app = create_app(services_factory=build_services)


if __name__ == "__main__":
    log.info("=" * 60)
    log.info("  Kernel API")
    log.info("=" * 60)
    uvicorn.run("main:app", host="127.0.0.1", port=8001, reload=False)
