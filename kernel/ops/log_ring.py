"""Ring buffer de logs para o painel Ops (sem Loki)."""

from __future__ import annotations

import logging
import threading
import time
from collections import deque
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class LogEntry:
    ts: float
    level: str
    logger: str
    message: str
    service: str = "kernel"


_LOCK = threading.Lock()
_BUFFER: deque[LogEntry] = deque(maxlen=2000)
_INSTALLED = False


class OpsLogHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record) if self.formatter else record.getMessage()
        except Exception:
            msg = str(record.msg)
        service = "kernel"
        name = record.name or ""
        if "orbit" in name.lower() or "whatsapp" in name.lower():
            service = "whatsapp"
        elif "discord" in name.lower():
            service = "discord"
        entry = LogEntry(
            ts=record.created if hasattr(record, "created") else time.time(),
            level=(record.levelname or "INFO").upper(),
            logger=name,
            message=str(msg)[:2000],
            service=service,
        )
        with _LOCK:
            _BUFFER.append(entry)


def install_ops_log_handler() -> None:
    global _INSTALLED
    if _INSTALLED:
        return
    handler = OpsLogHandler()
    handler.setLevel(logging.INFO)
    handler.setFormatter(logging.Formatter("%(message)s"))
    logging.getLogger().addHandler(handler)
    # também kernelbots.*
    logging.getLogger("kernelbots").addHandler(handler)
    _INSTALLED = True


def query_logs(
    *,
    service: str = "",
    level: str = "",
    text: str = "",
    limit: int = 200,
) -> list[LogEntry]:
    svc = (service or "").strip().lower()
    lvl = (level or "").strip().upper()
    needle = (text or "").strip().lower()
    limit = max(1, min(int(limit), 500))
    with _LOCK:
        items = list(_BUFFER)
    items.reverse()  # mais recentes primeiro
    out: list[LogEntry] = []
    for e in items:
        if svc and e.service != svc:
            continue
        if lvl:
            if lvl == "ERROR" and e.level not in {"ERROR", "CRITICAL"}:
                continue
            elif lvl in {"WARNING", "WARN"} and e.level not in {"WARNING", "WARN"}:
                continue
            elif lvl not in {"ERROR", "WARNING", "WARN"} and e.level != lvl:
                continue
        if needle and needle not in e.message.lower() and needle not in e.logger.lower():
            continue
        out.append(e)
        if len(out) >= limit:
            break
    return out


def log_stats() -> dict[str, Any]:
    with _LOCK:
        items = list(_BUFFER)
    errors = sum(1 for e in items if e.level in {"ERROR", "CRITICAL"})
    warns = sum(1 for e in items if e.level in {"WARNING", "WARN"})
    return {"buffered": len(items), "errors": errors, "warnings": warns}
