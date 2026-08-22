"""Rate limiting simples em memória para endpoints públicos."""

from __future__ import annotations

import threading
import time
from collections import defaultdict

_buckets: dict[str, list[float]] = defaultdict(list)
_lock = threading.Lock()
_last_gc = 0.0
_GC_INTERVAL_SEC = 120.0


def allow_request(key: str, *, limit: int = 30, window_sec: float = 60.0) -> bool:
    """Retorna True se o pedido é permitido dentro da janela."""
    now = time.monotonic()
    with _lock:
        global _last_gc
        bucket = _buckets[key]
        bucket[:] = [t for t in bucket if now - t < window_sec]
        if len(bucket) >= limit:
            return False
        bucket.append(now)
        if now - _last_gc >= _GC_INTERVAL_SEC:
            _gc_empty_buckets(now)
            _last_gc = now
        return True


def _gc_empty_buckets(now: float) -> None:
    stale = [k for k, v in _buckets.items() if not v]
    for k in stale:
        _buckets.pop(k, None)
    # também remove buckets com timestamps todos expirados (>10 min)
    expired = [
        k
        for k, v in _buckets.items()
        if v and (now - v[-1]) > 600.0
    ]
    for k in expired:
        _buckets.pop(k, None)


def reset_for_tests() -> None:
    with _lock:
        _buckets.clear()
