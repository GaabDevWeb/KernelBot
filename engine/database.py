"""Fonte de dados MySQL para o índice BM25."""
from __future__ import annotations

import json
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


def insert_knowledge(
    settings: Settings,
    *,
    slug: str,
    discipline: str,
    title: str,
    order: int,
    content: str,
    payload: dict,
    source_checksum: str,
) -> tuple[int, bool]:
    """
    Insere ou atualiza um registro na tabela knowledge (upsert por slug).

    Retorna (id, changed):
    - changed=True  → inserido ou atualizado (checksum diferente)
    - changed=False → ignorado (checksum idêntico, sem mudança)
    """
    if not all([settings.db_host, settings.db_name, settings.db_user]):
        raise RuntimeError("Variáveis DB_* não configuradas — impossível inserir.")

    try:
        import_module("pymysql")
    except ImportError:
        raise RuntimeError("PyMySQL não instalado.") from None

    payload_json = json.dumps(payload, ensure_ascii=False)

    conn = _get_connection(settings)
    with conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT id, source_checksum FROM knowledge WHERE slug = %s",
                (slug,),
            )
            existing = cursor.fetchone()

            if existing:
                if existing["source_checksum"] == source_checksum:
                    log.debug("⏭  slug=%r já existe com mesmo checksum — ignorado.", slug)
                    return existing["id"], False

                cursor.execute(
                    """
                    UPDATE knowledge
                       SET discipline       = %s,
                           title           = %s,
                           `order`         = %s,
                           content         = %s,
                           payload         = %s,
                           source_checksum = %s,
                           active          = 1
                     WHERE slug = %s
                    """,
                    (discipline, title, order, content, payload_json, source_checksum, slug),
                )
                conn.commit()
                log.info("✏️  Atualizado slug=%r id=%s", slug, existing["id"])
                return existing["id"], True

            cursor.execute(
                """
                INSERT INTO knowledge
                    (slug, discipline, title, `order`, content, payload, payload_version, source_checksum)
                VALUES (%s, %s, %s, %s, %s, %s, 1, %s)
                """,
                (slug, discipline, title, order, content, payload_json, source_checksum),
            )
            conn.commit()
            new_id = cursor.lastrowid
            log.info("✅  Inserido slug=%r id=%s", slug, new_id)
            return new_id, True
