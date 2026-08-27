"""Stress curto V1 — não substitui long-run de horas (ver relatório red team)."""

from __future__ import annotations

import gc
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from api.rate_limit import reset_for_tests
from app.factory import create_app
from app.state import AppServices
from kernel.memory.group_memory import GroupMemoryStore
from kernel.memory.idempotency import IdempotencyStore
from kernel.memory.pinned_store import PinnedSessionStore
from kernel.memory.transcript_store import TranscriptStore
from kernel.orchestrator.context import BuildMessagesResult, ContextTrace


@pytest.fixture(autouse=True)
def _rl():
    reset_for_tests()
    yield
    reset_for_tests()


class FastChatStub:
    async def stream_response(self, *_a, **_k):
        yield 'data: [ACL_META]{"confidence":"high","sources":[]}\n\n'
        yield "data: ok\n\n"
        yield "data: [DONE]\n\n"


class FastCM:
    def __init__(self):
        self.settings = SimpleNamespace(transcript_max_turns=4, group_memory_enabled=False)

    def build_messages(self, message, **kwargs):
        return BuildMessagesResult(
            messages=[{"role": "user", "content": message}],
            trace=ContextTrace(label="S", sources=(), source_details=()),
            effective_discipline=None,
        )


def test_short_stress_idempotency_and_memory_bounded(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("ACL_REQUIRE_API_AUTH", "true")
    monkeypatch.setenv("ACL_API_BEARER_TOKEN", "stress-token")
    monkeypatch.setenv("ACL_CHAT_RATE_LIMIT", "10000")
    monkeypatch.setenv("ACL_AUTH_FAIL_RATE_LIMIT", "10000")
    n = 80
    idem = IdempotencyStore(default_ttl_seconds=60)
    services = AppServices(
        search_engine=SimpleNamespace(),  # type: ignore[arg-type]
        context_manager=FastCM(),  # type: ignore[arg-type]
        chat_provider=FastChatStub(),  # type: ignore[arg-type]
        pinned_store=PinnedSessionStore(),
        transcript_store=TranscriptStore(),
        group_memory_store=GroupMemoryStore(tmp_path / "stress_gm.sqlite3"),
        idempotency_store=idem,
    )
    client = TestClient(create_app(services))
    headers_base = {"Authorization": "Bearer stress-token"}
    for i in range(n):
        h = {**headers_base, "X-Message-Id": f"stress-{i}"}
        r = client.post(
            "/v1/chat",
            json={
                "context": {
                    "platform": "whatsapp",
                    "user_id": "u-stress",
                    "channel_id": "g-stress@g.us",
                },
                "message": f"msg {i}",
            },
            headers=h,
        )
        assert r.status_code == 200
    gc.collect()
    assert len(idem._records) <= 2000
    assert len(services.transcript_store.list_keys()) <= n
