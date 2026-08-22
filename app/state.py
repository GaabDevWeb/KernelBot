"""Estado injetado na aplicação (sem globais de domínio)."""

from __future__ import annotations

from dataclasses import dataclass, field

from kernel.providers.chat_provider import ChatProvider
from kernel.orchestrator.context import ContextManager
from kernel.knowledge.lesson_catalog import LessonCatalog
from kernel.memory.group_memory import GroupMemoryStore
from kernel.memory.idempotency import IdempotencyStore
from kernel.memory.pinned_store import PinnedSessionStore
from kernel.memory.transcript_store import TranscriptStore
from kernel.rag.search import SearchEngine


@dataclass
class AppServices:
    search_engine: SearchEngine
    context_manager: ContextManager
    chat_provider: ChatProvider
    pinned_store: PinnedSessionStore
    lesson_catalog: LessonCatalog | None = None
    indexed_lesson_keys: frozenset[str] = field(default_factory=frozenset)
    catalog_drift_report: dict | None = None
    # Transcript store v1 (Kernel↔Orbit): default_factory preserva a
    # construção de `AppServices(...)` sem este campo nos testes legados.
    transcript_store: TranscriptStore = field(default_factory=TranscriptStore)
    # Memória Histórica de Grupos e Idempotência
    group_memory_store: GroupMemoryStore | None = None
    idempotency_store: IdempotencyStore = field(default_factory=IdempotencyStore)
