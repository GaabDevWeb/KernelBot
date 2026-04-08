"""Configuração centralizada de logging (stdlib)."""

from __future__ import annotations

import logging


def configure_logging(level: int = logging.INFO) -> None:
    """Configura o root logger uma vez; loggers filhos herdam o handler."""
    root = logging.getLogger()
    if root.handlers:
        return
    logging.basicConfig(
        level=level,
        format="%(asctime)s  %(levelname)-8s  [%(name)s]  %(message)s",
        datefmt="%H:%M:%S",
    )
