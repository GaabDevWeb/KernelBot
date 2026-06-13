"""Fonte de dados MySQL para o índice BM25 (schema v2)."""
from __future__ import annotations

import logging
from importlib import import_module

from core.structured_log import ACL_MOD_DATABASE, log_event
from engine.lesson_catalog import normalize_lesson_key
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.config import Settings

log = logging.getLogger(f"kernelbots.{__name__}")

DB_CHUNK_WORDS   = 500
DB_CHUNK_OVERLAP = 50


def _chunk_text(text: str, title: str, source: str, discipline: str) -> list[dict]:
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
            "discipline": discipline,
        })
        if end == len(words):
            break
        start += DB_CHUNK_WORDS - DB_CHUNK_OVERLAP
    return chunks


def fetch_db_chunks(settings: Settings) -> list[dict]:
    """
    Busca rows ativas da tabela knowledge (v2) e retorna lista de chunks BM25.
    Retorna [] com warning se o DB não estiver configurado ou falhar.
    """
    if not all([settings.db_host, settings.db_name, settings.db_user]):
        log_event(
            log,
            logging.DEBUG,
            ACL_MOD_DATABASE,
            "fetch_chunks_skipped",
            "DB_* incompleto — sem MySQL",
            metadata={},
        )
        return []

    try:
        pymysql = import_module("pymysql")
        cursors_mod = import_module("pymysql.cursors")
    except ImportError:
        log_event(
            log,
            logging.WARNING,
            ACL_MOD_DATABASE,
            "pymysql_missing",
            "PyMySQL nao instalado",
            metadata={},
        )
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
                    "SELECT id, slug, title, discipline, `order`, content "
                    "FROM knowledge WHERE active = 1 ORDER BY discipline, `order`"
                )
                rows = cursor.fetchall()

        all_chunks: list[dict] = []
        for row in rows:
            discipline = row["discipline"]
            source = f"db:{discipline}/{row['slug']}"
            chunks = _chunk_text(row["content"], row["title"], source, discipline)
            all_chunks.extend(chunks)

        log_event(
            log,
            logging.INFO,
            ACL_MOD_DATABASE,
            "fetch_chunks_ok",
            "rows MySQL convertidos em chunks",
            metadata={"row_count": len(rows), "chunk_count": len(all_chunks)},
        )
        return all_chunks

    except Exception as e:
        # 2003 = can't connect (servidor parado, porta errada, firewall)
        if getattr(e, "args", None) and e.args and e.args[0] == 2003:
            log_event(
                log,
                logging.WARNING,
                ACL_MOD_DATABASE,
                "mysql_unreachable",
                "MySQL inacessivel — BM25 sem dados",
                metadata={
                    "host": settings.db_host,
                    "port": settings.db_port,
                    "error": str(e.args[1] if len(e.args) > 1 else e),
                },
            )
        else:
            log_event(
                log,
                logging.WARNING,
                ACL_MOD_DATABASE,
                "fetch_chunks_error",
                "falha ao ler knowledge",
                metadata={"error": str(e)},
            )
            log.warning("fetch_db_chunks detail", exc_info=True)
        return []


def fetch_db_discipline_ids(settings: Settings) -> frozenset[str]:
    """Return distinct discipline values from the DB (for silo registration)."""
    if not all([settings.db_host, settings.db_name, settings.db_user]):
        return frozenset()
    try:
        pymysql = import_module("pymysql")
        cursors_mod = import_module("pymysql.cursors")
    except ImportError:
        return frozenset()
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
            read_timeout=5,
        )
        with conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT DISTINCT discipline FROM knowledge WHERE active = 1")
                return frozenset(row["discipline"] for row in cursor.fetchall())
    except Exception as e:
        if getattr(e, "args", None) and e.args and e.args[0] == 2003:
            log_event(
                log,
                logging.WARNING,
                ACL_MOD_DATABASE,
                "disciplines_unreachable",
                "MySQL inacessivel ao listar disciplines",
                metadata={"host": settings.db_host, "port": settings.db_port},
            )
        else:
            log_event(
                log,
                logging.WARNING,
                ACL_MOD_DATABASE,
                "disciplines_query_error",
                "falha SELECT DISTINCT discipline",
                metadata={"error": str(e)},
            )
            log.warning("fetch_db_discipline_ids detail", exc_info=True)
        return frozenset()


def fetch_indexed_lesson_keys(settings: "Settings") -> frozenset[str]:
    """
    Chaves `discipline:slug` ativas no MySQL (knowledge), normalizadas como o catálogo.
    Retorna frozenset vazio com warning se o DB estiver indisponível.
    """
    if not all([settings.db_host, settings.db_name, settings.db_user]):
        log_event(
            log,
            logging.DEBUG,
            ACL_MOD_DATABASE,
            "indexed_keys_skipped",
            "DB_* incompleto — sem chaves indexadas",
            metadata={},
        )
        return frozenset()

    try:
        pymysql = import_module("pymysql")
        cursors_mod = import_module("pymysql.cursors")
    except ImportError:
        log_event(
            log,
            logging.WARNING,
            ACL_MOD_DATABASE,
            "indexed_keys_pymysql_missing",
            "PyMySQL nao instalado — chaves indexadas vazias",
            metadata={},
        )
        return frozenset()

    sql = (
        "SELECT DISTINCT discipline, slug FROM knowledge "
        "WHERE active = 1 AND content IS NOT NULL AND TRIM(content) <> ''"
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
            connect_timeout=5,
            read_timeout=10,
        )
        with conn:
            with conn.cursor() as cursor:
                cursor.execute(sql)
                rows = cursor.fetchall()

        keys = frozenset(
            normalize_lesson_key(str(row["discipline"]), str(row["slug"]))
            for row in rows
            if row.get("discipline") and row.get("slug")
        )
        log_event(
            log,
            logging.INFO,
            ACL_MOD_DATABASE,
            "indexed_keys_ok",
            "chaves de aula indexadas carregadas",
            metadata={"key_count": len(keys)},
        )
        return keys

    except Exception as e:
        if getattr(e, "args", None) and e.args and e.args[0] == 2003:
            log_event(
                log,
                logging.WARNING,
                ACL_MOD_DATABASE,
                "indexed_keys_unreachable",
                "MySQL inacessivel — boot sem chaves indexadas",
                metadata={"host": settings.db_host, "port": settings.db_port},
            )
        else:
            log_event(
                log,
                logging.WARNING,
                ACL_MOD_DATABASE,
                "indexed_keys_error",
                "falha ao listar discipline/slug",
                metadata={"error": str(e)},
            )
            log.warning("fetch_indexed_lesson_keys detail", exc_info=True)
        return frozenset()
