"""Estado injetado na aplicação (sem globais de domínio)."""

from __future__ import annotations

from dataclasses import dataclass

from watchdog.observers import Observer

from engine.chat_provider import ChatProvider
from engine.context import ContextManager
from engine.pinned_store import PinnedSessionStore
from engine.search import SearchEngine


@dataclass
class AppServices:
    search_engine: SearchEngine
    context_manager: ContextManager
    chat_provider: ChatProvider
    observer: Observer
    pinned_store: PinnedSessionStore
