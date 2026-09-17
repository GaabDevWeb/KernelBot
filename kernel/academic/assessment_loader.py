"""Ingestão de TP/AT a partir de `tps-assessments-infnet/` (branch true-kernel)."""

from __future__ import annotations

import logging
import re
from pathlib import Path

from kernel.academic.models import AssessmentEntry

log = logging.getLogger(f"kernelbots.{__name__}")

# Pastas no repo → ids canónicos de disciplina (disciplines.json).
FOLDER_TO_DISCIPLINE: dict[str, str] = {
    "java": "fundamentos-java",
    "csharp": "fundamentos-csharp",
    "projeto-bloco-backend": "projeto-bloco-backend",
}

_TITLE_RE = re.compile(r"^#\s+(.+)$", re.MULTILINE)
_ACTIVITY_URL_RE = re.compile(
    r"\*\*Atividade:\*\*\s+\[[^\]]+\]\((https?://[^)]+)\)",
    re.IGNORECASE,
)
_DUE_DATE_RE = re.compile(
    r"\*\*Data de entrega:\*\*\s+(.+)$",
    re.MULTILINE | re.IGNORECASE,
)


def _parse_stem(stem: str) -> tuple[str, int | None, str]:
    if stem == "assessment":
        return "assessment", None, "assessment"
    if stem == "entrega-de-projeto":
        return "entrega", None, "entrega-de-projeto"
    m = re.fullmatch(r"tp(\d+)", stem, re.IGNORECASE)
    if m:
        n = int(m.group(1))
        return "tp", n, stem.lower()
    m = re.fullmatch(r"at(\d+)", stem, re.IGNORECASE)
    if m:
        n = int(m.group(1))
        return "at", n, stem.lower()
    return "other", None, stem.lower()


def _parse_markdown_meta(text: str) -> tuple[str, str | None, str | None]:
    title = ""
    m = _TITLE_RE.search(text)
    if m:
        title = m.group(1).strip()
    url_m = _ACTIVITY_URL_RE.search(text)
    url = url_m.group(1).strip() if url_m else None
    due_m = _DUE_DATE_RE.search(text)
    due = due_m.group(1).strip() if due_m else None
    return title, url, due


def load_assessment_entries(root: Path) -> tuple[AssessmentEntry, ...]:
    """Carrega entradas a partir de `tps-assessments-infnet/`."""
    if not root.is_dir():
        log.warning("Assessment loader: pasta inexistente %s", root)
        return ()

    entries: list[AssessmentEntry] = []
    for folder, discipline in sorted(FOLDER_TO_DISCIPLINE.items()):
        disc_dir = root / folder
        if not disc_dir.is_dir():
            continue
        for path in sorted(disc_dir.glob("*.md")):
            try:
                text = path.read_text(encoding="utf-8")
            except OSError as exc:
                log.warning("Assessment loader: falha ao ler %s: %s", path, exc)
                continue
            kind, number, slug = _parse_stem(path.stem)
            if kind == "other":
                log.debug("Assessment loader: ignorado %s (nome não reconhecido)", path.name)
                continue
            title, url, due = _parse_markdown_meta(text)
            rel = path.relative_to(root.parent).as_posix()
            entry_id = f"{discipline}:{slug}"
            entries.append(
                AssessmentEntry(
                    id=entry_id,
                    discipline=discipline,
                    kind=kind,
                    number=number,
                    title=title or path.stem.upper(),
                    slug=slug,
                    url=url,
                    source=rel,
                    content_path=str(path),
                    due_date=due,
                )
            )
    log.info(
        "AssessmentCatalog: %d entradas carregadas de %s",
        len(entries),
        root,
    )
    return tuple(entries)
