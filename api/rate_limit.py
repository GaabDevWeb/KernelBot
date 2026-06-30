"""Rate limiting simples em memória para endpoints públicos."""

from __future__ import annotations

import time
from collections import defaultdict

_buckets: dict[str, list[float]] = defaultdict(list)


def allow_request(key: str, *, limit: int = 30, window_sec: float = 60.0) -> bool:
    """Retorna True se o pedido é permitido dentro da janela."""
    now = time.monotonic()
    bucket = _buckets[key]
    bucket[:] = [t for t in bucket if now - t < window_sec]
    if len(bucket) >= limit:
        return False
    bucket.append(now)
    return True
