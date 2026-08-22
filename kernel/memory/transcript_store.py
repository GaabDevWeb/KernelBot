"""Armazenamento em memória do transcript de conversa por chave v1 (Kernel↔Orbit)."""

from __future__ import annotations

import logging
import threading
from collections import deque

log = logging.getLogger(f"kernelbots.{__name__}")

_Message = dict[str, str]


class TranscriptStore:
    """Mapa thread-safe ``chave v1`` → janela deslizante de pares user/assistant.

    Agnóstica de configuração: ``max_turns`` é sempre recebido do chamador em
    ``append_pair`` (mesma filosofia de ``PinnedSessionStore.set_pinned``),
    nunca lido de ``Settings`` aqui — mantém a store testável isoladamente.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._transcripts: dict[str, deque[_Message]] = {}

    def get(self, key: str | None) -> list[_Message]:
        """Devolve o transcript oldest-first; ``[]`` se ``key`` ausente/``None``."""
        if not key:
            return []
        with self._lock:
            bucket = self._transcripts.get(key)
            return list(bucket) if bucket else []

    def append_pair(
        self,
        key: str | None,
        user_message: str,
        assistant_message: str,
        max_turns: int,
    ) -> None:
        """Acrescenta um par completo; no-op se ``key``/mensagens vazias.

        Mantém só os últimos ``max_turns`` pares (``2 * max_turns`` mensagens),
        descartando do início. Se ``max_turns`` mudar entre chamadas para a
        mesma chave, a janela é reconstruída (mantendo as mensagens mais
        recentes) em vez de ignorar o novo limite.
        """
        if not key or not user_message or not assistant_message:
            return
        window = max(1, max_turns) * 2
        with self._lock:
            bucket = self._transcripts.get(key)
            if bucket is None or bucket.maxlen != window:
                bucket = deque(bucket or (), maxlen=window)
                self._transcripts[key] = bucket
            bucket.append({"role": "user", "content": user_message})
            bucket.append({"role": "assistant", "content": assistant_message})
            log.debug(
                "   💬 Transcript atualizado | key=%s… | pares=%s/%s",
                key[:24],
                len(bucket) // 2,
                max_turns,
            )

    def clear(self, key: str | None) -> None:
        """Remove por completo o transcript da chave; no-op se ``key`` vazia."""
        if not key:
            return
        with self._lock:
            if self._transcripts.pop(key, None) is not None:
                log.info("   🧹 Transcript removido | key=%s…", key[:24])

    def list_keys(self) -> list[str]:
        """Chaves activas em memória (Ops / diagnóstico)."""
        with self._lock:
            return list(self._transcripts.keys())

    def list_summaries(self) -> list[dict[str, int | str]]:
        with self._lock:
            return [
                {
                    "key": key,
                    "messages": len(bucket),
                    "pairs": len(bucket) // 2,
                }
                for key, bucket in self._transcripts.items()
            ]