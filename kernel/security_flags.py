"""Flags de segurança lidas do ambiente (sem dependência HTTP)."""

from __future__ import annotations

import os


def kernel_env() -> str:
    return (os.getenv("KERNELBOT_ENV") or "development").strip().lower()


def is_production() -> bool:
    return kernel_env() == "production"


def is_staging() -> bool:
    return kernel_env() == "staging"


def _env_flag(name: str, *, default: bool = False) -> bool:
    raw = (os.getenv(name) or "").strip().lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "on"}


def discipline_fail_closed() -> bool:
    """Se true, disciplina inválida não faz merge global de silos."""
    return _env_flag("ACL_DISCIPLINE_FAIL_CLOSED", default=is_production())
