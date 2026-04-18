"""Fonte de dados MySQL para o índice BM25."""
from __future__ import annotations

import logging
from importlib import import_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.config import Settings

log = logging.getLogger(f"kernelbots.{__name__}")

DB_CHUNK_WORDS   = 500
DB_CHUNK_OVERLAP = 50


def _chunk_text(text: str, title: str, source: str) -> list[dict]:
    """Divide texto em janelas de ~500 palavras com overlap de 50."""
    words = text.split()
    if not words:
        return []
    chunks: list[dict] = []
    start = 0
    while start < len(words):
        end = min(start + DB_CHUNK_WORDS, len(words))
        chunks.append({
            "text": f"{title}\n" + " ".join(words[start:end]),
            "source": source,
            "discipline": "db",
        })
        if end == len(words):
            break
        start += DB_CHUNK_WORDS - DB_CHUNK_OVERLAP
    return chunks


def fetch_db_chunks(settings: Settings) -> list[dict]:
    """
    Busca rows ativas da tabela knowledge e retorna lista de chunks BM25.
    Retorna [] com warning se o DB não estiver configurado ou falhar.
    """
    if not all([settings.db_host, settings.db_name, settings.db_user]):
        log.debug("Variáveis DB_* não configuradas — pulando fonte MySQL.")
        return []

    try:
        pymysql = import_module("pymysql")
        cursors_mod = import_module("pymysql.cursors")
    except ImportError:
        log.warning("PyMySQL não instalado — fonte MySQL desativada.")
        return []

    try:
        conn = pymysql.connect(
            host=settings.db_host,
            port=settings.db_port,
            database=settings.db_name,
            user=settings.db_user,
            password=settings.db_password,
            charset="utf8mb4",
            cursorclass=cursors_mod.DictCursor,
            connect_timeout=5,
            read_timeout=10,
        )
        with conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT id, title, content, category "
                    "FROM knowledge WHERE active = 1 ORDER BY id"
                )
                rows = cursor.fetchall()

        all_chunks: list[dict] = []
        for row in rows:
            source = f"db:{row['category']}"
            chunks = _chunk_text(row["content"], row["title"], source)
            all_chunks.extend(chunks)
            log.debug("   🗄  row id=%s '%s' → %s chunk(s)", row["id"], row["title"], len(chunks))

        log.info("   🗄  MySQL: %s row(s) → %s chunk(s) carregados", len(rows), len(all_chunks))
        return all_chunks

    except Exception:
        log.warning("⚠  Falha ao conectar ao MySQL — continuando apenas com .md.", exc_info=True)
        return []