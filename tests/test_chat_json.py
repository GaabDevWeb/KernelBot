"""Aceite do contrato JSON canónico de POST /chat (sem LLM/MySQL reais)."""

from __future__ import annotations

from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.factory import create_app
from app.state import AppServices
from kernel.orchestrator.context import BuildMessagesResult, ContextTrace


class ContextManagerStub:
    def build_messages(self, *_args, **_kwargs):
        trace = ContextTrace(
            label="SQL",
            sources=("db:sql/aula",),
            source_details=({"discipline": "sql-modelagem-relacional"},),
            confidence="high",
            decision="answer",
            reason="ok",
        )
        return BuildMessagesResult(
            messages=[{"role": "user", "content": "oi"}],
            trace=trace,
            decision=None,
        )


class ChatProviderStub:
    async def stream_response(self, *_args, **_kwargs):
        yield 'data: [ACL_META]{"confidence":"high","sources":["db:sql/aula"],"label":"SQL"}\n\n'
        yield "data: Resposta canónica\n\n"
        yield "data: [DONE]\n\n"


def test_chat_json_canonical_contract() -> None:
    services = AppServices(
        search_engine=SimpleNamespace(),  # type: ignore[arg-type]
        context_manager=ContextManagerStub(),  # type: ignore[arg-type]
        chat_provider=ChatProviderStub(),  # type: ignore[arg-type]
        pinned_store=SimpleNamespace(),  # type: ignore[arg-type]
    )
    response = TestClient(create_app(services)).post(
        "/chat",
        json={
            "user_id": "u1",
            "message": "O que é normalização?",
            "channel": "cli",
            "metadata": {"trace": "t1"},
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == "Resposta canónica"
    assert body["discipline"] == "sql-modelagem-relacional"
    assert body["sources"] == ["db:sql/aula"]
    assert body["confidence"] == 0.95
    assert body["metadata"]["user_id"] == "u1"
    assert body["metadata"]["channel"] == "cli"
    assert body["metadata"]["request_metadata"] == {"trace": "t1"}
