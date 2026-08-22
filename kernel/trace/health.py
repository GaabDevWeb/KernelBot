"""Métricas de saúde do processo (Flight Recorder — sem Prometheus)."""

from __future__ import annotations

import os
import resource
import shutil
from pathlib import Path
from typing import Any


def sample_system_metrics(*, db_path: Path | None = None) -> dict[str, Any]:
    """CPU/RAM/disco best-effort via stdlib (sem dependência psutil)."""
    usage = resource.getrusage(resource.RUSAGE_SELF)
    mem_mb = (usage.ru_maxrss or 0) / 1024.0
    # Linux: ru_maxrss em KB; macOS em bytes — heurística
    if mem_mb > 1024 * 50:  # claramente bytes
        mem_mb = (usage.ru_maxrss or 0) / (1024.0 * 1024.0)

    disk = None
    try:
        target = Path(db_path).parent if db_path else Path(".")
        du = shutil.disk_usage(str(target))
        disk = {
            "total_gb": round(du.total / (1024**3), 2),
            "used_gb": round(du.used / (1024**3), 2),
            "free_gb": round(du.free / (1024**3), 2),
            "used_pct": round(100.0 * du.used / du.total, 2) if du.total else None,
        }
    except OSError:
        disk = None

    loadavg = None
    try:
        loadavg = list(os.getloadavg())
    except (AttributeError, OSError):
        loadavg = None

    return {
        "rss_mb_approx": round(mem_mb, 2),
        "user_cpu_s": round(usage.ru_utime, 3),
        "system_cpu_s": round(usage.ru_stime, 3),
        "loadavg": loadavg,
        "disk": disk,
        "pid": os.getpid(),
    }
