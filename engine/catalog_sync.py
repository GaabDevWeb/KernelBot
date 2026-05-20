"""Sincronização de chaves indexadas e drift do catálogo (boot e /reload)."""

from __future__ import annotations

import logging

from app.state import AppServices
from core.config import Settings
from core.structured_log import ACL_MOD_CONTEXT, log_event, redact_secrets
from engine.database import fetch_indexed_lesson_keys
from engine.lesson_catalog import LessonCatalog

log = logging.getLogger(f"kernelbots.{__name__}")


def bootstrap_catalog_state(
    settings: Settings,
    *,
    indexed_lesson_keys: frozenset[str] | None = None,
) -> tuple[LessonCatalog | None, frozenset[str], dict | None]:
    """Carrega catálogo, chaves indexadas e relatório de drift."""
    keys = (
        indexed_lesson_keys
        if indexed_lesson_keys is not None
        else fetch_indexed_lesson_keys(settings)
    )
    lesson_catalog = LessonCatalog.load(settings) if settings.catalog_enabled else None
    catalog_drift_report: dict | None = None
    if lesson_catalog is not None:
        catalog_drift_report = lesson_catalog.audit_drift(keys)
        catalog_only = catalog_drift_report.get("catalog_only", [])
        if catalog_only:
            log.warning(
                "Catálogo: %d chave(s) sem correspondência no índice MySQL (catalog_only): %s",
                len(catalog_only),
                catalog_only[:20],
            )
    return lesson_catalog, keys, catalog_drift_report


def refresh_indexed_lesson_keys_state(services: AppServices) -> tuple[frozenset[str], bool]:
    """Re-sincroniza chaves indexadas e drift após rebuild BM25 (/reload).

    Em falha de MySQL mantém o snapshot anterior (fail-safe); não atribui
    ``frozenset()`` vazio salvo boot sem estado prévio.
    Retorna ``(chaves_efetivas, atualizou)``.
    """
    settings = services.context_manager.settings
    previous = services.indexed_lesson_keys
    try:
        new_keys = fetch_indexed_lesson_keys(settings)
    except Exception as e:
        log_event(
            log,
            logging.ERROR,
            ACL_MOD_CONTEXT,
            "indexed_lesson_keys_refresh_failed",
            "falha ao atualizar chaves indexadas — mantendo snapshot anterior",
            metadata={
                "error_type": type(e).__name__,
                "message_redacted": redact_secrets(str(e)),
                "previous_key_count": len(previous),
            },
            exc_info=True,
        )
        return previous, False

    services.indexed_lesson_keys = new_keys
    services.context_manager.refresh_indexed_lesson_keys(new_keys)
    if services.lesson_catalog is not None:
        report = services.lesson_catalog.audit_drift(new_keys)
        services.catalog_drift_report = report
        catalog_only = report.get("catalog_only", [])
        if catalog_only:
            log.warning(
                "Catálogo pós-reload: %d chave(s) catalog_only: %s",
                len(catalog_only),
                catalog_only[:20],
            )
    log_event(
        log,
        logging.INFO,
        ACL_MOD_CONTEXT,
        "indexed_lesson_keys_refreshed",
        "chaves de aula indexadas atualizadas apos reload",
        metadata={"key_count": len(new_keys)},
    )
    return new_keys, True
