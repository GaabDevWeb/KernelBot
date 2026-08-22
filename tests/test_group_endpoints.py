"""Testes para endpoints de Group Memory e Idempotência no /v1."""

from __future__ import annotations

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

BASE_CONTEXT = {"platform": "whatsapp", "user_id": "u1", "channel_id": "group-123@g.us"}


@pytest.fixture(autouse=True)
def _isolated_rate_limit():
    reset_for_tests()
    yield
    reset_for_tests()


class ChatProviderStub:
    async def stream_response(self, *_args, **_kwargs):
        yield 'data: [ACL_META]{"confidence":"high","sources":["kernel:lesson/1"],"label":"Python"}\n\n'
        yield "data: Resposta simulada\n\n"
        yield "data: [DONE]\n\n"


class ContextManagerStub:
    def __init__(self) -> None:
        self.settings = SimpleNamespace(
            transcript_max_turns=16,
            group_memory_enabled=True,
            group_profile_enabled=True,
            group_profile_update_threshold=50,
        )

    def build_messages(self, message, **kwargs):
        trace = ContextTrace(
            label="Python",
            sources=("kernel:lesson/1",),
            source_details=({"discipline": "python"},),
        )
        return BuildMessagesResult(
            messages=[{"role": "user", "content": message}],
            trace=trace,
            effective_discipline="python",
        )


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("ACL_INTERNAL_BEARER_TOKEN", "test-secret-token")
    monkeypatch.setenv("ACL_WHATSAPP_TOKEN", "test-secret-token")

    mem_store = GroupMemoryStore(tmp_path / "test_group_mem.sqlite3")
    idem_store = IdempotencyStore(default_ttl_seconds=60)

    services = AppServices(
        search_engine=SimpleNamespace(),  # type: ignore[arg-type]
        context_manager=ContextManagerStub(),  # type: ignore[arg-type]
        chat_provider=ChatProviderStub(),  # type: ignore[arg-type]
        pinned_store=PinnedSessionStore(),
        transcript_store=TranscriptStore(),
        group_memory_store=mem_store,
        idempotency_store=idem_store,
    )
    app = create_app(services)
    return TestClient(app)


def test_batch_ingest_and_history_search(client: TestClient) -> None:
    headers = {"Authorization": "Bearer test-secret-token"}
    payload = {
        "platform": "whatsapp",
        "channel_id": "group-123@g.us",
        "messages": [
            {
                "message_id": "m1",
                "user_id": "user-a",
                "sender_name": "Alice",
                "content": "A prova de Python é na próxima terça!",
            },
            {
                "message_id": "m2",
                "user_id": "user-b",
                "sender_name": "Bob",
                "content": "Beleza, obrigado Alice!",
            },
        ],
    }

    r_post = client.post("/v1/groups/messages", json=payload, headers=headers)
    assert r_post.status_code == 200
    assert r_post.json()["messages_inserted"] == 2

    # Busca histórica
    r_hist = client.get(
        "/v1/groups/whatsapp/group-123@g.us/history?query=prova",
        headers=headers,
    )
    assert r_hist.status_code == 200
    data = r_hist.json()
    assert data["count"] >= 1
    assert data["results"][0]["message_id"] == "m1"


def test_group_state_and_profile_endpoints(client: TestClient) -> None:
    headers = {"Authorization": "Bearer test-secret-token"}

    # Initial state
    r_state0 = client.get("/v1/groups/whatsapp/group-123@g.us/state", headers=headers)
    assert r_state0.status_code == 200
    assert r_state0.json()["introduction_sent"] is False

    # Set state
    r_set = client.post(
        "/v1/groups/whatsapp/group-123@g.us/state",
        json={"introduction_sent": True},
        headers=headers,
    )
    assert r_set.status_code == 200
    assert r_set.json()["introduction_sent"] is True

    # Refresh profile
    r_prof = client.post(
        "/v1/groups/whatsapp/group-123@g.us/profile/refresh",
        headers=headers,
    )
    assert r_prof.status_code == 200
    assert "profile" in r_prof.json()


def test_idempotency_via_x_message_id_header(client: TestClient) -> None:
    headers = {
        "Authorization": "Bearer test-secret-token",
        "X-Message-Id": "msg-unique-999",
    }
    chat_payload = {
        "context": BASE_CONTEXT,
        "message": "Qual é a sintaxe de list comprehension?",
    }

    # 1ª chamada -> 200
    r1 = client.post("/v1/chat", json=chat_payload, headers=headers)
    assert r1.status_code == 200
    ans1 = r1.json()["answer"]

    # 2ª chamada imediata com o mesmo X-Message-Id -> retorna cache (200) sem reexecutar LLM
    r2 = client.post("/v1/chat", json=chat_payload, headers=headers)
    assert r2.status_code == 200
    assert r2.json()["answer"] == ans1


def test_delete_group_memory_endpoint(client: TestClient) -> None:
    headers = {"Authorization": "Bearer test-secret-token"}

    r_del = client.delete(
        "/v1/groups/whatsapp/group-123@g.us/memory",
        headers=headers,
    )
    assert r_del.status_code == 200
    assert r_del.json()["ok"] is True
