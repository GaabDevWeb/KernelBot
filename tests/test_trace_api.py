"""Testes API TRACE: ingest + painel cookie + X-Trace-Id no /v1/chat."""

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

TOKEN = "test-trace-internal-token"


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
            label="Documentação",
            sources=("db:doc/x",),
            source_details=({"discipline": "doc"},),
            confidence="high",
            decision="answer",
            reason="ok",
        )
        return BuildMessagesResult(
            messages=[{"role": "user", "content": message}],
            trace=trace,
            decision=None,
        )


class ChatProviderStub:
    async def stream_response(self, *_args, **_kwargs):
        yield 'data: [ACL_META]{"confidence":"high","sources":["db:doc/x"],"label":"Documentação"}\n\n'
        yield "data: Resposta trace\n\n"
        yield "data: [DONE]\n\n"


def _wait_events(
    trace_id: str,
    min_count: int,
    timeout: float = 2.0,
    required_stage: str | None = None,
):
    """Espera eventos do bus assíncrono; com `required_stage`, espera até esse
    stage aparecer (evita corrida com eventos emitidos após a resposta HTTP)."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        store = get_trace_store()
        if store is not None:
            events = store.get_events(trace_id)
            if len(events) >= min_count and (
                required_stage is None
                or any(e.stage == required_stage for e in events)
            ):
                return events
        time.sleep(0.05)
    store = get_trace_store()
    return store.get_events(trace_id) if store else []


def _app(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("ACL_INTERNAL_BEARER_TOKEN", TOKEN)
    monkeypatch.setenv("ACL_TRACE_DB_PATH", str(tmp_path / "traces.sqlite3"))
    monkeypatch.delenv("KERNELBOT_ENV", raising=False)
    settings = SettingsStub(trace_db_path=tmp_path / "traces.sqlite3")
    cm = ContextManagerStub(settings)
    services = AppServices(
        search_engine=SimpleNamespace(stats=lambda: {}),
        context_manager=cm,
        chat_provider=ChatProviderStub(),
        pinned_store=PinnedSessionStore(),
        transcript_store=TranscriptStore(),
    )
    return create_app(services)


def test_ingest_and_list_detail(tmp_path, monkeypatch):
    app = _app(tmp_path, monkeypatch)
    tid = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    with TestClient(app) as client:
        r = client.post(
            "/internal/traces/events",
            headers={"Authorization": f"Bearer {TOKEN}"},
            json={
                "events": [
                    {
                        "trace_id": tid,
                        "service": "orbit",
                        "stage": "MESSAGE_RECEIVED",
                        "data": {"jid": "x"},
                    },
                    {
                        "trace_id": tid,
                        "service": "kernel",
                        "stage": "REQUEST_RECEIVED",
                        "data": {"ok": 1},
                    },
                ]
            },
        )
        assert r.status_code == 202
        assert r.json()["queued"] == 2

        events = _wait_events(tid, 2)
        assert len(events) >= 2

        login = client.post("/traces/login", data={"token": TOKEN}, follow_redirects=False)
        assert login.status_code == 303
        assert "trace_auth" in login.cookies

        listing = client.get("/traces", cookies=login.cookies)
        assert listing.status_code == 200
        assert tid in listing.text

        detail = client.get(f"/traces/{tid}", cookies=login.cookies)
        assert detail.status_code == 200
        assert "MESSAGE_RECEIVED" in detail.text
        assert "REQUEST_RECEIVED" in detail.text


def test_v1_chat_echoes_trace_id(tmp_path, monkeypatch):
    app = _app(tmp_path, monkeypatch)
    monkeypatch.delenv("ACL_REQUIRE_API_AUTH", raising=False)
    tid = "11111111-2222-3333-4444-555555555555"
    with TestClient(app) as client:
        r = client.post(
            "/v1/chat",
            headers={"X-Trace-Id": tid},
            json={
                "context": {"platform": "whatsapp", "user_id": "u1", "channel_id": "c1"},
                "message": "olá trace",
            },
        )
        assert r.status_code == 200
        body = r.json()
        assert body["metadata"]["trace_id"] == tid

        events = _wait_events(tid, 4, required_stage="RESPONSE_RETURNED")
        stages = {e.stage for e in events}
        assert "REQUEST_RECEIVED" in stages
        assert "RAG_STARTED" in stages
        assert "RESPONSE_RETURNED" in stages
