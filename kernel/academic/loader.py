"""Carregamento do catálogo académico (MySQL → fallback jsons/)."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from kernel.academic.catalog import AcademicCatalog
from kernel.config import Settings
from kernel.knowledge.database import fetch_db_document_meta
from kernel.knowledge.jsons_ingest import _LESSON_DISCIPLINE_DIRS

log = logging.getLogger(f"kernelbots.{__name__}")


def _rows_from_jsons(project_root: Path) -> list[dict]:
    jsons_dir = project_root / "jsons"
    if not jsons_dir.is_dir():
        return []
    rows: list[dict] = []
    for disc in _LESSON_DISCIPLINE_DIRS:
        disc_dir = jsons_dir / disc
        if not disc_dir.is_dir():
            continue
        for path in sorted(disc_dir.glob("*.json")):
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            discipline = str(raw.get("discipline") or disc).strip().lower()
            slug = str(raw.get("slug") or "").strip().lower()
            if not slug:
                continue
            order = int(raw.get("order") or 0)
            if order <= 0:
                continue
            title = str(raw.get("name") or raw.get("title") or slug).strip()
            rows.append(
                {
                    "discipline": discipline,
                    "slug": slug,
                    "title": title,
                    "order": order,
                    "source": f"db:{discipline}/{slug}",
                }
            )
    return rows


def load_academic_catalog(settings: Settings) -> AcademicCatalog | None:
    """SSOT: metadados MySQL; fallback dev/staging via `jsons/`."""
    iss_base = settings.iss_public_lesson_base
    meta = fetch_db_document_meta(settings)
    if meta:
        catalog = AcademicCatalog.from_rows(meta, iss_base=iss_base, source="mysql")
        if catalog is not None:
            return catalog
    rows = _rows_from_jsons(settings.project_root)
    if not rows:
        log.warning("AcademicCatalog: sem metadados MySQL nem jsons/ — catálogo académico indisponível")
        return None
    return AcademicCatalog.from_rows(rows, iss_base=iss_base, source="jsons")
