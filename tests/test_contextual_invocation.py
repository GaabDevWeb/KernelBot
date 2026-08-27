"""Testes — @orbit sem texto em grupos (CONTEXTUAL_INVOCATION)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from api.rate_limit import reset_for_tests
from app.factory import create_app
from app.state import AppServices
from kernel.group.invocation import (
    GROUP_INTRODUCTION_ANSWER,
    derive_rag_query_from_recent,
    has_useful_recent_context,
    parse_invocation_from_metadata,
)
from kernel.memory.group_memory import GroupMemoryStore
from kernel.memory.pinned_store import PinnedSessionStore
from kernel.memory.transcript_store import TranscriptStore
from kernel.orchestrator.context import BuildMessagesResult, ContextTrace
from kernel.schemas.chat import ChatRequestV1

GROUP_CTX = {
    "platform": "whatsapp",
    "user_id": "5511@s.whatsapp.net",
    "channel_id": "120363@g.us",
}


@pytest.fixture(autouse=True)
def _reset_rate_limit():
    reset_for_tests()
    yield
    reset_for_tests()


@dataclass
class SettingsStub:
    transcript_max_turns: int = 16
    chat_history_max_turns: int = 12
    chat_history_max_chars: int = 12000
    context_router_enabled: bool = True
    group_memory_enabled: bool = False
    group_profile_enabled: bool = False
    system_prompt_geral: str = "test"
    global_context_mode: str = "all"
    catalog_router_prompt: str = ""
    pinned_max_chars: int = 4000
    retrieval_candidate_k: int = 5
    retrieval_min_score: float = 0.0
    retrieval_min_score_margin: float = 0.0
    retrieval_min_coverage: float = 0.0
    retrieval_min_coverage_weighted: float = 0.0
    retrieval_min_terms: int = 1
    retrieval_top_k: int = 3
    retrieval_max_chunks_per_source: int = 2
    retrieval_mode: str = "bm25"
    disambiguation_enabled: bool = False


class ContextManagerCapture:
    def __init__(self) -> None:
        self.settings = SettingsStub()
        self.last_kwargs: dict | None = None

    def build_messages(self, message, **kwargs):
        self.last_kwargs = {"message": message, **kwargs}
        trace = ContextTrace(
            label="Teste",
            sources=(),
            confidence="high",
            decision="answer",
            reason="ok",
            contextual_invocation=not str(message or "").strip(),
            invocation_type="contextual_invocation",
            recent_context_count=len(
                (kwargs.get("request_metadata") or {}).get("recent_context") or []
            ),
        )
        return BuildMessagesResult(
            messages=[{"role": "user", "content": message or "[ctx]"}],
            trace=trace,
            decision=None,
        )


class ChatProviderStub:
    async def stream_response(self, *_args, **_kwargs):
        yield 'data: [ACL_META]{"confidence":"high","sources":[]}\n\n'
        yield "data: Resposta contextual\n\n"
        yield "data: [DONE]\n\n"


def _client_with_group_store(cm: ContextManagerCapture | None = None, tmp_path=None):
    cm = cm or ContextManagerCapture()
    db_path = (tmp_path / "ctx_inv.sqlite3") if tmp_path is not None else Path("data/test_ctx_inv.sqlite3")
    store = GroupMemoryStore(db_path)
    services = AppServices(
        search_engine=SimpleNamespace(chunks=[]),
        context_manager=cm,  # type: ignore[arg-type]
        chat_provider=ChatProviderStub(),  # type: ignore[arg-type]
        pinned_store=PinnedSessionStore(),
        transcript_store=TranscriptStore(),
        group_memory_store=store,
    )
    return TestClient(create_app(services)), services, cm, store


def test_schema_accepts_empty_message_with_contextual_invocation() -> None:
    req = ChatRequestV1(
        context=GROUP_CTX,
        message="",
        metadata={"invocation": {"type": "contextual_invocation", "explicit_text": False}},
    )
    assert req.message == ""


def test_schema_rejects_empty_message_without_invocation() -> None:
    with pytest.raises(ValidationError):
        ChatRequestV1(context=GROUP_CTX, message="")


def test_parse_invocation_empty_orbit_in_group() -> None:
    parsed = parse_invocation_from_metadata(
        {"invocation": {"type": "contextual_invocation", "explicit_text": False}},
        channel_id=GROUP_CTX["channel_id"],
        message="",
    )
    assert parsed.is_contextual is True
    assert parsed.type == "contextual_invocation"


def test_has_useful_recent_context() -> None:
    useful = (
        {"sender": "João", "text": "Alguém sabe se a prova mudou?", "is_bot": False},
        {"sender": "Maria", "text": "Ouvi que foi para sexta.", "is_bot": False},
    )
    noise = (
        {"sender": "João", "text": "bom dia", "is_bot": False},
        {"sender": "Maria", "text": "kkkk", "is_bot": False},
    )
    assert has_useful_recent_context(tuple(useful)) is True
    assert has_useful_recent_context(tuple(noise)) is False


def test_derive_rag_query_not_full_buffer() -> None:
    recent = tuple(
        {"sender": f"u{i}", "text": f"mensagem substantiva número {i}", "is_bot": False}
        for i in range(10)
    )
    q = derive_rag_query_from_recent(recent)
    assert "mensagem substantiva" in q
    assert len(q) <= 500
    assert q.count("mensagem substantiva") <= 3


def test_v1_empty_orbit_not_error_and_passes_metadata(tmp_path) -> None:
    client, _services, cm, store = _client_with_group_store(tmp_path=tmp_path)
    meta = {
        "invocation": {"type": "contextual_invocation", "explicit_text": False},
        "recent_context": [
            "João: A prova mudou?",
            "Maria: Ouvi que foi para sexta.",
        ],
    }
    store.set_group_state("whatsapp", GROUP_CTX["channel_id"], True)

    r = client.post("/v1/chat", json={"context": GROUP_CTX, "message": "", "metadata": meta})
    assert r.status_code == 200
    assert cm.last_kwargs is not None
    assert cm.last_kwargs["message"] == ""
    assert cm.last_kwargs["request_metadata"]["invocation"]["type"] == "contextual_invocation"


def test_first_introduction_on_empty_orbit(tmp_path) -> None:
    client, _services, _cm, store = _client_with_group_store(tmp_path=tmp_path)
    store.set_group_state("whatsapp", GROUP_CTX["channel_id"], False)
    meta = {"invocation": {"type": "contextual_invocation", "explicit_text": False}}

    r = client.post("/v1/chat", json={"context": GROUP_CTX, "message": "", "metadata": meta})
    assert r.status_code == 200
    assert GROUP_INTRODUCTION_ANSWER[:20] in r.json()["answer"]
    assert store.get_group_state("whatsapp", GROUP_CTX["channel_id"])["introduction_sent"] is True


def test_second_empty_orbit_uses_pipeline_not_intro(tmp_path) -> None:
    client, _services, cm, store = _client_with_group_store(tmp_path=tmp_path)
    store.set_group_state("whatsapp", GROUP_CTX["channel_id"], True)
    meta = {
        "invocation": {"type": "contextual_invocation", "explicit_text": False},
        "recent_context": ["João: Dúvida sobre AT"],
    }

    r = client.post("/v1/chat", json={"context": GROUP_CTX, "message": "", "metadata": meta})
    assert r.status_code == 200
    assert r.json()["answer"] == "Resposta contextual"
    assert cm.last_kwargs is not None


def test_explicit_question_still_works(tmp_path) -> None:
    client, _services, cm, store = _client_with_group_store(tmp_path=tmp_path)
    store.set_group_state("whatsapp", GROUP_CTX["channel_id"], True)

    r = client.post(
        "/v1/chat",
        json={
            "context": GROUP_CTX,
            "message": "o que é C#?",
            "metadata": {"invocation": {"type": "question", "explicit_text": True}},
        },
    )
    assert r.status_code == 200
    assert cm.last_kwargs["message"] == "o que é C#?"


def test_idempotency_duplicate_contextual_orbit(tmp_path) -> None:
    client, services, _cm, store = _client_with_group_store(tmp_path=tmp_path)
    store.set_group_state("whatsapp", GROUP_CTX["channel_id"], True)
    headers = {"X-Message-Id": "dup-orbit-1"}
    body = {
        "context": GROUP_CTX,
        "message": "",
        "metadata": {"invocation": {"type": "contextual_invocation", "explicit_text": False}},
    }

    r1 = client.post("/v1/chat", json=body, headers=headers)
    r2 = client.post("/v1/chat", json=body, headers=headers)
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.json()["answer"] == r2.json()["answer"]
