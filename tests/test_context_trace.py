"""Observabilidade das camadas de contexto: eventos TEMPORAL_CONTEXT /
CALENDAR_LOOKUP e secção `context` no snapshot do trace (painel)."""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from api.rate_limit import reset_for_tests
from app.factory import create_app
from app.state import AppServices
from kernel.inspect.recorder import reset_recorder_for_tests
from kernel.memory.pinned_store import PinnedSessionStore
from kernel.memory.transcript_store import TranscriptStore
from kernel.orchestrator.context import BuildMessagesResult, ContextTrace
from kernel.trace import get_trace_store, reset_trace_bus_for_tests

TOKEN = "test-context-trace-token"

_TEMPORAL = {
    "date": "2026-08-08",
    "time": "20:30",
    "weekday": "sábado",
    "timezone": "America/Sao_Paulo",
    "timestamp": "2026-08-08T20:30:00-03:00",
}

_CALENDAR = {
    "events_used": [
        {
            "id": "event-001",
            "title": "AT Banco de Dados",
            "type": "assessment",
            "discipline": "Banco de Dados",
            "date": "2026-09-15",
            "time": None,
            "days_delta": 38,
            "source": "official",
        }
    ],
    "events_used_count": 1,
}


@pytest.fixture(autouse=True)
def _iso():
    reset_for_tests()
    reset_recorder_for_tests()
    reset_trace_bus_for_tests()
    yield
    reset_for_tests()
    reset_recorder_for_tests()
    reset_trace_bus_for_tests()


@dataclass
class SettingsStub:
    transcript_max_turns: int = 16
    reload_bearer_token: str | None = TOKEN
    project_root: Path = Path(".").resolve()
    trace_db_path: Path | None = None


class ContextManagerStub:
    def __init__(self, settings: SettingsStub):
        self.settings = settings

    def build_messages(self, message, discipline_filter=None, session_id=None, conversation_history=None, **_kwargs):
        trace = ContextTrace(
            label="Base geral",
            sources=("db:doc/x",),
            confidence="high",
            decision="answer",
            reason="ok",
            temporal_context=dict(_TEMPORAL),
            calendar_context=dict(_CALENDAR),
            temporal_intent="calendar_fact",
            rag_skipped=False,
            institutional_files=("faculty.md",),
            identity_active=True,
        )
        return BuildMessagesResult(
            messages=[
                {"role": "system", "content": "system"},
                {"role": "user", "content": message},
            ],
            trace=trace,
            decision=None,
        )


class ChatProviderStub:
    async def stream_response(self, *_args, **_kwargs):
        yield 'data: [ACL_META]{"confidence":"high","sources":["db:doc/x"],"label":"Base geral"}\n\n'
        yield "data: Faltam 38 dias\n\n"
        yield "data: [DONE]\n\n"


def _app(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("ACL_INTERNAL_BEARER_TOKEN", TOKEN)
    monkeypatch.setenv("ACL_TRACE_DB_PATH", str(tmp_path / "traces.sqlite3"))
    monkeypatch.delenv("KERNELBOT_ENV", raising=False)
    monkeypatch.delenv("ACL_REQUIRE_API_AUTH", raising=False)
    settings = SettingsStub(trace_db_path=tmp_path / "traces.sqlite3")
    services = AppServices(
        search_engine=SimpleNamespace(stats=lambda: {}),
        context_manager=ContextManagerStub(settings),
        chat_provider=ChatProviderStub(),
        pinned_store=PinnedSessionStore(),
        transcript_store=TranscriptStore(),
    )
    return create_app(services)


def _wait_for_stage(trace_id: str, stage: str, timeout: float = 2.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        store = get_trace_store()
        if store is not None:
            events = store.get_events(trace_id)
            if any(e.stage == stage for e in events):
                return events
        time.sleep(0.05)
    store = get_trace_store()
    return store.get_events(trace_id) if store else []


def test_context_layers_emit_trace_events_and_snapshot(tmp_path, monkeypatch):
    app = _app(tmp_path, monkeypatch)
    tid = "99999999-8888-7777-6666-555555555555"
    with TestClient(app) as client:
        r = client.post(
            "/v1/chat",
            headers={"X-Trace-Id": tid},
            json={
                "context": {"platform": "whatsapp", "user_id": "u1", "channel_id": "c1"},
                "message": "quantos dias faltam para a AT?",
            },
        )
        assert r.status_code == 200

        events = _wait_for_stage(tid, "RESPONSE_RETURNED")
        by_stage = {e.stage: e for e in events}

        assert "TEMPORAL_CONTEXT" in by_stage
        temporal = by_stage["TEMPORAL_CONTEXT"].data
        assert temporal["date"] == "2026-08-08"
        assert temporal["timezone"] == "America/Sao_Paulo"
        assert temporal["intent"] == "calendar_fact"
        assert temporal["rag_skipped"] is False

        assert "CALENDAR_LOOKUP" in by_stage
        calendar = by_stage["CALENDAR_LOOKUP"].data
        assert calendar["events_used_count"] == 1
        assert calendar["events_used"][0]["title"] == "AT Banco de Dados"
        assert calendar["events_used"][0]["days_delta"] == 38

        store = get_trace_store()
        snapshot = store.get_snapshot(tid)
        context = snapshot["prompt"]["context"]
        assert context["identity_active"] is True
        assert context["institutional_files"] == ["faculty.md"]
        assert context["temporal"]["date"] == "2026-08-08"
        assert context["calendar_events_used"][0]["id"] == "event-001"
        assert context["rag_sources_used"] == ["db:doc/x"]

        # Painel: secção "Contexto (camadas)" renderiza o snapshot.
        login = client.post(
            "/traces/login", data={"token": TOKEN}, follow_redirects=False
        )
        detail = client.get(f"/traces/{tid}", cookies=login.cookies)
        assert detail.status_code == 200
        assert "Contexto (camadas)" in detail.text
        assert "AT Banco de Dados" in detail.text
        assert "America/Sao_Paulo" in detail.text
