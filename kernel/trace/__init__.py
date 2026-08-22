"""API pública de emissão TRACE + redacção de `data`."""

from __future__ import annotations

import json
import logging
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from kernel.structured_log import redact_secrets
from kernel.trace.bus import TraceBus
from kernel.trace.stages import PRIORITY_ERROR, PRIORITY_NORMAL, SERVICE_KERNEL
from kernel.trace.store import TraceStore

log = logging.getLogger("kernelbots.trace")

_bus: TraceBus | None = None

_SENSITIVE_KEY = re.compile(
    r"(password|passwd|secret|token|authorization|api[_-]?key|bearer|cookie)",
    re.IGNORECASE,
)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def new_trace_id() -> str:
    return str(uuid.uuid4())


def resolve_trace_id(header_value: str | None) -> str:
    raw = (header_value or "").strip()
    if not raw:
        return new_trace_id()
    # Aceitar UUID ou hex curto; limitar tamanho
    if len(raw) > 128:
        return new_trace_id()
    return raw


def redact_trace_data(data: Any) -> dict[str, Any]:
    """Remove secrets de estruturas antes de persistir."""
    if data is None:
        return {}
    if not isinstance(data, dict):
        return {"value": redact_secrets(str(data))[:2000]}

    def _walk(obj: Any, depth: int = 0) -> Any:
        if depth > 6:
            return "[truncated]"
        if isinstance(obj, dict):
            out: dict[str, Any] = {}
            for k, v in obj.items():
                key = str(k)
                if _SENSITIVE_KEY.search(key):
                    out[key] = "***"
                else:
                    out[key] = _walk(v, depth + 1)
            return out
        if isinstance(obj, (list, tuple)):
            return [_walk(x, depth + 1) for x in obj[:50]]
        if isinstance(obj, str):
            return redact_secrets(obj)[:4000]
        if isinstance(obj, (int, float, bool)) or obj is None:
            return obj
        return redact_secrets(str(obj))[:2000]

    result = _walk(data)
    # Garantir JSON-serializável
    try:
        json.dumps(result, default=str)
    except TypeError:
        return {"value": redact_secrets(str(data))[:2000]}
    return result if isinstance(result, dict) else {"value": result}


def init_trace_bus(db_path: Path, *, retention_days: int | None = None) -> TraceBus:
    global _bus
    store = TraceStore(db_path)
    _bus = TraceBus(store, retention_days=retention_days)
    return _bus


def get_trace_bus() -> TraceBus | None:
    return _bus


def get_trace_store() -> TraceStore | None:
    return _bus.store if _bus is not None else None


async def start_trace_bus(db_path: Path, *, retention_days: int | None = None) -> TraceBus:
    bus = init_trace_bus(db_path, retention_days=retention_days)
    await bus.start()
    return bus


async def stop_trace_bus() -> None:
    global _bus
    if _bus is not None:
        await _bus.stop()
        _bus = None


def reset_trace_bus_for_tests() -> None:
    global _bus
    _bus = None


def emit_kernel(
    stage: str,
    *,
    trace_id: str,
    data: dict[str, Any] | None = None,
) -> bool:
    return emit_event(
        service=SERVICE_KERNEL,
        stage=stage,
        trace_id=trace_id,
        data=data,
    )


def emit_event(
    *,
    service: str,
    stage: str,
    trace_id: str,
    data: dict[str, Any] | None = None,
    timestamp: str | None = None,
) -> bool:
    from kernel.trace.forensics import trace_enabled

    if not trace_enabled():
        return False
    bus = _bus
    if bus is None:
        return False
    safe = redact_trace_data(data)
    prio = PRIORITY_ERROR if (stage or "").upper() == "ERROR" else PRIORITY_NORMAL
    return bus.emit(
        trace_id=trace_id,
        service=service,
        stage=stage,
        data=safe,
        timestamp=timestamp or utc_now_iso(),
        priority=prio,
    )
