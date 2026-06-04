"""Logging estruturado (JSON ou texto) para auditoria e debugging do ACL.

Campos estáveis em ``metadata`` (snake_case):
  query, top_score, second_score, score_margin, decision, reason, confidence,
  mode, discipline_filter, informative_terms, coverage, coverage_weighted,
  candidate_count, selected_sources, llm_called, tokens_used, model, ...

Erros MySQL (``module=database``) — contrato de observabilidade:
  - ``event``: identificador estável (ex. ``fetch_chunks_error``, ``indexed_keys_error``)
  - ``metadata.host`` / ``metadata.port`` quando a falha é de conectividade
  - ``metadata.error_type``: nome da excepção (``OperationalError``, …)
  - ``metadata.message_redacted``: mensagem sanitizada (``redact_secrets``)
  - traceback: ``exc_info=True`` em ``log_event`` — anexado ao registo (campo
    ``traceback`` em JSON; bloco após a linha em modo texto)

Sanitização: ``redact_secrets`` em mensagens, metadata e traceback; padrões
``password=``, ``DB_PASSWORD``, URLs com credenciais, fragmentos PyMySQL.

Variável de ambiente: ACL_LOG_FORMAT=json | text (default: text).
"""

from __future__ import annotations

import datetime as _dt
import json
import logging
import os
import re
from typing import Any, Mapping

# Módulos lógicos (filtro em ferramentas: module=...)
ACL_MOD_SEARCH = "search"
ACL_MOD_CONTEXT = "context"
ACL_MOD_DECISION = "decision"
ACL_MOD_PROVIDER = "provider"
ACL_MOD_EVALUATION = "evaluation"
ACL_MOD_DATABASE = "database"

ACL_EXTRA = "acl_payload"
_MAX_QUERY_META = 512
_MAX_LIST_META = 24

_SECRET_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"(password\s*[=:]\s*)[^\s,\)\'\"]+", re.IGNORECASE), r"\1***"),
    (re.compile(r"(DB_PASSWORD\s*[=:]\s*)[^\s,\)\'\"]+", re.IGNORECASE), r"\1***"),
    (re.compile(r"(//[^:]+:)[^@\s/]+(@)", re.IGNORECASE), r"\1***\2"),
    (
        re.compile(
            r"(pymysql\.[^\s]*password[\"']?\s*[=:]\s*)[^\s,\)]+",
            re.IGNORECASE,
        ),
        r"\1***",
    ),
]


def redact_secrets(text: str) -> str:
    """Remove credenciais de strings de log (mensagem, metadata, traceback)."""
    s = str(text)
    for pattern, repl in _SECRET_PATTERNS:
        s = pattern.sub(repl, s)
    return s


class SecretRedactingFilter(logging.Filter):
    """Última linha de defesa: redige ``msg`` e ``exc_text`` antes do formatador."""

    def filter(self, record: logging.LogRecord) -> bool:
        # Materializa a mensagem final uma vez; limpa args para o Formatter não
        # re-interpolar (httpx, pinned_store, etc.).
        try:
            record.msg = record.getMessage()
        except Exception:
            record.msg = str(record.msg)
        record.args = ()
        record.msg = redact_secrets(str(record.msg))
        if record.exc_text:
            record.exc_text = redact_secrets(record.exc_text)
        return True


def _truncate(s: str, n: int) -> str:
    s = str(s)
    if len(s) <= n:
        return s
    return s[: n - 3] + "..."


def _sanitize_metadata(meta: Mapping[str, Any] | None) -> dict[str, Any]:
    if not meta:
        return {}
    out: dict[str, Any] = {}
    for k, v in meta.items():
        if k == "query" and isinstance(v, str):
            out[k] = _truncate(redact_secrets(v), _MAX_QUERY_META)
        elif isinstance(v, str):
            out[k] = redact_secrets(v)
        elif k == "debug" and isinstance(v, dict):
            keys = list(v.keys())[:18]
            out[k] = {
                kk: redact_secrets(v[kk]) if isinstance(v[kk], str) else v[kk]
                for kk in keys
            }
            if len(v) > len(keys):
                out[k]["_truncated"] = len(v) - len(keys)
        elif isinstance(v, (list, tuple)) and len(v) > _MAX_LIST_META:
            out[k] = list(v[:_MAX_LIST_META]) + [f"...(+{len(v) - _MAX_LIST_META})"]
        else:
            out[k] = v
    return out


def log_event(
    logger: logging.Logger,
    level: int,
    module: str,
    event: str,
    message: str,
    metadata: Mapping[str, Any] | None = None,
    *,
    exc_info: bool = False,
) -> None:
    """Um evento ACL = um registo com payload em ``extra`` (Formatter consome)."""
    safe_message = redact_secrets(message)
    payload = {
        "module": module,
        "event": event,
        "message": safe_message,
        "metadata": _sanitize_metadata(dict(metadata) if metadata else None),
    }
    logger.log(level, safe_message, extra={ACL_EXTRA: payload}, exc_info=exc_info)


class AclLogFormatter(logging.Formatter):
    """Se o record tiver ``acl_payload``, formata JSON ou linha compacta; senão legado."""

    def __init__(self, json_mode: bool, datefmt: str | None = None) -> None:
        super().__init__(
            fmt="%(asctime)s %(levelname)s [%(name)s] %(message)s",
            datefmt=datefmt or "%H:%M:%S",
        )
        self._json_mode = json_mode

    def _append_traceback(self, record: logging.LogRecord, base: str) -> str:
        if record.exc_info:
            exc_text = self.formatException(record.exc_info)
            return f"{base}\n{redact_secrets(exc_text)}"
        if record.exc_text:
            return f"{base}\n{redact_secrets(record.exc_text)}"
        return base

    def format(self, record: logging.LogRecord) -> str:
        pl = getattr(record, ACL_EXTRA, None)
        if isinstance(pl, dict):
            ts = _dt.datetime.fromtimestamp(
                record.created, tz=_dt.timezone.utc
            ).isoformat(timespec="milliseconds")
            if self._json_mode:
                line: dict[str, Any] = {
                    "timestamp": ts,
                    "level": record.levelname,
                    "module": pl["module"],
                    "event": pl["event"],
                    "message": pl["message"],
                    "metadata": pl.get("metadata") or {},
                }
                if record.exc_info:
                    line["traceback"] = redact_secrets(
                        self.formatException(record.exc_info)
                    )
                return json.dumps(line, ensure_ascii=False, default=str)
            meta = pl.get("metadata") or {}
            parts = [f"{k}={v!r}" for k, v in list(meta.items())[:14]]
            tail = " ".join(parts)
            base = (
                f"{ts}  {record.levelname:7}  [{pl['module']}]  {pl['event']}  |  {pl['message']}"
                + (f"  |  {tail}" if tail else "")
            )
            return self._append_traceback(record, base)
        formatted = super().format(record)
        return redact_secrets(formatted)
