"""REDTEAM-015 — replay Orbit→Kernel via X-Message-Id (equivalente determinístico)."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from api.rate_limit import reset_for_tests
from app.factory import create_app
from app.state import AppServices
from kernel.memory.idempotency import IdempotencyStore
from kernel.memory.pinned_store import PinnedSessionStore
from kernel.memory.transcript_store import TranscriptStore
from kernel.orchestrator.context import BuildMessagesResult, ContextTrace


@pytest.fixture(autouse=True)
def _rl():
    reset_for_tests()
    yield
    reset_for_tests()


class ChatProviderStub:
    calls = 0

    async def stream_response(self, *_args, **_kwargs):
        type(self).calls += 1
        yield 'data: [ACL_META]{"confidence":"high","sources":[]}\n\n'
        yield "data: resposta unica\n\n"
        yield "data: [DONE]\n\n"


class ContextManagerStub:
    def __init__(self) -> None:
        self.settings = SimpleNamespace(transcript_max_turns=8, group_memory_enabled=False)
        self.calls = 0

    def build_messages(self, message, **kwargs):
        self.calls += 1
        trace = ContextTrace(label="T", sources=(), source_details=())
        return BuildMessagesResult(
            messages=[{"role": "user", "content": message}],
            trace=trace,
            effective_discipline=None,
        )


def test_replay_same_x_message_id_does_not_reexecute_llm(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    ChatProviderStub.calls = 0
    monkeypatch.setenv("ACL_REQUIRE_API_AUTH", "true")
    monkeypatch.setenv("ACL_API_BEARER_TOKEN", "orbit-secret")
    cm = ContextManagerStub()
    services = AppServices(
        search_engine=SimpleNamespace(),  # type: ignore[arg-type]
        context_manager=cm,  # type: ignore[arg-type]
        chat_provider=ChatProviderStub(),  # type: ignore[arg-type]
        pinned_store=PinnedSessionStore(),
        transcript_store=TranscriptStore(),
        idempotency_store=IdempotencyStore(default_ttl_seconds=120),
    )
    client = TestClient(create_app(services))
    headers = {"Authorization": "Bearer orbit-secret", "X-Message-Id": "WA-MSG-CRASH-001"}
    body = {
        "context": {"platform": "whatsapp", "user_id": "u1", "channel_id": "g1@g.us"},
        "message": "ola",
    }
    r1 = client.post("/v1/chat", json=body, headers=headers)
    r2 = client.post("/v1/chat", json=body, headers=headers)
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.json()["answer"] == r2.json()["answer"]
    assert cm.calls == 1
    assert ChatProviderStub.calls == 1


def test_concurrent_same_message_id_one_wins(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    import threading

    monkeypatch.setenv("ACL_REQUIRE_API_AUTH", "true")
    monkeypatch.setenv("ACL_API_BEARER_TOKEN", "orbit-secret")
    cm = ContextManagerStub()
    services = AppServices(
        search_engine=SimpleNamespace(),  # type: ignore[arg-type]
        context_manager=cm,  # type: ignore[arg-type]
        chat_provider=ChatProviderStub(),  # type: ignore[arg-type]
        pinned_store=PinnedSessionStore(),
        transcript_store=TranscriptStore(),
        idempotency_store=IdempotencyStore(default_ttl_seconds=120),
    )
    client = TestClient(create_app(services))
    headers = {"Authorization": "Bearer orbit-secret", "X-Message-Id": "WA-CONCURRENT-99"}
    body = {
        "context": {"platform": "whatsapp", "user_id": "u1", "channel_id": "g1@g.us"},
        "message": "race",
    }
    codes: list[int] = []

    def _post():
        codes.append(client.post("/v1/chat", json=body, headers=headers).status_code)

    threads = [threading.Thread(target=_post) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert 200 in codes
    assert any(c in (409, 200) for c in codes)
    assert cm.calls <= 2
