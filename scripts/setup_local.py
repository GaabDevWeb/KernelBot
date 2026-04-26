#!/usr/bin/env python3
"""
Setup local: pip (opcional), verifica .env, cria base MySQL, aplica SQL/schema.sql,
ingere Markdown de content/ → tabela knowledge.

Uso:
  python scripts/setup_local.py
  python scripts/setup_local.py --no-pip --skip-ingest

Depois:
  python main.py
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import re
import subprocess
import sys
from pathlib import Path

log = logging.getLogger("setup_local")

ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = ROOT / "SQL" / "schema.sql"
CONTENT_ROOT = ROOT / "content"
DOTENV_PATH = ROOT / ".env"
DOTENV_EXAMPLE = ROOT / ".env.example"

# Erro comum: .env com 127.0.0.0 em vez de 127.0.0.1 (timeout ao conectar).
_DB_HOST_LOOPBACK_TYPO = "127.0.0.0"


def _normalize_db_host(host: str) -> str:
    h = (host or "").strip().strip("'\"")
    if h == _DB_HOST_LOOPBACK_TYPO:
        log.warning(
            "DB_HOST era '%s' (nao e o loopback habitual). A usar '127.0.0.1'. Corrija o .env.",
            _DB_HOST_LOOPBACK_TYPO,
        )
        return "127.0.0.1"
    return h


def _configure_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(levelname)s %(message)s",
    )


def _load_dotenv() -> None:
    try:
        from dotenv import load_dotenv

        load_dotenv(DOTENV_PATH)
    except ImportError:
        pass


def _ensure_env_file() -> None:
    if DOTENV_PATH.is_file():
        return
    if DOTENV_EXAMPLE.is_file():
        import shutil

        shutil.copy(DOTENV_EXAMPLE, DOTENV_PATH)
        log.warning("Criado .env a partir de .env.example — preencha OPENROUTER_API_KEY e DB_*.")
    else:
        log.error("Falta .env e .env.example na raiz do projeto.")
        sys.exit(1)


def _db_params() -> dict[str, object]:
    host = _normalize_db_host(os.getenv("DB_HOST") or "")
    port_raw = (os.getenv("DB_PORT") or "3306").strip()
    name = (os.getenv("DB_NAME") or "").strip()
    user = (os.getenv("DB_USER") or "").strip()
    password = os.getenv("DB_PASSWORD") or ""
    try:
        port = int(port_raw)
    except ValueError:
        log.error("DB_PORT invalido.")
        sys.exit(1)
    return {"host": host, "port": port, "database": name, "user": user, "password": password}


def _require_db_env_only() -> dict[str, object]:
    """Apenas MySQL — para ingest isolado sem OpenRouter."""
    _ensure_env_file()
    _load_dotenv()
    db = _db_params()
    missing: list[str] = []
    if not db["host"]:
        missing.append("DB_HOST")
    if not db["database"]:
        missing.append("DB_NAME")
    if not (db["user"] or "").strip():
        missing.append("DB_USER")
    if missing:
        log.error("Variaveis ausentes no .env: %s", ", ".join(missing))
        sys.exit(1)
    return db


def _require_env_for_full_setup() -> dict[str, object]:
    _ensure_env_file()
    _load_dotenv()
    key = (os.getenv("OPENROUTER_API_KEY") or "").strip()
    db = _db_params()
    missing: list[str] = []
    if not key:
        missing.append("OPENROUTER_API_KEY")
    if not db["host"]:
        missing.append("DB_HOST")
    if not db["database"]:
        missing.append("DB_NAME")
    if not (db["user"] or "").strip():
        missing.append("DB_USER")
    if missing:
        log.error("Variaveis ausentes no .env: %s", ", ".join(missing))
        log.error("Edite %s e volte a executar este script.", DOTENV_PATH)
        sys.exit(1)
    return db


def _connect_mysql(*, database: str | None) -> "object":
    import pymysql

    db = _db_params()
    kwargs: dict = {
        "host": db["host"],
        "port": int(db["port"]),
        "user": db["user"],
        "password": db["password"],
        "charset": "utf8mb4",
        "autocommit": True,
    }
    if database is not None:
        kwargs["database"] = database
    kwargs["connect_timeout"] = 15
    try:
        return pymysql.connect(**kwargs)
    except pymysql.err.OperationalError as e:
        _log_mysql_connection_help(e)
        raise SystemExit(1) from e
    except RuntimeError as e:
        if "cryptography" in str(e).lower():
            log.error("%s", e)
            log.error(
                "MySQL 8 (caching_sha2_password) exige o pacote 'cryptography'. "
                "Corra de novo sem --no-pip ou: pip install cryptography"
            )
            raise SystemExit(1) from e
        raise


def _log_mysql_connection_help(exc: BaseException) -> None:
    db = _db_params()
    log.error("Nao foi possivel ligar ao MySQL em %s:%s", db["host"], db["port"])
    log.error("Detalhe: %s", exc)
    log.error(
        "Checklist: servico MySQL a correr; DB_HOST (use 127.0.0.1 ou localhost, "
        "nao 127.0.0.0); DB_PORT=3306; utilizador e palavra-passe corretos; firewall."
    )


def _create_database_and_schema(db_name: str) -> None:
    if not SCHEMA_PATH.is_file():
        log.error("Ficheiro em falta: %s", SCHEMA_PATH)
        sys.exit(1)
    sql = SCHEMA_PATH.read_text(encoding="utf-8")
    conn = _connect_mysql(database=None)
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"CREATE DATABASE IF NOT EXISTS `{db_name}` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
    finally:
        conn.close()

    conn = _connect_mysql(database=db_name)
    try:
        with conn.cursor() as cur:
            for stmt in _split_sql_statements(sql):
                if stmt:
                    cur.execute(stmt)
    finally:
        conn.close()
    log.info("Schema aplicado em %s.", db_name)


def _split_sql_statements(sql: str) -> list[str]:
    """Divide por ';' em linha propria ou fim — suficiente para schema.sql simples."""
    parts: list[str] = []
    buf: list[str] = []
    for line in sql.splitlines():
        s = line.strip()
        if not s or s.startswith("--"):
            continue
        if s.endswith(";"):
            buf.append(s[:-1].strip())
            parts.append("\n".join(buf))
            buf = []
        else:
            buf.append(s)
    if buf:
        parts.append("\n".join(buf))
    return [p for p in parts if p.strip()]


def _parse_front_matter(raw: str) -> tuple[dict, str]:
    if not raw.startswith("---"):
        return {}, raw
    end = raw.find("\n---", 3)
    if end == -1:
        return {}, raw
    yaml_block = raw[3:end].strip()
    body = raw[end + 4 :].lstrip("\n")
    try:
        import yaml

        meta = yaml.safe_load(yaml_block) or {}
    except Exception as e:
        log.warning("YAML invalido, a usar metadados inferidos: %s", e)
        return {}, raw
    if not isinstance(meta, dict):
        return {}, raw
    return meta, body


def _infer_order_from_stem(stem: str) -> int:
    m = re.match(r"aula-(\d+)-", stem, re.IGNORECASE)
    if m:
        return int(m.group(1))
    return 999


def _infer_title_from_body(body: str, stem: str) -> str:
    for line in body.splitlines():
        line = line.strip()
        if line.startswith("# "):
            return line[2:].strip()
        if line.startswith("#"):
            continue
        if line:
            break
    return stem.replace("-", " ").replace("_", " ").title()


def _build_row(path: Path, rel_under_content: Path, raw_bytes: bytes, raw_text: str) -> dict | None:
    meta, body = _parse_front_matter(raw_text)
    discipline = str(meta.get("discipline") or rel_under_content.parts[0]).strip()
    slug = str(meta.get("slug") or path.stem).strip()
    title = str(meta.get("title") or _infer_title_from_body(body, path.stem)).strip()
    order = meta.get("order")
    if order is None:
        order = _infer_order_from_stem(path.stem)
    try:
        order = int(order)
    except (TypeError, ValueError):
        order = _infer_order_from_stem(path.stem)

    if not slug or not discipline or not title:
        log.warning("Ignorado (metadados incompletos): %s", path)
        return None

    payload = dict(meta) if meta else {}
    payload.setdefault("slug", slug)
    payload.setdefault("discipline", discipline)
    payload.setdefault("title", title)
    payload.setdefault("order", order)
    if not meta:
        payload["_ingest"] = "synthetic_from_path"

    content_body = body.strip() or raw_text.strip()
    checksum = hashlib.sha256(raw_bytes).hexdigest()

    return {
        "slug": slug,
        "discipline": discipline,
        "title": title,
        "order": order,
        "content": content_body,
        "payload": json.dumps(payload, ensure_ascii=False, default=str),
        "source_checksum": checksum,
    }


def ingest_all_markdown(*, dry_run: bool = False) -> tuple[int, int]:
    """Devolve (inseridos_ou_atualizados, ignorados_mesmo_checksum)."""
    if not CONTENT_ROOT.is_dir():
        log.error("Pasta content/ nao encontrada.")
        sys.exit(1)

    db_name = str(_db_params()["database"])
    rows: list[dict] = []
    for path in sorted(CONTENT_ROOT.rglob("*.md")):
        if "__pycache__" in path.parts:
            continue
        try:
            rel = path.relative_to(CONTENT_ROOT)
        except ValueError:
            continue
        raw_bytes = path.read_bytes()
        try:
            raw_text = raw_bytes.decode("utf-8")
        except UnicodeDecodeError:
            raw_text = raw_bytes.decode("utf-8", errors="replace")
        row = _build_row(path, rel, raw_bytes, raw_text)
        if row:
            rows.append(row)

    if dry_run:
        log.info("[dry-run] %d ficheiros .md prontos para ingestao.", len(rows))
        return len(rows), 0

    conn = _connect_mysql(database=db_name)
    inserted = 0
    skipped = 0
    try:
        with conn.cursor() as cur:
            for r in rows:
                cur.execute(
                    "SELECT source_checksum FROM knowledge WHERE slug = %s",
                    (r["slug"],),
                )
                existing = cur.fetchone()
                if existing and existing[0] == r["source_checksum"]:
                    skipped += 1
                    continue
                cur.execute(
                    """
                    INSERT INTO knowledge (
                        slug, discipline, title, `order`, content, payload,
                        payload_version, source_checksum, active
                    ) VALUES (%s, %s, %s, %s, %s, %s, 1, %s, 1)
                    ON DUPLICATE KEY UPDATE
                        discipline = VALUES(discipline),
                        title = VALUES(title),
                        `order` = VALUES(`order`),
                        content = VALUES(content),
                        payload = VALUES(payload),
                        source_checksum = VALUES(source_checksum),
                        active = 1
                    """,
                    (
                        r["slug"],
                        r["discipline"],
                        r["title"],
                        r["order"],
                        r["content"],
                        r["payload"],
                        r["source_checksum"],
                    ),
                )
                inserted += 1
    finally:
        conn.close()

    log.info("Ingestao: %d linhas gravadas/atualizadas, %d ignoradas (checksum igual).", inserted, skipped)
    return inserted, skipped


def _pip_install() -> None:
    req = ROOT / "requirements.txt"
    if not req.is_file():
        log.warning("requirements.txt nao encontrado.")
        return
    log.info("A instalar dependencias (pip)...")
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-q", "-r", str(req)],
        check=True,
        cwd=str(ROOT),
    )
    log.info("pip install concluido.")


def run_setup(*, pip_install: bool, skip_ingest: bool, dry_run: bool, verbose: bool) -> None:
    _configure_logging(verbose)
    _require_env_for_full_setup()

    if pip_install:
        _pip_install()

    db = _db_params()
    db_name = str(db["database"])
    _create_database_and_schema(db_name)

    if not skip_ingest:
        ingest_all_markdown(dry_run=dry_run)
    else:
        log.info("Ingestao ignorada (--skip-ingest).")

    if not dry_run:
        conn = _connect_mysql(database=db_name)
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM knowledge WHERE active = 1")
                n = cur.fetchone()[0]
            log.info("Linhas ativas em knowledge: %d", n)
        finally:
            conn.close()

    log.info("Pronto. Inicie o servidor com: python main.py")


def main() -> None:
    p = argparse.ArgumentParser(description="Setup MySQL + ingestao content/")
    p.add_argument("--no-pip", action="store_true", help="Nao executar pip install -r requirements.txt")
    p.add_argument("--skip-ingest", action="store_true", help="So criar base e schema")
    p.add_argument("--dry-run", action="store_true", help="So listar ingestao sem escrever no MySQL")
    p.add_argument("-v", "--verbose", action="store_true")
    args = p.parse_args()
    run_setup(
        pip_install=not args.no_pip,
        skip_ingest=args.skip_ingest,
        dry_run=args.dry_run,
        verbose=args.verbose,
    )


if __name__ == "__main__":
    main()
