"""Uptime e metadados do processo para o painel Sistema."""

from __future__ import annotations

import os
import threading
import time
from typing import Any

_BOOT_MONO = time.monotonic()
_BOOT_WALL = time.time()
_LOCK = threading.Lock()


def uptime_seconds() -> float:
    return max(0.0, time.monotonic() - _BOOT_MONO)


def format_uptime(seconds: float | None = None) -> str:
    s = int(seconds if seconds is not None else uptime_seconds())
    days, rem = divmod(s, 86400)
    hours, rem = divmod(rem, 3600)
    mins, secs = divmod(rem, 60)
    if days:
        return f"{days}d {hours:02d}h {mins:02d}m"
    if hours:
        return f"{hours}h {mins:02d}m {secs:02d}s"
    return f"{mins}m {secs:02d}s"


def process_info() -> dict[str, Any]:
    return {
        "pid": os.getpid(),
        "uptime_s": round(uptime_seconds(), 1),
        "uptime_human": format_uptime(),
        "boot_unix": _BOOT_WALL,
        "thread_count": threading.active_count(),
    }
