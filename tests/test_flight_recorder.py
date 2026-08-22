"""Flight Recorder (fatia C): snapshot, retention, zip v2, replay diff."""

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
from kernel.trace.replay import text_diff
from kernel.trace.store import TraceStore

TOKEN = "test-flight-recorder-token"


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
    trace_retention_days: int = 30


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
            messages=[
                {"role": "system", "content": "sys prompt"},
                {"role": "user", "content": message},
            ],
            trace=trace,
            decision=None,
            candidates_considered=(),
            effective_discipline="doc",
        )


class ChatProviderStub:
    async def stream_response(self, *_args, **_kwargs):
        yield 'data: [ACL_META]{"confidence":"high","sources":["db:doc/x"],"label":"Documentação"}\n\n'
        yield "data: Resposta flight\n\n"
        yield "data: [DONE]\n\n"


def _wait(tid: str, n: int = 1, timeout: float = 2.5):
    deadline = time.time() + timeout
    while time.time() < deadline:
        store = get_trace_store()
        if store and len(store.get_events(tid)) >= n:
            return
        time.sleep(0.05)


def _app(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("ACL_INTERNAL_BEARER_TOKEN", TOKEN)
    monkeypatch.setenv("ACL_TRACE_DB_PATH", str(tmp_path / "traces.sqlite3"))
    monkeypatch.setenv("ACL_TRACE_ENABLED", "true")
    monkeypatch.setenv("ACL_TRACE_STORE_PROMPTS", "true")
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


def test_snapshot_retention_zip_v2(tmp_path):
    store = TraceStore(tmp_path / "fr.sqlite3")
    store.insert_event(
        trace_id="old",
        timestamp="2020-01-01T00:00:00.000Z",
        service="kernel",
        stage="REQUEST_RECEIVED",
        data={},
        priority=10,
    )
    store.upsert_snapshot(
        "old",
        conversation={"message": "oi", "answer": "ola"},
        rag={"query": "oi"},
        prompt={"prompt_chars": 10},
        tokens={"total_tokens": 3},
        performance={"llm_ms": 10},
    )
    assert store.get_snapshot("old") is not None
    purged = store.purge_older_than(30)
    assert purged >= 1
    assert store.get_snapshot("old") is None

    store.insert_event(
        trace_id="new",
        timestamp="2026-07-28T12:00:00.000Z",
        service="kernel",
        stage="REQUEST_RECEIVED",
        data={"message_preview": "x"},
        priority=10,
    )
    store.upsert_snapshot("new", conversation={"message": "x", "answer": "y"})
    raw = build_trace_zip(store, ["new"], scope="trace")
    with zipfile.ZipFile(io.BytesIO(raw)) as zf:
        names = set(zf.namelist())
        assert "trace.json" in names
        assert "conversation.json" in names
        assert "performance.json" in names
        assert "rag.json" in names
        assert "prompt.json" in names
        assert "tokens.json" in names
        assert "system_metrics.json" in names


def test_text_diff():
    d = text_diff("ola mundo", "ola terra")
    assert d["identical"] is False
    assert "ola" in d["unified"] or d["similarity"] < 1


def test_v1_creates_snapshot_and_replay(tmp_path, monkeypatch):
    app = _app(tmp_path, monkeypatch)
    monkeypatch.delenv("ACL_REQUIRE_API_AUTH", raising=False)
    tid = "cccccccc-cccc-cccc-cccc-cccccccccccc"
    with TestClient(app) as client:
        r = client.post(
            "/v1/chat",
            headers={"X-Trace-Id": tid},
            json={
                "context": {"platform": "whatsapp", "user_id": "u1", "channel_id": "c1"},
                "message": "o que é list comprehension?",
            },
        )
        assert r.status_code == 200
        _wait(tid, 5)
        store = get_trace_store()
        assert store is not None
        # flush snapshots written sync in pipeline
        snap = store.get_snapshot(tid)
        assert snap is not None
        assert snap["conversation"].get("message")
        assert "prompt_chars" in (snap.get("prompt") or {}) or snap.get("prompt")

        login = client.post("/traces/login", data={"token": TOKEN}, follow_redirects=False)
        cookies = login.cookies
        detail = client.get(f"/traces/{tid}", cookies=cookies)
        assert detail.status_code == 200
        assert "PROMPT_BUILT" in detail.text or "Prompt forensics" in detail.text

        replay = client.post(f"/traces/{tid}/replay", cookies=cookies)
        assert replay.status_code == 200
        assert "Diff" in replay.text or "Replay" in replay.text

        m = store.metrics(hours=24)
        assert m.p95_ms is not None or m.total_traces >= 1
