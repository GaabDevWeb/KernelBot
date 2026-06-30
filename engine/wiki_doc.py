"""Ingestão da wiki (`docs/wiki/*.md`) para o silo MySQL `doc`."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from importlib import import_module
from pathlib import Path

from core.structured_log import ACL_MOD_DATABASE, log_event, redact_secrets
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.config import Settings

log = logging.getLogger(f"kernelbots.{__name__}")

_DOC_DISCIPLINE = "doc"
_TITLE_RE = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)
_ORDER_RE = re.compile(r"^(\d+)")


@dataclass(frozen=True)
class WikiPage:
    slug: str
    title: str
    content: str
    order: int


def _slug_from_path(path: Path) -> str:
    return path.stem


def _title_from_markdown(text: str, slug: str) -> str:
    match = _TITLE_RE.search(text)
    if match:
        return match.group(1).strip()
    return slug.replace("-", " ").title()


def _order_from_slug(slug: str, fallback: int) -> int:
    match = _ORDER_RE.match(slug)
    if match:
        return int(match.group(1))
    if slug.upper() == "README":
        return 0
    return fallback


def iter_wiki_pages(wiki_dir: Path) -> list[WikiPage]:
    """Lê `docs/wiki/*.md` e devolve páginas prontas para UPSERT em `knowledge`."""
    if not wiki_dir.is_dir():
        return []

    paths = sorted(wiki_dir.glob("*.md"))
    pages: list[WikiPage] = []
    for index, path in enumerate(paths):
        try:
            text = path.read_text(encoding="utf-8").strip()
        except OSError as exc:
            log_event(
                log,
                logging.WARNING,
                ACL_MOD_DATABASE,
                "wiki_doc_read_error",
                "falha ao ler pagina wiki",
                metadata={"path": str(path), "error": type(exc).__name__},
            )
            continue
        if not text:
            continue
        slug = _slug_from_path(path)
        pages.append(
            WikiPage(
                slug=slug,
                title=_title_from_markdown(text, slug),
                content=text,
                order=_order_from_slug(slug, 1000 + index),
            )
        )
    return pages


def ingest_wiki_to_mysql(settings: Settings, wiki_dir: Path | None = None) -> int:
    """UPSERT de todas as páginas wiki em `knowledge` (discipline=doc). Devolve contagem."""
    target = wiki_dir or (settings.project_root / "docs" / "wiki")
    pages = iter_wiki_pages(target)
    if not pages:
        log_event(
            log,
            logging.WARNING,
            ACL_MOD_DATABASE,
            "wiki_ingest_empty",
            "nenhuma pagina wiki para ingerir",
            metadata={"wiki_dir": str(target)},
        )
        return 0

    if not all([settings.db_host, settings.db_name, settings.db_user]):
        raise RuntimeError("DB_* incompleto — impossível ingerir wiki no MySQL.")

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
            read_timeout=30,
            write_timeout=30,
        )
        with conn:
            with conn.cursor() as cursor:
                for page in pages:
                    cursor.execute(
                        upsert_sql,
                        (_DOC_DISCIPLINE, page.slug, page.title, page.order, page.content),
                    )
            conn.commit()
    except Exception as exc:
        msg = str(exc.args[1] if getattr(exc, "args", None) and len(exc.args) > 1 else exc)
        log_event(
            log,
            logging.ERROR,
            ACL_MOD_DATABASE,
            "wiki_ingest_error",
            "falha ao upsert wiki no MySQL",
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
        "wiki_ingest_ok",
        "wiki ingerida no silo doc",
        metadata={
            "wiki_dir": str(target),
            "page_count": len(pages),
            "discipline": _DOC_DISCIPLINE,
        },
    )
    return len(pages)


def main() -> None:
    from core.config import Settings

    settings = Settings.load()
    count = ingest_wiki_to_mysql(settings)
    print(f"Ingest OK: {count} página(s) → knowledge (discipline=doc)")


if __name__ == "__main__":
    main()
