"""Testes da API interna e do SDK de inspeção."""

from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.factory import create_app
from app.state import AppServices
from kernel.inspect.recorder import reset_recorder_for_tests
from kernel.orchestrator.context import BuildMessagesResult, ContextTrace
from kernel.rag.retrieval import RetrievalCandidate


TOKEN = "test-internal-token"


@dataclass
class SettingsStub:
    iss_public_lesson_base: str = ""
    catalog_enabled: bool = False
    reload_bearer_token: str | None = TOKEN
    retrieval_candidate_k: int = 8
    retrieval_min_score: float = 1.5
    retrieval_min_score_margin: float = 0.15
    retrieval_min_coverage: float = 0.34
    retrieval_min_coverage_weighted: float = 0.34
    retrieval_min_terms: int = 2
    retrieval_top_k: int = 4
    retrieval_max_chunks_per_source: int = 2
    retrieval_mode: str = "strict"
    disambiguation_enabled: bool = False
    grounding_policy: str = "anchored"
    llm_provider: str = "openrouter"
    cursor_model: str = "composer-2.5"
    cursor_api_key: str = ""
    openrouter_api_key: str = "x"
    models: tuple[str, ...] = ("m1",)
    global_context_mode: str = "geral"
    project_root: object = None

    def __post_init__(self):
        from pathlib import Path

        if self.project_root is None:
            self.project_root = Path(".").resolve()


class ContextManagerStub:
    settings = SettingsStub()

    def build_messages(self, message, discipline_filter=None, session_id=None, conversation_history=None, **_kwargs):
        cand = RetrievalCandidate(
            source="db:doc/x",
            chunk_id="doc:0",
            text="texto",
            discipline="doc",
            raw_score=3.0,
            normalized_score=1.0,
            matched_terms=("texto",),
        )
        from kernel.rag.retrieval import RetrievalDecision, RetrievalTrace

        trace_r = RetrievalTrace(
            query=message,
            normalized_query=message.lower(),
            informative_terms=("texto",),
            mode="strict",
            top_score=3.0,
            decision="answer",
            reason="ok",
        )
        decision = RetrievalDecision(
            allow_generation=True,
            reason="ok",
            confidence="high",
            selected_candidates=(cand,),
            trace=trace_r,
        )
        ctx = ContextTrace(
            label="Documentação (doc)",
            sources=("db:doc/x",),
            source_details=({"discipline": "doc", "source": "db:doc/x"},),
            confidence="high",
            decision="answer",
            reason="ok",
        )
        return BuildMessagesResult(
            messages=[
                {"role": "system", "content": "sys"},
                {"role": "user", "content": message},
            ],
            trace=ctx,
            decision=decision,
            candidates_considered=(cand,),
            effective_discipline="doc",
        )


class ChatProviderStub:
    async def stream_response(self, *_a, **_k):
        yield 'data: [ACL_META]{"confidence":"high","sources":["db:doc/x"],"llm_called":true,"tokens_used":1}\n\n'
        yield "data: olá\n\n"
        yield "data: [DONE]\n\n"


class SearchEngineStub:
    chunks = [{"id": 1}]
    discipline_ids = ["doc", "python"]

    def search_candidates(self, message, candidate_k=8, discipline_filter=None):
        return [
            RetrievalCandidate(
                source="db:doc/x",
                chunk_id="doc:0",
                text="Normalização e BM25",
                discipline="doc",
                raw_score=4.0,
                normalized_score=1.0,
                matched_terms=("bm25",),
            )
        ]

    def normalize_discipline(self, raw):
        return raw


def _app():
    reset_recorder_for_tests()
    services = AppServices(
        search_engine=SearchEngineStub(),  # type: ignore[arg-type]
        context_manager=ContextManagerStub(),  # type: ignore[arg-type]
        chat_provider=ChatProviderStub(),  # type: ignore[arg-type]
        pinned_store=SimpleNamespace(get=lambda *_: None),  # type: ignore[arg-type]
    )
    return create_app(services)


def test_internal_requires_bearer(monkeypatch) -> None:
    monkeypatch.setenv("ACL_INTERNAL_BEARER_TOKEN", TOKEN)
    monkeypatch.delenv("KERNELBOT_ENV", raising=False)
    client = TestClient(_app())
    assert client.get("/internal/system").status_code in {401, 503}


