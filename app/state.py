"""Estado injetado na aplicação (sem globais de domínio)."""

from __future__ import annotations

from dataclasses import dataclass, field

from engine.chat_provider import ChatProvider
from engine.context import ContextManager
from engine.lesson_catalog import LessonCatalog
from engine.pinned_store import PinnedSessionStore
from engine.search import SearchEngine


@dataclass
class AppServices:
    search_engine: SearchEngine
    context_manager: ContextManager
    chat_provider: ChatProvider
    pinned_store: PinnedSessionStore
    lesson_catalog: LessonCatalog | None = None
    indexed_lesson_keys: frozenset[str] = field(default_factory=frozenset)
    catalog_drift_report: dict | None = None
