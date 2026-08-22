"""Testes do ContextBuilder e da integração com o ContextManager real.

Cobrem os cenários obrigatórios da arquitetura de contexto em camadas:
tempo, datas, eventos, transcript+tempo, ausência e conflito de fontes.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from kernel.config import Settings
from kernel.context.builder import ContextBuilder, SystemContextBlocks
from kernel.context.calendar_provider import CalendarProvider
from kernel.context.institutional import InstitutionalContextProvider
from kernel.context.temporal import TemporalContextProvider
from kernel.orchestrator.context import ContextManager

# Sexta 2026-08-08 20:30 em America/Sao_Paulo.
_FIXED_UTC = datetime(2026, 8, 8, 23, 30, 0, tzinfo=timezone.utc)

_EVENTS = [
    {
        "id": "event-001",
        "title": "AT Banco de Dados",
        "type": "assessment",
        "discipline": "Banco de Dados",
        "date": "2026-09-15",
    },
]


class SearchEngineStub:
    """Regista chamadas BM25; devolve sempre zero candidatos."""

    def __init__(self) -> None:
        self.chunks: list = []
        self.calls: list[str] = []

    def search_candidates(self, query, candidate_k=8, discipline_filter=None):
        self.calls.append(query)
        return []

    def normalize_discipline(self, raw):
        return str(raw) if raw else None


@pytest.fixture()
def settings(monkeypatch) -> Settings:
    monkeypatch.setenv("ACL_LLM_PROVIDER", "openrouter")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.delenv("KERNELBOT_ENV", raising=False)
    monkeypatch.delenv("KERNEL_TIMEZONE", raising=False)
    return Settings.load()


def _builder(tmp_path: Path, *, with_calendar: bool = True) -> ContextBuilder:
    calendar_path = tmp_path / "calendar.json"
    calendar_path.write_text(
        json.dumps({"events": _EVENTS if with_calendar else []}), encoding="utf-8"
    )
    return ContextBuilder(
        identity_prompt="## Identidade operacional\n\nPrioridade de fontes (maior → menor).",
        institutional=InstitutionalContextProvider(tmp_path / "ctx"),
        temporal=TemporalContextProvider(
            "America/Sao_Paulo", clock=lambda: _FIXED_UTC
        ),
        calendar=CalendarProvider(calendar_path),
    )


def _manager(settings: Settings, tmp_path: Path, **kwargs) -> tuple[ContextManager, SearchEngineStub]:
    engine = SearchEngineStub()
    cm = ContextManager(
        settings,
        engine,  # type: ignore[arg-type]
        context_builder=_builder(tmp_path, **kwargs),
    )
    return cm, engine


def _system_content(result) -> str:
    assert result.messages[0]["role"] == "system"
    return result.messages[0]["content"]


# --- Ordem de montagem -------------------------------------------------------


def test_assemble_order_is_canonical():
    content = ContextBuilder.assemble_system_content(
        SystemContextBlocks(
            base_prompt="[BASE]",
            identity="[IDENTITY]",
            institutional="[INSTITUTIONAL]",
            temporal="[TEMPORAL]",
            calendar="[CALENDAR]",
            catalog_router="[ROUTER]",
            catalog_section="[CATALOG]",
            sticky="[STICKY]",
            grounding="[GROUNDING]",
            chunk_context="[CHUNKS]",
        )
    )
    order = [
        "[BASE]", "[IDENTITY]", "[INSTITUTIONAL]", "[TEMPORAL]", "[CALENDAR]",
        "[ROUTER]", "[CATALOG]", "[STICKY]", "[GROUNDING]", "[CHUNKS]",
    ]
    positions = [content.index(m) for m in order]
    assert positions == sorted(positions)


def test_assemble_skips_empty_blocks():
    content = ContextBuilder.assemble_system_content(
        SystemContextBlocks(base_prompt="[BASE]", grounding="[GROUNDING]")
    )
    assert content == "[BASE]\n\n[GROUNDING]"


# --- Tempo: "que dia é hoje?" / "que horas são?" -----------------------------


def test_time_fact_answers_from_server_and_skips_rag(settings, tmp_path):
    cm, engine = _manager(settings, tmp_path)
    result = cm.build_messages("Que dia é hoje?", session_id=None)
    system = _system_content(result)
    assert "2026-08-08" in system
    assert "sábado, 8 de agosto de 2026" in system
    assert "20:30" in system
    assert "America/Sao_Paulo" in system
    assert engine.calls == []                      # RAG dispensado
    assert result.trace.rag_skipped is True
    assert result.trace.temporal_intent == "time_fact"
    assert result.trace.reason == "temporal_fact"
    assert result.trace.temporal_context["date"] == "2026-08-08"


def test_time_fact_clock_question_also_skips_rag(settings, tmp_path):
    cm, engine = _manager(settings, tmp_path)
    result = cm.build_messages("que horas são?", session_id=None)
    assert engine.calls == []
    assert result.trace.rag_skipped is True


# --- Datas/eventos: "quantos dias faltam?" (backend calcula) -----------------


def test_calendar_fact_injects_computed_days_and_keeps_rag(settings, tmp_path):
    cm, engine = _manager(settings, tmp_path)
    result = cm.build_messages(
        "Quantos dias faltam para a AT de Banco de Dados?", session_id=None
    )
    system = _system_content(result)
    assert "AT Banco de Dados" in system
    assert "faltam 38 dias" in system              # 2026-08-08 → 2026-09-15
    assert len(engine.calls) == 1                  # híbrido: RAG continua ativo
    assert result.trace.rag_skipped is False
    assert result.trace.temporal_intent == "calendar_fact"
    events = result.trace.calendar_context["events_used"]
    assert events[0]["id"] == "event-001" and events[0]["days_delta"] == 38


# --- Transcript + tempo (contexto híbrido) -----------------------------------


def test_transcript_plus_time_both_reach_the_prompt(settings, tmp_path):
    cm, _ = _manager(settings, tmp_path)
    history = [
        {"role": "user", "content": "o professor falou que a prova é semana que vem"},
        {"role": "assistant", "content": "anotado!"},
    ]
    result = cm.build_messages(
        "quantos dias faltam?", session_id=None, conversation_history=history
    )
    system = _system_content(result)
    assert "## Contexto temporal" in system
    contents = [m["content"] for m in result.messages]
    assert "o professor falou que a prova é semana que vem" in contents


# --- Ausência: prova inexistente → não inventar ------------------------------


def test_absence_of_events_yields_honest_agenda_block(settings, tmp_path):
    cm, _ = _manager(settings, tmp_path, with_calendar=False)
    result = cm.build_messages("quando é a prova de Física?", session_id=None)
    system = _system_content(result)
    assert "Não há eventos acadêmicos registados" in system
    assert "NÃO invente" in system


# --- Conflito: transcript diz uma data, agenda oficial diz outra -------------


def test_conflict_official_calendar_has_priority_in_prompt(settings, tmp_path):
    cm, _ = _manager(settings, tmp_path)
    history = [
        {"role": "user", "content": "a AT de Banco de Dados é dia 2026-09-20, né?"},
    ]
    result = cm.build_messages(
        "quantos dias faltam para a AT?", session_id=None, conversation_history=history
    )
    system = _system_content(result)
    assert "2026-09-15" in system                          # data oficial presente
    assert "agenda oficial tem prioridade" in system       # política de conflito
    assert "Prioridade de fontes" in system                # identidade injetada
    contents = [m["content"] for m in result.messages]
    assert any("2026-09-20" in c for c in contents)        # transcript preservado


# --- Institucional ------------------------------------------------------------


def test_institutional_sections_enter_prompt_when_filled(settings, tmp_path):
    ctx_dir = tmp_path / "ctx"
    ctx_dir.mkdir()
    (ctx_dir / "faculty.md").write_text(
        "Nome: Faculdade Exemplo\nTurma: T-01", encoding="utf-8"
    )
    (ctx_dir / "rules.md").write_text(
        "<!-- só comentário: deve ser ignorado -->", encoding="utf-8"
    )
    cm, _ = _manager(settings, tmp_path)
    result = cm.build_messages("olá", session_id=None)
    system = _system_content(result)
    assert "Faculdade Exemplo" in system
    assert "só comentário" not in system
    assert result.trace.institutional_files == ("faculty.md",)


# --- Compatibilidade: sem builder, comportamento anterior ---------------------


def test_without_builder_no_new_layers_are_injected(settings):
    engine = SearchEngineStub()
    cm = ContextManager(settings, engine)  # type: ignore[arg-type]
    result = cm.build_messages("Que dia é hoje?", session_id=None)
    system = _system_content(result)
    assert "## Contexto temporal" not in system
    assert result.trace.rag_skipped is False
    assert result.trace.temporal_context is None
    assert len(engine.calls) == 1                  # RAG segue o fluxo normal