def test_internal_system_and_pipeline_after_chat(monkeypatch) -> None:
    monkeypatch.setenv("ACL_INTERNAL_STORE_PROMPTS", "true")
    monkeypatch.setenv("ACL_INTERNAL_BEARER_TOKEN", TOKEN)
    monkeypatch.delenv("KERNELBOT_ENV", raising=False)
    client = TestClient(_app())
    headers = {"Authorization": f"Bearer {TOKEN}"}
    sys_resp = client.get("/internal/system", headers=headers)
    assert sys_resp.status_code == 200
    assert sys_resp.json()["product"] == "Kernel API"

    chat = client.post(
        "/chat",
        json={"message": "o que é BM25?", "channel": "cli", "user_id": "u1"},
    )
    assert chat.status_code == 200
    request_id = chat.json()["metadata"]["request_id"]
    assert chat.headers.get("X-Request-Id") == request_id

    pipe = client.get(f"/internal/pipeline/{request_id}", headers=headers)
    assert pipe.status_code == 200
    body = pipe.json()
    assert body["kind"] == "chat"
    assert body["rag"]["candidates_selected"][0]["source"] == "db:doc/x"

    rag_q = client.get(f"/internal/rag/query/{request_id}", headers=headers)
    assert rag_q.status_code == 200
    assert rag_q.json()["rag"]["reason"] == "ok"

    prompt = client.get(f"/internal/prompt/{request_id}", headers=headers)
    assert prompt.status_code == 200
    assert prompt.json()["prompt"][0]["role"] == "system"


def test_search_records_pipeline(monkeypatch) -> None:
    monkeypatch.setenv("ACL_INTERNAL_BEARER_TOKEN", TOKEN)
    monkeypatch.delenv("KERNELBOT_ENV", raising=False)
    monkeypatch.delenv("ACL_REQUIRE_API_AUTH", raising=False)
    client = TestClient(_app())
    headers = {"Authorization": f"Bearer {TOKEN}"}
    resp = client.post("/search", json={"message": "BM25", "channel": "cli", "top_k": 1})
    assert resp.status_code == 200
    rid = resp.json()["metadata"]["request_id"]
    pipe = client.get(f"/internal/pipeline/{rid}", headers=headers)
    assert pipe.status_code == 200
    assert pipe.json()["kind"] == "search"


def test_health_deep(monkeypatch) -> None:
    monkeypatch.setenv("ACL_INTERNAL_BEARER_TOKEN", TOKEN)
    monkeypatch.delenv("KERNELBOT_ENV", raising=False)
    client = TestClient(_app())
    headers = {"Authorization": f"Bearer {TOKEN}"}
    resp = client.get("/internal/health/deep", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["checks"]["provider_configured"] is True


def test_api_auth_required_when_enabled(monkeypatch) -> None:
    monkeypatch.setenv("ACL_REQUIRE_API_AUTH", "true")
    monkeypatch.setenv("ACL_API_BEARER_TOKEN", "channel-secret")
    monkeypatch.delenv("KERNELBOT_ENV", raising=False)
    client = TestClient(_app())
    denied = client.post("/chat", json={"message": "oi", "channel": "cli"})
    assert denied.status_code == 401
    ok = client.post(
        "/chat",
        json={"message": "oi", "channel": "cli", "user_id": "u1"},
        headers={"Authorization": "Bearer channel-secret"},
    )
    assert ok.status_code == 200


def test_session_id_digits_rejected(monkeypatch) -> None:
    monkeypatch.delenv("ACL_REQUIRE_API_AUTH", raising=False)
    monkeypatch.delenv("KERNELBOT_ENV", raising=False)
    client = TestClient(_app())
    resp = client.post(
        "/chat",
        json={"message": "oi", "channel": "cli", "session_id": "12345678"},
    )
    assert resp.status_code == 422


def test_metadata_too_large_rejected(monkeypatch) -> None:
    monkeypatch.delenv("ACL_REQUIRE_API_AUTH", raising=False)
    client = TestClient(_app())
    resp = client.post(
        "/chat",
        json={
            "message": "oi",
            "channel": "cli",
            "metadata": {"blob": "x" * 5000},
        },
    )
    assert resp.status_code == 422
