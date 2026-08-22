"""Idempotência de requisições no Kernel (Kernel↔Orbit e APIs públicas).

Evita processamento duplicado quando o adapter reenvia a mesma mensagem
ou em retries de rede. Armazena status em memória thread-safe com TTL
e permite salvar respostas prontas para entrega instantânea.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from typing import Any

log = logging.getLogger("kernelbots.memory.idempotency")

DEFAULT_IDEMPOTENCY_TTL_SECONDS = 300  # 5 minutos


@dataclass
class IdempotencyRecord:
    key: str
    status: str  # "processing" | "completed" | "error"
    created_at: float
    expires_at: float
    response_data: Any = None
    trace_id: str | None = None


class IdempotencyStore:
    """Store thread-safe com expiração por TTL para garantir idempotência."""

    def __init__(self, default_ttl_seconds: int = DEFAULT_IDEMPOTENCY_TTL_SECONDS) -> None:
        self._default_ttl = max(10, default_ttl_seconds)
        self._lock = threading.RLock()
        self._records: dict[str, IdempotencyRecord] = {}

    def _purge_expired(self, now: float) -> None:
        expired = [k for k, r in self._records.items() if r.expires_at <= now]
        for k in expired:
            self._records.pop(k, None)

    def claim(
        self,
        key: str,
        *,
        ttl_seconds: int | None = None,
        trace_id: str | None = None,
    ) -> tuple[bool, IdempotencyRecord | None]:
        """Tenta reservar uma chave.

        Retorna:
            (True, None) -> primeira vez; chamada pode prosseguir.
            (False, record) -> chave já existente (em processamento ou concluída).
        """
        if not key or not key.strip():
            return True, None

        clean_key = key.strip()
        ttl = ttl_seconds if ttl_seconds is not None else self._default_ttl
        now = time.time()

        with self._lock:
            if len(self._records) > 2000:
                self._purge_expired(now)

            existing = self._records.get(clean_key)
            if existing is not None:
                if existing.expires_at > now:
                    log.info("Idempotency HIT: key=%s status=%s", clean_key[:32], existing.status)
                    return False, existing
                # expirado -> remove
                self._records.pop(clean_key, None)

            record = IdempotencyRecord(
                key=clean_key,
                status="processing",
                created_at=now,
                expires_at=now + ttl,
                trace_id=trace_id,
            )
            self._records[clean_key] = record
            log.debug("Idempotency MISS: key=%s reservada", clean_key[:32])
            return True, None

    def complete(
        self,
        key: str,
        response_data: Any,
        *,
        trace_id: str | None = None,
        ttl_seconds: int | None = None,
    ) -> None:
        """Marca a chave como concluída e armazena o resultado."""
        if not key:
            return
        clean_key = key.strip()
        ttl = ttl_seconds if ttl_seconds is not None else self._default_ttl
        now = time.time()

        with self._lock:
            record = self._records.get(clean_key)
            if record is None:
                record = IdempotencyRecord(
                    key=clean_key,
                    status="completed",
                    created_at=now,
                    expires_at=now + ttl,
                    response_data=response_data,
                    trace_id=trace_id,
                )
                self._records[clean_key] = record
            else:
                record.status = "completed"
                record.response_data = response_data
                record.expires_at = now + ttl
                if trace_id:
                    record.trace_id = trace_id

    def fail(self, key: str) -> None:
        """Remove a chave em caso de erro para permitir retry posterior imediato."""
        if not key:
            return
        clean_key = key.strip()
        with self._lock:
            self._records.pop(clean_key, None)

    def get(self, key: str) -> IdempotencyRecord | None:
        if not key:
            return None
        now = time.time()
        with self._lock:
            record = self._records.get(key.strip())
            if record and record.expires_at > now:
                return record
            if record:
                self._records.pop(key.strip(), None)
            return None

    def clear(self) -> None:
        with self._lock:
            self._records.clear()
