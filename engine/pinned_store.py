"""Armazenamento em memória do contexto RAG fixado por sessão (sticky context)."""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field

log = logging.getLogger(f"kernelbots.{__name__}")


@dataclass
class PinnedContext:
    """Chunks e metadados do último RAG forte, reutilizáveis em perguntas de acompanhamento."""

    scope_key: str
    chunks: list[dict[str, str]] = field(default_factory=list)
    display_name: str = ""
    turns_left: int = 0


class PinnedSessionStore:
    """Mapa thread-safe `session_id` → contexto fixado."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._sessions: dict[str, PinnedContext] = {}

    def get(self, session_id: str | None) -> PinnedContext | None:
        if not session_id:
            return None
        with self._lock:
            return self._sessions.get(session_id)

    def set_pinned(
        self,
        session_id: str,
        scope_key: str,
        chunks: list[dict[str, str]],
        display_name: str,
        max_turns: int,
    ) -> None:
        with self._lock:
            self._sessions[session_id] = PinnedContext(
                scope_key=scope_key,
                chunks=chunks,
                display_name=display_name,
                turns_left=max(1, max_turns),
            )
            log.info(
                "   📌 Contexto fixado | session=%s… | scope=%s | chunks=%s | exibe=%r | turnos=%s",
                session_id[:8],
                scope_key,
                len(chunks),
                display_name,
                max_turns,
            )

    def clear(self, session_id: str | None) -> None:
        if not session_id:
            return
        with self._lock:
            if self._sessions.pop(session_id, None):
                log.info("   🧹 Contexto fixado removido | session=%s…", session_id[:8])

    def begin_turn(self, session_id: str | None) -> None:
        """No início de cada mensagem com sessão: consome um turno do pin existente."""
        if not session_id:
            return
        with self._lock:
            p = self._sessions.get(session_id)
            if not p:
                return
            p.turns_left -= 1
            if p.turns_left <= 0:
                self._sessions.pop(session_id, None)
                log.info("   ⏳ Contexto fixado expirou (turnos) | session=%s…", session_id[:8])
