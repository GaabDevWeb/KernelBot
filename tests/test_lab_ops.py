"""Testes Ops Lab P3 — auth, páginas 200, playground com provider stub."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.factory import create_app
from app.state import AppServices
from kernel.memory.pinned_store import PinnedSessionStore
from kernel.memory.transcript_store import TranscriptStore
from kernel.orchestrator.context import BuildMessagesResult, ContextTrace
from kernel.trace import reset_trace_bus_for_tests
from kernel.comms.store import reset_comms_store_for_tests
from kernel.users.store import reset_users_store_for_tests


@dataclass
class SettingsStub:
    llm_provider: str = "openrouter"
    cursor_model: str = "composer-2.5"
    models: tuple[str, ...] = ("model-a", "model-b", "model-c")
    retrieval_top_k: int = 4
    transcript_max_turns: int = 16
    grounding_policy: str = "strict"


class ContextManagerStub:
    def __init__(self) -> None:
        self.settings = SettingsStub()
        self.last_kwargs: dict | None = None

    def build_messages(
        self,
        message,
        discipline_filter=None,
        session_id=None,
        conversation_history=None,
        *,
        top_k=None,
    ):
        self.last_kwargs = {
            "message": message,
            "discipline_filter": discipline_filter,
            "session_id": session_id,
            "conversation_history": conversation_history,
            "top_k": top_k,
        }
        trace = ContextTrace(
            label="Lab",
            sources=("db:doc/x",),
            source_details=({"discipline": "doc"},),
            confidence="high",
            decision="answer",
            reason="ok",
        )
        return BuildMessagesResult(
            messages=[
                {"role": "system", "content": "sys"},
                {"role": "user", "content": message},
            ],
            trace=trace,
            decision=None,
        )


class ChatProviderStub:
    def __init__(self) -> None:
        self.last_kwargs: dict | None = None

    async def stream_response(self, *_args, **kwargs):
        self.last_kwargs = kwargs
        yield 'data: [ACL_META]{"confidence":"high","sources":["db:doc/x"],"label":"Lab","llm_called":true,"tokens_used":3}\n\n'
        yield "data: Resposta lab stub\n\n"
        yield "data: [DONE]\n\n"


def _build_app():
    cm = ContextManagerStub()
    provider = ChatProviderStub()
    services = AppServices(
        context_manager=cm,
        chat_provider=provider,
        search_engine=SimpleNamespace(chunks=[], discipline_ids=[]),
        pinned_store=PinnedSessionStore(),
        transcript_store=TranscriptStore(),
        lesson_catalog=None,
        indexed_lesson_keys=frozenset(),
    )
    return create_app(services=services), cm, provider


def test_lab_pages_require_auth(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("ACL_INTERNAL_BEARER_TOKEN", "lab-p3-token")
    monkeypatch.setenv("ACL_TRACE_DB_PATH", str(tmp_path / "traces.sqlite3"))
    monkeypatch.setenv("ACL_USERS_DB_PATH", str(tmp_path / "users.sqlite3"))
    monkeypatch.setenv("ACL_COMM_DB_PATH", str(tmp_path / "comms.sqlite3"))
    reset_trace_bus_for_tests()
    reset_comms_store_for_tests()
    reset_users_store_for_tests()

    app, _, _ = _build_app()
    with TestClient(app) as client:
        for path in (
            "/ops/lab/playground",
            "/ops/lab/replay",
            "/ops/lab/diff",
            "/ops/lab/benchmark",
        ):
            r = client.get(path, follow_redirects=False)
            assert r.status_code == 303, path
            assert "/ops/login" in r.headers.get("location", "")

    reset_users_store_for_tests()
    reset_comms_store_for_tests()
    reset_trace_bus_for_tests()


def test_lab_pages_ok_and_playground_stub(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("ACL_INTERNAL_BEARER_TOKEN", "lab-p3-token")
    monkeypatch.setenv("ACL_TRACE_DB_PATH", str(tmp_path / "traces.sqlite3"))
    monkeypatch.setenv("ACL_USERS_DB_PATH", str(tmp_path / "users.sqlite3"))
    monkeypatch.setenv("ACL_COMM_DB_PATH", str(tmp_path / "comms.sqlite3"))
    monkeypatch.setenv("ACL_LAB_BENCHMARK_MODELS", "model-a,model-b")
    reset_trace_bus_for_tests()
    reset_comms_store_for_tests()
    reset_users_store_for_tests()

    app, cm, provider = _build_app()
    with TestClient(app) as client:
        client.post("/ops/login", data={"token": "lab-p3-token"}, follow_redirects=False)

        for path in (
            "/ops/lab/playground",
            "/ops/lab/replay",
            "/ops/lab/diff",
            "/ops/lab/benchmark",
        ):
            r = client.get(path)
            assert r.status_code == 200, path
            assert b'phase-pill">P3' not in r.content

        # Playground: stub provider
        play = client.post(
            "/ops/lab/playground",
            data={
                "message": "ola lab",
                "model": "model-a",
                "temperature": "0.5",
                "top_k": "3",
                "max_tokens": "256",
            },
        )
        assert play.status_code == 200
        assert b"Resposta lab stub" in play.content
        assert b"Lat" in play.content or b"lat" in play.content.lower()
        assert cm.last_kwargs is not None
        assert cm.last_kwargs["top_k"] == 3
        assert provider.last_kwargs is not None
        assert provider.last_kwargs.get("model") == "model-a"
        assert provider.last_kwargs.get("temperature") == 0.5
        assert provider.last_kwargs.get("max_tokens") == 256

        # Benchmark: 2 modelos do env
        bench = client.post(
            "/ops/lab/benchmark",
            data={
                "message": "compare",
                "temperature": "0.7",
                "top_k": "4",
                "max_tokens": "128",
            },
        )
        assert bench.status_code == 200
        assert b"model-a" in bench.content
        assert b"model-b" in bench.content
        assert b"Resposta lab stub" in bench.content

        # Diff page with empty form still 200
        d = client.get("/ops/lab/diff?a=missing&b=also")
        assert d.status_code == 200

    reset_users_store_for_tests()
    reset_comms_store_for_tests()
    reset_trace_bus_for_tests()
