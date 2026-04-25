"""Configuração centralizada de logging (stdlib)."""

from __future__ import annotations

import logging
import os

from core.structured_log import AclLogFormatter


def configure_logging(level: int | None = None) -> None:
    """Configura o root uma vez.

    - ``ACL_LOG_FORMAT=json`` — uma linha JSON por evento ACL (``log_event``).
    - ``ACL_LOG_LEVEL=DEBUG`` — inclui eventos DEBUG (ex.: inputs antes dos gates).
    """
    root = logging.getLogger()
    if root.handlers:
        return
    if level is None:
        name = (os.getenv("ACL_LOG_LEVEL") or "INFO").strip().upper()
        level = getattr(logging, name, logging.INFO)
    json_mode = (os.getenv("ACL_LOG_FORMAT") or "text").strip().lower() == "json"
    handler = logging.StreamHandler()
    handler.setFormatter(AclLogFormatter(json_mode=json_mode))
    root.addHandler(handler)
    root.setLevel(level)
