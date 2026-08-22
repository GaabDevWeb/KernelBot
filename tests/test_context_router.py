"""Golden + hard gates do ContextRouter (optimization/routing.md)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from kernel.config import Settings
from kernel.context.builder import ContextBuilder
from kernel.context.calendar_provider import CalendarProvider
from kernel.context.institutional import InstitutionalContextProvider, SECTION_FILES
from kernel.context.intent import detect_temporal_intent
from kernel.context.router import ContextRouter
from kernel.context.temporal import TemporalContextProvider
from kernel.context.types import ContextProfile, RagSkipReason, RouteSignals
from kernel.orchestrator.context import ContextManager

_FIXED_UTC = datetime(2026, 8, 8, 23, 30, 0, tzinfo=timezone.utc)


class SearchEngineStub:
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
    monkeypatch.delenv("ACL_CONTEXT_ROUTER", raising=False)
    return Settings.load()


@pytest.fixture()
def router_settings(monkeypatch) -> Settings:
    monkeypatch.setenv("ACL_LLM_PROVIDER", "openrouter")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setenv("ACL_CONTEXT_ROUTER", "1")
    monkeypatch.delenv("KERNELBOT_ENV", raising=False)
    return Settings.load()


def _signals(query: str, **kwargs) -> RouteSignals:
    defaults = {
        "temporal_intent": detect_temporal_intent(query),
        "history_turns": 0,
        "chat_history_max_turns": 12,
    }
    defaults.update(kwargs)
    return RouteSignals(**defaults)


def _many_events(n_future: int = 20, n_past: int = 10) -> list[dict]:
    events: list[dict] = []
    # Passados relativos a 2026-08-08
    for i in range(n_past):
        day = 1 + (i % 7)
        events.append(
            {
                "id": f"past-{i}",
                "title": f"Evento passado {i}",
                "type": "class",
                "discipline": "Geral",
                "date": f"2026-08-{day:02d}",
            }
        )
    # Futuros
    for i in range(n_future):
        month = 9 if i < 15 else 10
        day = 1 + (i % 28)
        events.append(
            {
                "id": f"future-{i}",
                "title": f"Evento futuro {i}",
                "type": "assessment",
                "discipline": "Geral",
                "date": f"2026-{month:02d}-{day:02d}",
            }
        )
    return events


def _builder(tmp_path: Path, *, events: list[dict] | None = None) -> ContextBuilder:
    ctx = tmp_path / "ctx"
    ctx.mkdir(exist_ok=True)
    for name, _title in SECTION_FILES:
        (ctx / name).write_text(f"conteudo de {name}", encoding="utf-8")
    calendar_path = tmp_path / "calendar.json"
    calendar_path.write_text(
        json.dumps({"events": events if events is not None else _many_events()}),
        encoding="utf-8",
    )
    return ContextBuilder(
        identity_prompt="## Identidade\n\nPrioridade de fontes.",
        institutional=InstitutionalContextProvider(ctx),
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


# --- Router puro (golden) ----------------------------------------------------


@pytest.mark.parametrize(
    "query,profile,rag_skipped,reason_substr",
    [
        ("que horas são chefe?", ContextProfile.FAST, True, "time_fact"),
        ("Que dia é hoje?", ContextProfile.FAST, True, "time_fact"),
        ("oi", ContextProfile.FAST, True, "greeting_ack"),
        ("obrigado", ContextProfile.FAST, True, "greeting_ack"),
        ("Quando é a próxima prova?", ContextProfile.NORMAL, True, "calendar_fact"),
        (
            "explica o TP de projeto de bloco com base nos materiais",
            ContextProfile.DEEP,
            False,
            "deep_markers",
        ),
        ("o que é list comprehension?", ContextProfile.NORMAL, False, "default_academic"),
    ],
)
def test_router_golden_profiles(query, profile, rag_skipped, reason_substr):
    route = ContextRouter().route(query, signals=_signals(query))
    assert route.profile is profile
    assert route.rag_skipped is rag_skipped
    assert reason_substr in route.reasons
    if profile is ContextProfile.FAST:
        assert route.include_calendar is False
        assert route.institutional_files == ()
        assert route.calendar_budgets.max_events == 0
        assert route.max_rag_sources == 0


def test_router_force_rag_not_fast():
    query = "que horas são?"
    route = ContextRouter().route(
        query, signals=_signals(query, force_rag=True)
    )
    assert route.profile is not ContextProfile.FAST
    assert route.profile is ContextProfile.DEEP
    assert route.rag_skipped is False


def test_router_calendar_only_skip_reason():
    query = "Quando é a próxima prova?"
    route = ContextRouter().route(query, signals=_signals(query))
    assert route.rag_skip_reason is RagSkipReason.CALENDAR_ONLY
    assert route.include_calendar is True
    assert route.calendar_budgets.max_events == 6
    assert route.calendar_budgets.max_past_events == 4


def test_router_deixis_followup_raises_transcript():
    query = "e o AT?"
    route = ContextRouter().route(
        query, signals=_signals(query, history_turns=4)
    )
    assert route.profile is ContextProfile.NORMAL
    assert route.transcript_max_turns >= 2
    assert "deixis_followup" in route.reasons


# --- Hard gates com ACL_CONTEXT_ROUTER=1 -------------------------------------


def test_hard_gate_time_fact_no_institutional_or_calendar(router_settings, tmp_path):
    assert router_settings.context_router_enabled is True
    cm, engine = _manager(router_settings, tmp_path)
    result = cm.build_messages("que horas são chefe?", session_id=None)
    assert result.trace.context_profile == "FAST"
    assert result.trace.rag_skipped is True
    assert result.trace.rag_skip_reason == "temporal_fact"
    assert result.trace.institutional_files == ()
    assert result.trace.include_institutional is False
    assert result.trace.include_calendar is False
    assert result.trace.calendar_context is None
    system = result.messages[0]["content"]
    assert "## Contexto institucional" not in system
    assert "## Agenda acadêmica" not in system
    assert engine.calls == []


def test_hard_gate_greeting_fast_rag_skip(router_settings, tmp_path):
    cm, engine = _manager(router_settings, tmp_path)
    result = cm.build_messages("oi", session_id=None)
    assert result.trace.context_profile == "FAST"
    assert result.trace.rag_skipped is True
    assert result.trace.rag_skip_reason == "greeting_ack"
    assert engine.calls == []


def test_hard_gate_calendar_fact_caps(router_settings, tmp_path):
    cm, engine = _manager(router_settings, tmp_path)
    result = cm.build_messages("Quando é a próxima prova?", session_id=None)
    assert result.trace.context_profile == "NORMAL"
    assert result.trace.include_calendar is True
    assert result.trace.rag_skipped is True
    assert result.trace.rag_skip_reason == "calendar_only"
    events = result.trace.calendar_context["events_used"]
    future = [e for e in events if (e.get("days_delta") or 0) >= 0]
    past = [e for e in events if (e.get("days_delta") or 0) < 0]
    assert len(future) <= 6
    assert len(past) <= 4
    assert len(events) <= 10
    assert engine.calls == []


def test_hard_gate_force_rag_not_fast(router_settings, tmp_path):
    cm, engine = _manager(router_settings, tmp_path)
    result = cm.build_messages("/content que horas são?", session_id=None)
    assert result.trace.context_profile != "FAST"
    assert result.trace.context_profile == "DEEP"
    assert result.trace.rag_skipped is False
    assert len(engine.calls) == 1


def test_flag_off_preserves_legacy_layers(settings, tmp_path):
    assert settings.context_router_enabled is False
    cm, _ = _manager(settings, tmp_path)
    result = cm.build_messages("Que dia é hoje?", session_id=None)
    assert result.trace.router_enabled is False
    assert result.trace.context_profile is None
    system = result.messages[0]["content"]
    # Legado: institutional + calendar always-on
    assert "## Contexto institucional" in system
    assert "## Agenda acadêmica" in system
    assert result.trace.rag_skipped is True
    assert len(result.trace.institutional_files) == len(SECTION_FILES)


def test_build_layers_without_route_is_legacy(tmp_path):
    layers = _builder(tmp_path).build_layers()
    assert layers.institutional_files
    assert layers.calendar_events_used
    assert layers.institutional_block
    assert layers.calendar_block


def test_build_layers_with_fast_route_omits_heavy_layers(tmp_path):
    from kernel.context.types import CalendarBudgets, ContextRoute

    route = ContextRoute(
        profile=ContextProfile.FAST,
        include_institutional=False,
        institutional_files=(),
        include_calendar=False,
        calendar_budgets=CalendarBudgets(0, 0),
        rag_skipped=True,
        rag_skip_reason=RagSkipReason.TEMPORAL_FACT,
    )
    layers = _builder(tmp_path).build_layers(route=route)
    assert layers.institutional_files == ()
    assert layers.institutional_block == ""
    assert layers.calendar_events_used == ()
    assert layers.calendar_block == ""
    assert layers.temporal_block


def test_institutional_prompt_block_allowlist(tmp_path):
    ctx = tmp_path / "ctx"
    ctx.mkdir()
    (ctx / "professors.md").write_text("Prof X", encoding="utf-8")
    (ctx / "rules.md").write_text("Regra Y", encoding="utf-8")
    provider = InstitutionalContextProvider(ctx)
    block, files = provider.prompt_block(files=("professors.md",))
    assert files == ("professors.md",)
    assert "Prof X" in block
    assert "Regra Y" not in block
    empty_block, empty_files = provider.prompt_block(files=())
    assert empty_block == "" and empty_files == ()


def test_router_time_fact_with_policy_not_fast():
    """SEC-001: substring time_fact + política → NORMAL + rules.md."""
    query = "que dia e hoje e qual a politica de faltas?"
    route = ContextRouter().route(query, signals=_signals(query))
    assert route.profile is ContextProfile.NORMAL
    assert "rules.md" in route.institutional_files
    assert route.rag_skipped is False


def test_router_policy_faltar_injects_rules():
    """SEC-002: morfologia faltar → rules.md."""
    query = "posso faltar amanha?"
    route = ContextRouter().route(query, signals=_signals(query))
    assert "rules.md" in route.institutional_files
    assert route.include_institutional is True


def test_router_calendar_plus_policy_no_calendar_only_skip():
    """SEC-002: calendário + política não skipa RAG por calendar_only."""
    query = "quando e a proxima prova e posso faltar?"
    route = ContextRouter().route(query, signals=_signals(query))
    assert route.rag_skip_reason is not RagSkipReason.CALENDAR_ONLY
    assert route.rag_skipped is False
    assert "rules.md" in route.institutional_files
