"""Validadores partilhados de payloads HTTP."""

from __future__ import annotations

import json
from typing import Any

from pydantic import field_validator

_MAX_METADATA_BYTES = 4096
_MAX_METADATA_DEPTH = 2
_MAX_METADATA_KEYS = 32


def _depth(value: Any, current: int = 0) -> int:
    if current > _MAX_METADATA_DEPTH:
        return current
    if isinstance(value, dict):
        if not value:
            return current
        return max(_depth(v, current + 1) for v in value.values())
    if isinstance(value, list):
        if not value:
            return current
        return max(_depth(v, current + 1) for v in value)
    return current


def validate_metadata(value: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("metadata deve ser um objecto")
    if len(value) > _MAX_METADATA_KEYS:
        raise ValueError(f"metadata: máximo {_MAX_METADATA_KEYS} chaves")
    if _depth(value) > _MAX_METADATA_DEPTH:
        raise ValueError(f"metadata: profundidade máxima {_MAX_METADATA_DEPTH}")
    try:
        encoded = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    except (TypeError, ValueError) as exc:
        raise ValueError("metadata não é serializável em JSON") from exc
    if len(encoded.encode("utf-8")) > _MAX_METADATA_BYTES:
        raise ValueError(f"metadata: máximo {_MAX_METADATA_BYTES} bytes JSON")
    return value


def strip_and_require(value: str | None) -> str | None:
    """Normaliza campo textual opcional: remove NUL/whitespace, rejeita vazio pós-strip.

    Preserva ``None`` (campo ausente é válido nos schemas que a usam); só o
    valor vazio *após* limpeza é rejeitado — mesma semântica das validações
    ``strip_strings`` historicamente duplicadas em ``ChatRequest``/``SearchRequest``.
    """
    if value is None:
        return None
    value = value.replace("\x00", "").strip()
    if not value:
        raise ValueError("campo não pode ser vazio")
    return value


def validate_session_id(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None
    # Evita session_id = user_id numérico previsível
    if value.isdigit():
        raise ValueError("session_id não pode ser apenas dígitos; use UUID opaco")
    return value


def metadata_field_validator():
    return field_validator("metadata", mode="after")(classmethod(lambda cls, v: validate_metadata(v)))
