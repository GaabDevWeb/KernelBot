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


def _get_connection(settings: Settings):
    pymysql = import_module("pymysql")
    cursors_mod = import_module("pymysql.cursors")
    return pymysql.connect(
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


def fetch_db_chunks(settings: Settings) -> list[dict]:
    """
    Busca rows ativas da tabela knowledge e retorna lista de chunks BM25.
    Retorna [] com warning se o DB não estiver configurado ou falhar.
    """
    if not all([settings.db_host, settings.db_name, settings.db_user]):
        log.debug("Variáveis DB_* não configuradas — pulando fonte MySQL.")
        return []

    try:
        import_module("pymysql")
    except ImportError:
        log.warning("PyMySQL não instalado — fonte MySQL desativada.")
        return []

    try:
        conn = _get_connection(settings)
        with conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT id, title, content, discipline "
                    "FROM knowledge WHERE active = 1 ORDER BY `order`, id"
                )
                rows = cursor.fetchall()

        all_chunks: list[dict] = []
        for row in rows:
            discipline = row["discipline"]
            source = f"db:{discipline}"
            chunks = _chunk_text(row["content"], row["title"], source, discipline)
            all_chunks.extend(chunks)
            log.debug("   🗄  row id=%s '%s' → %s chunk(s)", row["id"], row["title"], len(chunks))

        log.info("   🗄  MySQL: %s row(s) → %s chunk(s) carregados", len(rows), len(all_chunks))
        return all_chunks

    except Exception:
        log.warning("⚠  Falha ao conectar ao MySQL — continuando apenas com .md.", exc_info=True)
        return []


def get_all_existing_orders(settings: Settings) -> dict[str, set[int]]:
    """
    Retorna {discipline: {order, ...}} para todas as rows ativas.
    Retorna {} se o DB não estiver configurado ou falhar.
    """
    if not all([settings.db_host, settings.db_name, settings.db_user]):
        return {}
    try:
        import_module("pymysql")
    except ImportError:
        return {}
    try:
        conn = _get_connection(settings)
        with conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT discipline, `order` FROM knowledge WHERE active = 1",
                )
                rows = cursor.fetchall()
        result: dict[str, set[int]] = {}
        for row in rows:
            result.setdefault(row["discipline"], set()).add(row["order"])
        return result
    except Exception:
        log.warning("⚠  Falha ao consultar orders existentes — continuando sem filtro.", exc_info=True)
        return {}


def get_existing_orders(settings: Settings, discipline: str) -> set[int]:
    """
    Retorna os valores de `order` já cadastrados para a disciplina informada.
    Retorna set vazio se o DB não estiver configurado ou falhar.
    """
    if not all([settings.db_host, settings.db_name, settings.db_user]):
        return set()
    try:
        import_module("pymysql")
    except ImportError:
        return set()
    try:
        conn = _get_connection(settings)
        with conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT `order` FROM knowledge WHERE discipline = %s AND active = 1",
                    (discipline,),
                )
                rows = cursor.fetchall()
        return {row["order"] for row in rows}
    except Exception:
        log.warning("⚠  Falha ao consultar orders existentes — continuando sem filtro.", exc_info=True)
        return set()


def insert_knowledge(
    settings: Settings,
    *,
    slug: str,
    discipline: str,
    title: str,
    order: int,
    description: str,
    content: str,
    keywords: str | None = None,
    learning_objectives: str | None = None,
    concepts: str | None = None,
) -> tuple[int, str]:
    """
    Insere ou atualiza um registro na tabela knowledge (upsert por slug+discipline).

    Sem UNIQUE em slug, a deduplicação é feita por SELECT prévio:
    - Se existe row com (slug, discipline) → UPDATE → status="updated"
    - Caso contrário → INSERT → status="inserted"
    """
    if not all([settings.db_host, settings.db_name, settings.db_user]):
        raise RuntimeError("Variáveis DB_* não configuradas — impossível inserir.")

    try:
        import_module("pymysql")
    except ImportError:
        raise RuntimeError("PyMySQL não instalado.") from None

    conn = _get_connection(settings)
    with conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT id FROM knowledge WHERE slug = %s AND discipline = %s LIMIT 1",
                (slug, discipline),
            )
            existing = cursor.fetchone()

            if existing:
                cursor.execute(
                    """
                    UPDATE knowledge
                       SET title               = %s,
                           description         = %s,
                           `order`             = %s,
                           keywords            = %s,
                           learning_objectives = %s,
                           content             = %s,
                           concepts            = %s,
                           active              = 1
                     WHERE id = %s
                    """,
                    (title, description, order, keywords, learning_objectives,
                     content, concepts, existing["id"]),
                )
                conn.commit()
                log.info("✏️  Atualizado slug=%r id=%s", slug, existing["id"])
                return existing["id"], "updated"

            cursor.execute(
                """
                INSERT INTO knowledge
                    (slug, discipline, title, description, `order`,
                     keywords, learning_objectives, content, concepts)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (slug, discipline, title, description, order,
                 keywords, learning_objectives, content, concepts),
            )
            conn.commit()
            new_id = cursor.lastrowid
            log.info("✅  Inserido slug=%r id=%s", slug, new_id)
            return new_id, "inserted"
