"""Testes Fatia B: filtros, métricas, ZIP, dashboard."""

from __future__ import annotations

import io
import time
import zipfile
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
from kernel.trace import emit_event, get_trace_store, reset_trace_bus_for_tests
from kernel.trace.export import build_trace_zip
from kernel.trace.store import TraceFilters, TraceStore

TOKEN = "test-trace-b-token"


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
        yield "data: Resposta B\n\n"
        yield "data: [DONE]\n\n"


def _wait(tid: str, n: int = 1, timeout: float = 2.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        store = get_trace_store()
        if store and len(store.get_events(tid)) >= n:
            return
        time.sleep(0.05)


def _app(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("ACL_INTERNAL_BEARER_TOKEN", TOKEN)
    monkeypatch.setenv("ACL_TRACE_DB_PATH", str(tmp_path / "traces.sqlite3"))
    monkeypatch.delenv("KERNELBOT_ENV", raising=False)
    settings = SettingsStub(trace_db_path=tmp_path / "traces.sqlite3")
    services = AppServices(
        search_engine=SimpleNamespace(stats=lambda: {}),
        context_manager=ContextManagerStub(settings),
        chat_provider=ChatProviderStub(),
        pinned_store=PinnedSessionStore(),
        transcript_store=TranscriptStore(),
    )
    return create_app(services)


def test_store_filters_and_metrics(tmp_path):
    store = TraceStore(tmp_path / "t.sqlite3")
    store.insert_event(
        trace_id="t-phone",
        timestamp="2026-07-28T10:00:00.000Z",
        service="orbit",
        stage="MESSAGE_RECEIVED",
        data={"jid": "5511999999999@s.whatsapp.net", "channel": "1:1"},
        priority=10,
    )
    store.insert_event(
        trace_id="t-phone",
        timestamp="2026-07-28T10:00:01.500Z",
        service="kernel",
        stage="RESPONSE_RETURNED",
        data={"answer_preview": "ola"},
        priority=10,
    )
    store.insert_event(
        trace_id="t-group",
        timestamp="2026-07-28T11:00:00.000Z",
        service="orbit",
        stage="MESSAGE_RECEIVED",
        data={"groupJid": "120363@g.us", "channel": "group", "authorJid": "a@s.whatsapp.net"},
        priority=10,
    )
    store.insert_event(
        trace_id="t-err",
        timestamp="2026-07-28T12:00:00.000Z",
        service="kernel",
        stage="ERROR",
        data={"error": "boom"},
        priority=0,
    )

    phone_hits = store.search_traces(TraceFilters(phone="5511999", limit=20))
    assert any(t.trace_id == "t-phone" for t in phone_hits)

    group_hits = store.search_traces(TraceFilters(group="120363@g.us", limit=20))
    assert any(t.trace_id == "t-group" for t in group_hits)

    err_hits = store.search_traces(TraceFilters(errors_only=True, limit=20))
    assert any(t.trace_id == "t-err" for t in err_hits)

    m = store.metrics(hours=24)
    assert m.total_traces >= 3
    assert m.total_errors >= 1

    raw = build_trace_zip(store, ["t-phone"], scope="trace")
    with zipfile.ZipFile(io.BytesIO(raw)) as zf:
        names = set(zf.namelist())
        assert {
            "traces.json",
            "events.json",
            "messages.json",
            "orbit.log",
            "kernel.log",
            "metadata.json",
        }.issubset(names)


def test_dashboard_filters_zip_routes(tmp_path, monkeypatch):
    app = _app(tmp_path, monkeypatch)
    tid = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
    with TestClient(app) as client:
        emit_event(
            service="orbit",
            stage="MESSAGE_RECEIVED",
            trace_id=tid,
            data={"jid": "5511888777666@s.whatsapp.net", "channel": "1:1", "message_preview": "ping"},
        )
        emit_event(
            service="kernel",
            stage="RAG_FINISHED",
            trace_id=tid,
            data={"query": "ping", "reason": "ok", "confidence": "high", "sources": ["db:doc/x"]},
        )
        emit_event(
            service="kernel",
            stage="RESPONSE_GENERATED",
            trace_id=tid,
            data={"answer_preview": "pong"},
        )
        _wait(tid, 3)

        login = client.post("/traces/login", data={"token": TOKEN}, follow_redirects=False)
        assert login.status_code == 303
        cookies = login.cookies

        dash = client.get("/traces/dashboard", cookies=cookies)
        assert dash.status_code == 200
        assert "Dashboard" in dash.text

        listing = client.get("/traces?phone=5511888", cookies=cookies)
        assert listing.status_code == 200
        assert tid in listing.text

        detail = client.get(f"/traces/{tid}", cookies=cookies)
        assert detail.status_code == 200
        assert "Timeline" in detail.text
        assert "RAG" in detail.text
        assert "Conversa" in detail.text

        z1 = client.get(f"/traces/{tid}/export.zip", cookies=cookies)
        assert z1.status_code == 200
        assert z1.headers["content-type"].startswith("application/zip")
        with zipfile.ZipFile(io.BytesIO(z1.content)) as zf:
            assert "events.json" in zf.namelist()

        z2 = client.get("/traces/export.zip?scope=all", cookies=cookies)
        assert z2.status_code == 200
