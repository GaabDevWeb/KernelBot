"""SSOT de disciplinas de aula — comandos, labels e markers de pin."""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

_DISCIPLINES_JSON = Path(__file__).resolve().parent / "disciplines.json"


@dataclass(frozen=True)
class DisciplineConfig:
    id: str
    label: str
    command: str
    menu_short: str
    silo_class: str
    menu_description: str
    query_markers: tuple[str, ...]


def _parse_discipline(raw: dict[str, Any]) -> DisciplineConfig:
    markers = raw.get("queryMarkers") or []
    return DisciplineConfig(
        id=str(raw["id"]).strip(),
        label=str(raw["label"]).strip(),
        command=str(raw["command"]).strip(),
        menu_short=str(raw.get("menuShort") or raw["command"]).strip(),
        silo_class=str(raw.get("siloClass") or raw["id"]).strip(),
        menu_description=str(raw.get("menuDescription") or raw["label"]).strip(),
        query_markers=tuple(str(m) for m in markers),
    )


@lru_cache(maxsize=1)
def load_disciplines() -> tuple[DisciplineConfig, ...]:
    data = json.loads(_DISCIPLINES_JSON.read_text(encoding="utf-8"))
    items = [_parse_discipline(row) for row in data.get("disciplines", [])]
    # Mais longo primeiro — mesma regra que context.py (evita `/python` antes de `/python-processamento-dados`).
    items.sort(key=lambda d: len(d.command), reverse=True)
    return tuple(items)


def command_prefixes() -> tuple[tuple[str, str], ...]:
    return tuple((d.command, d.id) for d in load_disciplines())


def trace_label_by_discipline() -> dict[str, str]:
    labels = {d.id: d.label for d in load_disciplines()}
    labels["doc"] = "Documentação (doc)"
    labels["geral"] = "Base geral"
    return labels


def query_markers_by_discipline() -> dict[str, tuple[str, ...]]:
    return {d.id: d.query_markers for d in load_disciplines()}


def discipline_by_id(discipline_id: str) -> DisciplineConfig | None:
    key = discipline_id.strip().lower()
    for d in load_disciplines():
        if d.id == key:
            return d
    return None
