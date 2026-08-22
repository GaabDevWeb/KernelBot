"""Testes do CalendarProvider — matemática temporal no backend."""

from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path

from kernel.context.calendar_provider import ASSESSMENT_TYPES, CalendarProvider
from kernel.context.temporal import TemporalContextProvider

# Hoje fixo: sexta-feira 2026-08-08 (20:30 em America/Sao_Paulo).
_FIXED_UTC = datetime(2026, 8, 8, 23, 30, 0, tzinfo=timezone.utc)
_TODAY = date(2026, 8, 8)


def _temporal():
    return TemporalContextProvider("America/Sao_Paulo", clock=lambda: _FIXED_UTC).now()


def _write_calendar(tmp_path: Path, events: list[dict]) -> Path:
    path = tmp_path / "calendar.json"
    path.write_text(json.dumps({"events": events}), encoding="utf-8")
    return path


_EVENTS = [
    {
        "id": "event-001",
        "title": "AT Banco de Dados",
        "type": "assessment",
        "discipline": "Banco de Dados",
        "date": "2026-09-15",
    },
    {
        "id": "event-002",
        "title": "Entrega trabalho Python",
        "type": "delivery",
        "discipline": "Python",
        "date": "2026-08-09",
        "time": "19:00",
    },
    {
        "id": "event-003",
        "title": "Seminário de Visualização",
        "type": "seminar",
        "discipline": "Visualização SQL",
        "date": "2026-08-07",
    },
]


def test_next_event_and_ordering(tmp_path):
    provider = CalendarProvider(_write_calendar(tmp_path, _EVENTS))
    nxt = provider.next_event(_TODAY)
    assert nxt is not None and nxt.id == "event-002"  # amanhã antes do AT


def test_next_assessment_filters_types(tmp_path):
    provider = CalendarProvider(_write_calendar(tmp_path, _EVENTS))
    nxt = provider.next_assessment(_TODAY)
    assert nxt is not None and nxt.title == "AT Banco de Dados"
    assert nxt.type in ASSESSMENT_TYPES


def test_days_until_computed_by_backend(tmp_path):
    provider = CalendarProvider(_write_calendar(tmp_path, _EVENTS))
    at = provider.next_assessment(_TODAY)
    assert CalendarProvider.days_until(at, _TODAY) == 38


def test_discipline_filter_is_case_insensitive_and_partial(tmp_path):
    provider = CalendarProvider(_write_calendar(tmp_path, _EVENTS))
    events = provider.events_for_discipline("banco de dados")
    assert [e.id for e in events] == ["event-001"]


def test_events_between_covers_this_week(tmp_path):
    provider = CalendarProvider(_write_calendar(tmp_path, _EVENTS))
    week = provider.events_between(date(2026, 8, 8), date(2026, 8, 14))
    assert [e.id for e in week] == ["event-002"]


def test_prompt_block_contains_computed_deltas(tmp_path):
    provider = CalendarProvider(_write_calendar(tmp_path, _EVENTS))
    block, used = provider.build_prompt_block(_temporal())
    assert "AT Banco de Dados" in block
    assert "faltam 38 dias" in block          # calculado pelo servidor
    assert "é AMANHÃ" in block                # entrega de 2026-08-09
    assert "foi ONTEM" in block               # seminário de 2026-08-07
    assert "NÃO invente" in block             # política anti-invenção
    assert "agenda oficial tem prioridade" in block  # política de conflito
    assert {e.id for e in used} == {"event-001", "event-002", "event-003"}


def test_prompt_block_declares_absence_when_empty(tmp_path):
    provider = CalendarProvider(_write_calendar(tmp_path, []))
    block, used = provider.build_prompt_block(_temporal())
    assert "Não há eventos acadêmicos registados" in block
    assert "NÃO invente" in block
    assert used == ()


def test_missing_file_behaves_as_empty(tmp_path):
    provider = CalendarProvider(tmp_path / "nao-existe.json")
    assert provider.events == ()
    block, _ = provider.build_prompt_block(_temporal())
    assert "Não há eventos acadêmicos registados" in block


def test_invalid_events_are_skipped(tmp_path):
    events = [
        {"title": "Sem data"},
        {"title": "Data inválida", "date": "15/09/2026"},
        "não é objeto",
        {"title": "Válido", "date": "2026-10-01"},
    ]
    provider = CalendarProvider(_write_calendar(tmp_path, events))
    assert [e.title for e in provider.events] == ["Válido"]


def test_reload_when_file_changes(tmp_path):
    path = _write_calendar(tmp_path, [])
    provider = CalendarProvider(path)
    assert provider.events == ()
    import os

    _write_calendar(tmp_path, _EVENTS)
    os.utime(path, (0, 9_999_999_999))  # força mtime diferente
    assert len(provider.events) == 3
