"""Ingestão de `jsons/<discipline>/*.json` para MySQL `knowledge` (dev/staging)."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from importlib import import_module
from pathlib import Path
from typing import TYPE_CHECKING, Any

from engine.database import META_END_MARKER, META_START_MARKER
from core.structured_log import ACL_MOD_DATABASE, log_event, redact_secrets

if TYPE_CHECKING:
    from core.config import Settings

log = logging.getLogger(f"kernelbots.{__name__}")

_FRONTMATTER_RE = re.compile(r"^---\s*\n.*?\n---\s*\n?", re.DOTALL)

# Disciplinas de aula (exclui doc — ingerido por wiki_doc).
_LESSON_DISCIPLINE_DIRS = (
    "fluencia-ia",
    "planejamento-curso-carreira",
    "projeto-bloco",
    "python",
    "python-processamento-dados",
    "sql-modelagem-relacional",
    "visualizacao-sql",
)


@dataclass(frozen=True)
class LessonRow:
    discipline: str
    slug: str
    title: str
    order: int
    content: str


def _csv_field(values: Any) -> str:
    if not values:
        return ""
    if isinstance(values, str):
        return values.strip()
    return ", ".join(str(v).strip() for v in values if str(v).strip())


def _objectives_field(values: Any) -> str:
    if not values:
        return ""
    if isinstance(values, str):
        return values.strip()
    return "; ".join(str(v).strip() for v in values if str(v).strip())


def build_meta_header(
    *,
    discipline: str,
    title: str,
    concepts: Any,
    keywords: Any,
    objectives: Any,
) -> str:
    return (
        f"{META_START_MARKER}\n"
        f"Disciplina: {discipline}\n"
        f"Título: {title}\n"
        f"Conceitos: {_csv_field(concepts)}\n"
        f"Keywords: {_csv_field(keywords)}\n"
        f"Objetivos: {_objectives_field(objectives)}\n"
        f"{META_END_MARKER}\n"
    )


def _strip_frontmatter(markdown: str) -> str:
    return _FRONTMATTER_RE.sub("", markdown.strip(), count=1).strip()


def _lesson_from_json(path: Path) -> LessonRow | None:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        log_event(
            log,
            logging.WARNING,
            ACL_MOD_DATABASE,
            "jsons_ingest_read_error",
            "falha ao ler json de aula",
            metadata={"path": str(path), "error": type(exc).__name__},
        )
        return None

    discipline = str(raw.get("discipline") or "").strip()
    slug = str(raw.get("slug") or "").strip()
    if not discipline or not slug:
        return None

    title = str(raw.get("name") or raw.get("title") or slug).strip()
    order = int(raw.get("order") or 0)
    body_md = _strip_frontmatter(str(raw.get("content") or ""))
    meta = build_meta_header(
        discipline=discipline,
        title=title,
        concepts=raw.get("concepts"),
        keywords=raw.get("keywords"),
        objectives=raw.get("learning_objectives"),
    )
    content = f"{meta}\n{body_md}" if body_md else meta.rstrip()
    return LessonRow(
        discipline=discipline,
        slug=slug,
        title=title,
        order=order,
        content=content,
    )


def iter_lesson_rows(jsons_dir: Path) -> list[LessonRow]:
    rows: list[LessonRow] = []
    for disc in _LESSON_DISCIPLINE_DIRS:
        disc_dir = jsons_dir / disc
        if not disc_dir.is_dir():
            continue
        for path in sorted(disc_dir.glob("*.json")):
            row = _lesson_from_json(path)
            if row:
                rows.append(row)
    return rows


def ingest_jsons_to_mysql(settings: Settings, jsons_dir: Path | None = None) -> dict[str, int]:
    """UPSERT aulas de `jsons/`; devolve contagem por disciplina."""
    target = jsons_dir or (settings.project_root / "jsons")
    rows = iter_lesson_rows(target)
    if not rows:
        log_event(
            log,
            logging.WARNING,
            ACL_MOD_DATABASE,
            "jsons_ingest_empty",
            "nenhuma aula json para ingerir",
            metadata={"jsons_dir": str(target)},
        )
        return {}

    if not all([settings.db_host, settings.db_name, settings.db_user]):
        raise RuntimeError("DB_* incompleto — impossível ingerir jsons no MySQL.")

    try:
        pymysql = import_module("pymysql")
        cursors_mod = import_module("pymysql.cursors")
    except ImportError as exc:
        raise RuntimeError("PyMySQL não instalado — pip install pymysql") from exc

    upsert_sql = (
        "INSERT INTO knowledge (discipline, slug, title, `order`, content, active) "
        "VALUES (%s, %s, %s, %s, %s, 1) "
        "ON DUPLICATE KEY UPDATE "
        "title = VALUES(title), "
        "`order` = VALUES(`order`), "
        "content = VALUES(content), "
        "active = 1, "
        "updated_at = CURRENT_TIMESTAMP"
    )

    counts: dict[str, int] = {}
    try:
        conn = pymysql.connect(
            host=settings.db_host,
            port=settings.db_port,
            database=settings.db_name,
            user=settings.db_user,
            password=settings.db_password,
            charset="utf8mb4",
            cursorclass=cursors_mod.DictCursor,
            connect_timeout=10,
            read_timeout=120,
            write_timeout=120,
        )
        with conn:
            with conn.cursor() as cursor:
                for row in rows:
                    cursor.execute(
                        upsert_sql,
                        (row.discipline, row.slug, row.title, row.order, row.content),
                    )
                    counts[row.discipline] = counts.get(row.discipline, 0) + 1
            conn.commit()
    except Exception as exc:
        msg = str(exc.args[1] if getattr(exc, "args", None) and len(exc.args) > 1 else exc)
        log_event(
            log,
            logging.ERROR,
            ACL_MOD_DATABASE,
            "jsons_ingest_error",
            "falha ao upsert jsons no MySQL",
            metadata={
                "host": settings.db_host,
                "port": settings.db_port,
                "database": settings.db_name,
                "message_redacted": redact_secrets(msg),
            },
            exc_info=True,
        )
        raise

    log_event(
        log,
        logging.INFO,
        ACL_MOD_DATABASE,
        "jsons_ingest_ok",
        "aulas json ingeridas no MySQL",
        metadata={"jsons_dir": str(target), "total": len(rows), "by_discipline": counts},
    )
    return counts


def main() -> None:
    from core.config import Settings

    settings = Settings.load()
    counts = ingest_jsons_to_mysql(settings)
    total = sum(counts.values())
    print(f"Ingest OK: {total} aula(s) → knowledge")
    for disc in sorted(counts):
        print(f"  {disc}: {counts[disc]}")


if __name__ == "__main__":
    main()
