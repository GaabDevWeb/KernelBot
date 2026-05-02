"""Logging estruturado (JSON ou texto) para auditoria e debugging do ACL.

Campos estáveis em ``metadata`` (snake_case):
  query, top_score, second_score, score_margin, decision, reason, confidence,
  mode, discipline_filter, informative_terms, coverage, coverage_weighted,
  candidate_count, selected_sources, llm_called, tokens_used, model, ...

Variável de ambiente: ACL_LOG_FORMAT=json | text (default: text).
"""

from __future__ import annotations

import datetime as _dt
import json
import logging
import os
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
            out[k] = _truncate(v, _MAX_QUERY_META)
        elif k == "debug" and isinstance(v, dict):
            keys = list(v.keys())[:18]
            out[k] = {kk: v[kk] for kk in keys}
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
) -> None:
    """Um evento ACL = um registo com payload em ``extra`` (Formatter consome)."""
    payload = {
        "module": module,
        "event": event,
        "message": message,
        "metadata": _sanitize_metadata(dict(metadata) if metadata else None),
    }
    logger.log(level, message, extra={ACL_EXTRA: payload})


class AclLogFormatter(logging.Formatter):
    """Se o record tiver ``acl_payload``, formata JSON ou linha compacta; senão legado."""

    def __init__(self, json_mode: bool, datefmt: str | None = None) -> None:
        super().__init__(
            fmt="%(asctime)s %(levelname)s [%(name)s] %(message)s",
            datefmt=datefmt or "%H:%M:%S",
        )
        self._json_mode = json_mode

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
                return json.dumps(line, ensure_ascii=False, default=str)
            meta = pl.get("metadata") or {}
            parts = [f"{k}={v!r}" for k, v in list(meta.items())[:14]]
            tail = " ".join(parts)
            return (
                f"{ts}  {record.levelname:7}  [{pl['module']}]  {pl['event']}  |  {pl['message']}"
                + (f"  |  {tail}" if tail else "")
            )
        return super().format(record)
