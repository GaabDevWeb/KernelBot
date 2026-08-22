"""Aceite do contrato v1 multi-canal POST /v1/chat (Kernel↔Orbit — ADR-0002).

Casos (a)-(h) do plano `memory/kernel-orbit-integration/plan.md` (T5). Segue o
padrão de stubs de `test_chat_json.py` (ContextManagerStub/ChatProviderStub) e
de `test_internal_api.py` (monkeypatch de env para auth), mas usa
`PinnedSessionStore`/`TranscriptStore` REAIS — `api/routes_v1.py` chama
`.clear`/`.get`/`.append_pair`, que um `SimpleNamespace` não fornece.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from api.rate_limit import reset_for_tests
from app.factory import create_app
from app.state import AppServices
from kernel.memory.pinned_store import PinnedSessionStore
from kernel.memory.transcript_store import TranscriptStore
from kernel.orchestrator.context import BuildMessagesResult, ContextTrace

BASE_CONTEXT = {"platform": "whatsapp", "user_id": "u1", "channel_id": "c1"}


@pytest.fixture(autouse=True)
def _isolated_rate_limit_buckets():
    """Evita que o rate limit (dict process-local) vaze entre testes/módulos."""
    reset_for_tests()
    yield
    reset_for_tests()


@dataclass
class SettingsStub:
    """Só os atributos que `api/routes_v1.py` acede em `context_manager.settings`."""

    transcript_max_turns: int = 16


class ContextManagerStub:
    """Grava os kwargs de `build_messages` para inspeção pelo teste (foco: `conversation_history`)."""

    def __init__(self) -> None:
        self.settings = SettingsStub(transcript_max_turns=16)
        self.last_kwargs: dict | None = None

    def build_messages(self, message, discipline_filter=None, session_id=None, conversation_history=None, **_kwargs):
        self.last_kwargs = {
            "message": message,
            "discipline_filter": discipline_filter,
            "session_id": session_id,
            "conversation_history": conversation_history,
        }
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
        yield "data: Resposta v1\n\n"
        yield "data: [DONE]\n\n"


def _build_app(context_manager=None, search_engine=None):
    cm = context_manager or ContextManagerStub()
    services = AppServices(
        search_engine=search_engine if search_engine is not None else SimpleNamespace(),  # type: ignore[arg-type]
        context_manager=cm,  # type: ignore[arg-type]
        chat_provider=ChatProviderStub(),  # type: ignore[arg-type]
        pinned_store=PinnedSessionStore(),
        lesson_catalog=None,
        transcript_store=TranscriptStore(),
    )
    return TestClient(create_app(services)), services, cm


# (a) fluxo feliz -----------------------------------------------------------


def test_v1_chat_happy_path_returns_answer_sources_confidence_and_channel_metadata() -> None:
    client, _services, _cm = _build_app()

    response = client.post("/v1/chat", json={"context": BASE_CONTEXT, "message": "ola"})

    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == "Resposta v1"
    assert body["sources"] == ["db:doc/x"]
    assert body["confidence"] == 0.95
    assert body["metadata"]["channel"] == "whatsapp"


# (b) reset_context=true limpa transcript ANTES de build_messages -----------


def test_v1_chat_reset_context_clears_transcript_before_build_messages() -> None:
    client, services, cm = _build_app()
    key = "whatsapp:u1:c1"
    services.transcript_store.append_pair(key, "pergunta antiga", "resposta antiga", max_turns=16)

    response = client.post(
        "/v1/chat",
        json={"context": BASE_CONTEXT, "message": "nova pergunta", "reset_context": True},
    )

    assert response.status_code == 200
    assert cm.last_kwargs["conversation_history"] == []


# (c) duas POSTs com o mesmo contexto → 2ª recebe o par da 1ª ---------------


def test_v1_chat_second_call_receives_first_pair_in_history() -> None:
    client, _services, cm = _build_app()

    first = client.post("/v1/chat", json={"context": BASE_CONTEXT, "message": "primeira"})
    assert first.status_code == 200

    second = client.post("/v1/chat", json={"context": BASE_CONTEXT, "message": "segunda"})
    assert second.status_code == 200

    assert cm.last_kwargs["conversation_history"] == [
        {"role": "user", "content": "primeira"},
        {"role": "assistant", "content": "Resposta v1"},
    ]


# (d) history no body é sempre ignorado (G7) ---------------------------------


def test_v1_chat_body_history_is_ignored_conversation_history_comes_only_from_store() -> None:
    client, _services, cm = _build_app()
    body_history = [{"role": "user", "content": "não deve aparecer"}]

    response = client.post(
        "/v1/chat",
        json={"context": BASE_CONTEXT, "message": "ola", "history": body_history},
    )

    assert response.status_code == 200
    conversation_history = cm.last_kwargs["conversation_history"]
    assert conversation_history != body_history
    assert conversation_history == []


# (e) auth de canal: sem Bearer → 401; com Bearer correto → 200 -------------


def test_v1_chat_requires_valid_channel_bearer_when_auth_enabled(monkeypatch) -> None:
    monkeypatch.setenv("ACL_REQUIRE_API_AUTH", "true")
    monkeypatch.setenv("ACL_CHANNEL_API_KEYS", "whatsapp:tokensecret")
    monkeypatch.delenv("KERNELBOT_ENV", raising=False)
    monkeypatch.delenv("ACL_API_BEARER_TOKEN", raising=False)
    client, _services, _cm = _build_app()

    denied = client.post("/v1/chat", json={"context": BASE_CONTEXT, "message": "ola"})
    assert denied.status_code == 401

    ok = client.post(
        "/v1/chat",
        json={"context": BASE_CONTEXT, "message": "ola"},
        headers={"Authorization": "Bearer tokensecret"},
    )
    assert ok.status_code == 200


# (f) session_id só-dígitos → 422 --------------------------------------------


def test_v1_chat_rejects_digits_only_session_id() -> None:
    client, _services, _cm = _build_app()
    context = {**BASE_CONTEXT, "session_id": "12345678"}

    response = client.post("/v1/chat", json={"context": context, "message": "ola"})

    assert response.status_code == 422


# (g) stream=true não persiste transcript (SUP-1) ----------------------------


def test_v1_chat_stream_true_does_not_leak_into_next_non_stream_call() -> None:
    client, _services, cm = _build_app()

    streamed = client.post(
        "/v1/chat",
        json={"context": BASE_CONTEXT, "message": "mensagem em stream", "stream": True},
    )
    assert streamed.status_code == 200

    after = client.post("/v1/chat", json={"context": BASE_CONTEXT, "message": "depois do stream"})
    assert after.status_code == 200
    assert cm.last_kwargs["conversation_history"] == []


# (h) message="/reload" não é tratado como comando privilegiado em /v1/chat -


def test_v1_chat_reload_message_does_not_trigger_search_engine_rebuild() -> None:
    rebuild_state = SimpleNamespace(called=False)

    def _rebuild() -> None:
        rebuild_state.called = True

    search_engine = SimpleNamespace(rebuild=_rebuild)
    client, _services, _cm = _build_app(search_engine=search_engine)

    response = client.post("/v1/chat", json={"context": BASE_CONTEXT, "message": "/reload"})

    assert response.status_code == 200
    assert response.json()["answer"] == "Resposta v1"
    assert rebuild_state.called is False
